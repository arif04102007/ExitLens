"""Text helpers shared by extraction and verification."""
import re
import unicodedata
from urllib.parse import urlparse

_MULTI_TLD = {"co.in", "co.uk", "com.au", "co.jp", "com.br", "co.nz", "org.in", "net.in", "gov.in", "co.za"}


def strip_markdown(md: str) -> str:
    """Turn fetched markdown into plain text. Links keep their URL: 'text (url)'."""
    t = md or ""
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)  # images
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)[^)]*\)", r"\1 (\2)", t)  # links
    t = re.sub(r"^[ \t]*[#>]+[ \t]*", "", t, flags=re.M)  # headings, quotes
    t = re.sub(r"^[ \t]*[-*+•][ \t]+", "", t, flags=re.M)  # bullets
    t = re.sub(r"[*_`|]+", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def normalize(s: str) -> str:
    """Normalisation used when comparing a quote with page text."""
    s = unicodedata.normalize("NFKC", s or "")
    s = (
        s.replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("–", "-").replace("—", "-").replace(" ", " ")
    )
    s = re.sub(r"[*_`#>|]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().casefold()


def split_sentences(plain: str):
    parts = re.split(r"(?<=[.!?])\s+|\n+", plain)
    return [p.strip() for p in parts if p and p.strip()]


def host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def registrable(host: str) -> str:
    host = host.lower().lstrip(".")
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in _MULTI_TLD:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def same_site(a: str, b: str) -> bool:
    ha, hb = host_of(a), host_of(b)
    return bool(ha) and bool(hb) and registrable(ha) == registrable(hb)
