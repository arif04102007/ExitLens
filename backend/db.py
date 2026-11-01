"""Tiny SQLite store: cases (JSON blob), a response cache, and policy watches."""
import json
from pathlib import Path
import sqlite3
import threading
import time

from .config import db_path

_lock = threading.Lock()
_conn = None


def _c():
    global _conn
    if _conn is None:
        p = db_path()
        Path(p).parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(p, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases(
              id TEXT PRIMARY KEY, status TEXT, data TEXT, created_at REAL);
            CREATE TABLE IF NOT EXISTS cache(
              key TEXT PRIMARY KEY, value TEXT, ts REAL);
            CREATE TABLE IF NOT EXISTS watches(
              id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, url TEXT,
              text_hash TEXT, last_checked REAL, changed INTEGER DEFAULT 0);
            """
        )
        _conn.commit()
    return _conn


def reset_for_tests():
    global _conn
    if _conn is not None:
        _conn.close()
    _conn = None


# ---- cases ----
def save_case(case: dict):
    with _lock:
        c = _c()
        c.execute(
            "INSERT OR REPLACE INTO cases(id,status,data,created_at) VALUES(?,?,?,?)",
            (case["id"], case.get("status", ""), json.dumps(case), case.get("created_at", time.time())),
        )
        c.commit()


def load_case(case_id: str):
    with _lock:
        row = _c().execute("SELECT data FROM cases WHERE id=?", (case_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def recent_cases(limit: int = 8):
    with _lock:
        rows = _c().execute(
            "SELECT id,status,data FROM cases ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = json.loads(r["data"])
        out.append({"id": r["id"], "status": r["status"], "user_text": d.get("user_text", "")})
    return out


# ---- cache ----
def cache_get(key: str, ttl: int):
    if ttl <= 0:
        return None
    with _lock:
        row = _c().execute("SELECT value, ts FROM cache WHERE key=?", (key,)).fetchone()
    if row and time.time() - row["ts"] < ttl:
        return json.loads(row["value"])
    return None


def cache_put(key: str, value):
    with _lock:
        c = _c()
        c.execute(
            "INSERT OR REPLACE INTO cache(key,value,ts) VALUES(?,?,?)",
            (key, json.dumps(value), time.time()),
        )
        c.commit()


# ---- watches ----
def add_watch(case_id: str, url: str, text_hash: str):
    with _lock:
        c = _c()
        c.execute(
            "DELETE FROM watches WHERE case_id=? AND url=?", (case_id, url)
        )
        c.execute(
            "INSERT INTO watches(case_id,url,text_hash,last_checked) VALUES(?,?,?,?)",
            (case_id, url, text_hash, time.time()),
        )
        c.commit()


def list_watches(case_id: str):
    with _lock:
        rows = _c().execute("SELECT * FROM watches WHERE case_id=?", (case_id,)).fetchall()
    return [dict(r) for r in rows]


def update_watch(watch_id: int, text_hash: str, changed: bool):
    with _lock:
        c = _c()
        c.execute(
            "UPDATE watches SET text_hash=?, last_checked=?, changed=? WHERE id=?",
            (text_hash, time.time(), 1 if changed else 0, watch_id),
        )
        c.commit()
