"""Central config. Everything comes from environment variables / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def mode() -> str:
    """'live' talks to TinyFish. 'fixture' uses clearly-labelled sample pages (dev only)."""
    return env("EXITLENS_MODE", "live").strip().lower()


def per_site_timeout() -> int:
    return int(env("PER_SITE_TIMEOUT", "90"))


def cache_ttl() -> int:
    """Seconds a cached TinyFish response is reused. 0 disables the cache."""
    return int(env("CACHE_TTL", "21600"))


def db_path() -> str:
    return env("EXITLENS_DB", str(ROOT / "data" / "exitlens.db"))


_data_cache = {}


def _load_json(name: str):
    if name not in _data_cache:
        path = ROOT / "data" / name
        if path.exists():
            import json
            try:
                _data_cache[name] = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                _data_cache[name] = {}
        else:
            _data_cache[name] = {}
    return _data_cache[name]


def known_entities(): return _load_json("known_entities.json")
def brand_aliases(): return _load_json("brand_aliases.json")
def escalation_data(): return _load_json("escalation.json")
def case_type_defs(): return _load_json("case_types.json")
def default_country(): return env("DEFAULT_COUNTRY", "India")
def disclaimer(): return env("DISCLAIMER_TEXT", "Guidance only, not legal advice. ExitLens never pays, cancels or submits anything for you.")
def min_complaint_length(): return int(env("MIN_COMPLAINT_LENGTH", "8"))

