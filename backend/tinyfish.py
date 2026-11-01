"""Thin TinyFish REST client (Search, Fetch, Agent) with a SQLite cache.

Endpoints and auth header (X-API-Key) follow docs.tinyfish.ai:
  Search  GET  https://api.search.tinyfish.ai?query=...
  Fetch   POST https://api.fetch.tinyfish.ai            {"urls": [...], "format": "markdown"}
  Agent   POST https://agent.tinyfish.ai/v1/automation/run-sse | run-async | run   {"url","goal"}
  Run     GET  https://agent.tinyfish.ai/v1/runs/{run_id}

If something differs on your account, this is the only file to change.
"""
import hashlib
import json
import time

import requests

from . import db
from .config import cache_ttl, env

SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
AGENT_BASE = "https://agent.tinyfish.ai/v1/automation"
RUNS_URL = "https://agent.tinyfish.ai/v1/runs"


class TinyFishError(Exception):
    pass


def _key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


class TinyFish:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or env("TINYFISH_API_KEY")
        if not self.api_key:
            raise TinyFishError("TINYFISH_API_KEY is not set (put it in .env)")
        self.h = {"X-API-Key": self.api_key}

    # ---------------- Search ----------------
    def search(self, query: str, **params):
        ck = _key("search", query, params)
        hit = db.cache_get(ck, cache_ttl())
        if hit is not None:
            return hit
        r = requests.get(SEARCH_URL, params={"query": query, **params}, headers=self.h, timeout=30)
        if r.status_code >= 400:
            raise TinyFishError(f"search {r.status_code}: {r.text[:200]}")
        results = r.json().get("results", [])
        db.cache_put(ck, results)
        return results

    # ---------------- Fetch ----------------
    def fetch(self, urls, fresh: bool = False):
        """Returns {url: {'text','final_url','title'} or None}. Per-URL failures give None."""
        if isinstance(urls, str):
            urls = [urls]
        out, todo = {}, []
        for u in urls:
            hit = None if fresh else db.cache_get(_key("fetch", u), cache_ttl())
            if hit is not None:
                out[u] = hit
            else:
                todo.append(u)
        if todo:
            body = {"urls": todo[:10], "format": "markdown"}
            if fresh:
                body["ttl"] = 0
            r = requests.post(FETCH_URL, json=body, headers=self.h, timeout=60)
            if r.status_code >= 400:
                raise TinyFishError(f"fetch {r.status_code}: {r.text[:200]}")
            data = r.json()
            for item in data.get("results", []):
                rec = {
                    "text": item.get("text") if isinstance(item.get("text"), str) else json.dumps(item.get("text")),
                    "final_url": item.get("final_url") or item.get("url"),
                    "title": item.get("title"),
                }
                key_url = item.get("url")
                out[key_url] = rec
                db.cache_put(_key("fetch", key_url), rec)
            for u in todo:
                out.setdefault(u, None)
        return out

    # ---------------- Agent ----------------
    def agent_run(self, url: str, goal: str, max_seconds: int = 90, on_progress=None):
        """Run a web agent. Streams progress when possible, otherwise polls. Returns the result."""
        ck = _key("agent", url, goal)
        hit = db.cache_get(ck, cache_ttl())
        if hit is not None:
            if on_progress:
                on_progress("cached agent result")
            return hit
        body = {"url": url, "goal": goal, "agent_config": {"max_duration_seconds": max_seconds}}
        try:
            result = self._run_sse(body, max_seconds, on_progress)
        except TinyFishError:
            raise
        except Exception as e:  # streaming hiccup -> fall back to async + poll
            if on_progress:
                on_progress("stream dropped, polling instead")
            result = self._run_async(body, max_seconds, on_progress)
        db.cache_put(ck, result)
        return result

    def _run_sse(self, body, max_seconds, on_progress):
        deadline = time.time() + max_seconds + 15
        with requests.post(
            f"{AGENT_BASE}/run-sse", json=body, headers={**self.h, "Accept": "text/event-stream"},
            stream=True, timeout=(15, max_seconds + 30),
        ) as r:
            if r.status_code >= 400:
                raise TinyFishError(f"agent {r.status_code}: {r.text[:200]}")
            for raw in r.iter_lines(decode_unicode=True):
                if time.time() > deadline:
                    raise TinyFishError("agent timed out")
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    ev = json.loads(raw[5:].strip())
                except Exception:
                    continue
                kind = str(ev.get("type") or ev.get("event") or "").upper()
                if kind == "PROGRESS" and on_progress:
                    on_progress(ev.get("purpose") or ev.get("message") or "working")
                elif kind == "STREAMING_URL" and on_progress:
                    on_progress("live view ready", live_url=ev.get("streaming_url") or ev.get("url"))
                elif kind == "COMPLETE":
                    status = str(ev.get("status", "")).upper()
                    if status and status not in ("COMPLETED", "SUCCESS", "SUCCEEDED"):
                        err = (ev.get("error") or {}).get("message") if isinstance(ev.get("error"), dict) else ev.get("error")
                        raise TinyFishError(f"agent ended {status}: {err}")
                    return self._coerce(ev.get("result"))
        raise TinyFishError("agent stream ended without a result")

    def _run_async(self, body, max_seconds, on_progress):
        r = requests.post(f"{AGENT_BASE}/run-async", json=body, headers=self.h, timeout=30)
        if r.status_code >= 400:
            raise TinyFishError(f"agent {r.status_code}: {r.text[:200]}")
        run_id = r.json().get("run_id")
        if not run_id:
            raise TinyFishError("agent returned no run_id")
        end = time.time() + max_seconds + 15
        while time.time() < end:
            time.sleep(3)
            g = requests.get(f"{RUNS_URL}/{run_id}", headers=self.h, timeout=30)
            if g.status_code >= 400:
                continue
            d = g.json()
            st = str(d.get("status", "")).upper()
            if on_progress:
                on_progress(f"run {st.lower()}")
            if st == "COMPLETED":
                return self._coerce(d.get("result"))
            if st in ("FAILED", "CANCELLED"):
                raise TinyFishError(f"agent run {st.lower()}")
        raise TinyFishError("agent timed out")

    @staticmethod
    def _coerce(result):
        if isinstance(result, str):
            s = result.strip()
            try:
                return json.loads(s)
            except Exception:
                a, b = s.find("{"), s.rfind("}")
                if a != -1 and b > a:
                    try:
                        return json.loads(s[a : b + 1])
                    except Exception:
                        pass
        return result
