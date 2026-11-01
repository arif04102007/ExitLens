"""Stage 4: verification in plain code, never AI.

A fact is verified only if
  1. its quote really appears in the page text we fetched, and
  2. its source URL is on the same site as the official page we targeted.
"""
import re

from .textutil import normalize, same_site

MIN_QUOTE_CHARS = 20


def quote_in_text(quote: str, page_text: str) -> bool:
    q = normalize(quote)
    if len(q) < MIN_QUOTE_CHARS:
        return False
    text = normalize(page_text)
    # Allow the model to elide the middle of a long sentence with "..." / "…"
    chunks = [c.strip() for c in re.split(r"\.\.\.|…", q) if c.strip()]
    chunks = [c for c in chunks if len(c) >= 8]
    if not chunks:
        return False
    return all(c in text for c in chunks)


def verify_fact(fact: dict, page_text: str, expected_site_url: str) -> dict:
    ok_quote = quote_in_text(fact.get("quote", ""), page_text)
    ok_domain = same_site(fact.get("source_url", ""), expected_site_url)
    fact["verified"] = bool(ok_quote and ok_domain)
    if not fact["verified"]:
        fact["unverified_reason"] = (
            "quote not found on the page" if not ok_quote else "page is not on the official site"
        )
    return fact
