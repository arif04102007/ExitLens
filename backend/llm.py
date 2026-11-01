"""Claude calls (optional). Every function returns None if there is no key or the call fails,
and the caller falls back to the no-AI heuristics. Claude never sees the open web:
it only reads page text we fetched, and its output is re-checked by the code verifier."""
import json
import re

import requests

from .config import case_type_defs, default_country, env

URL = "https://api.anthropic.com/v1/messages"
FIELDS = "return_window | warranty_period | cancellation_notice | conditions | proof_required | exclusions | claim_route"


def available() -> bool:
    return bool(env("ANTHROPIC_API_KEY"))


def _call(system: str, user: str, max_tokens: int = 2500) -> str:
    r = requests.post(
        URL,
        headers={
            "x-api-key": env("ANTHROPIC_API_KEY"),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": env("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=90,
    )
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", []))


def _json_from(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        a, b = text.find(opener), text.rfind(closer)
        if a != -1 and b > a:
            try:
                return json.loads(text[a : b + 1])
            except Exception:
                continue
    return None


def parse_case(user_text: str, fields: dict):
    if not available():
        return None
    types = list(case_type_defs().keys()) if case_type_defs() else [
        "defective_product", "subscription_cancel", "delayed_delivery", "food_delivery_issue",
        "flight_issue", "train_issue", "ride_hailing_issue", "wrong_item_delivered",
        "payment_dispute", "ticket_booking_issue", "telecom_issue", "insurance_claim",
        "banking_dispute", "edtech_refund", "hotel_booking_issue", "health_pharma_issue",
        "grocery_delivery_issue", "furniture_delivery_issue", "counterfeit_product",
        "seller_cancelled_order"
    ]
    types_str = " | ".join(types)
    country = default_country()
    system = (
        "You read a consumer's complaint and return ONLY JSON with keys: "
        f"case_type ({types_str}), product, brand, seller, "
        f"service (for subscriptions), purchase_date (YYYY-MM-DD or null), country (default {country}), "
        "missing_info (list of short questions, ONLY if the seller/service/platform is truly unknown). "
        "Use null for unknown values. Do not guess."
    )
    try:
        data = _json_from(_call(system, f"Complaint: {user_text}\nOptional fields: {json.dumps(fields)}", 600))
        return data if isinstance(data, dict) else None
    except Exception as e:  # noqa
        print("[llm.parse_case] failed:", e)
        return None


def extract_facts(plain_text: str, party: str, name: str, case_type: str, product: str):
    if not available():
        return None
    system = (
        "You extract consumer-policy rules from ONE web page. Return ONLY JSON: "
        '{"facts":[{"field":"' + FIELDS + '","value":"short plain value","quote":"EXACT sentence copied character-for-character from the page text"}]}. '
        "Rules: only include rules the page explicitly states; never infer or use outside knowledge; "
        "the quote must be copied exactly, no paraphrasing; return {\"facts\":[]} if the page has no relevant policy."
    )
    user = (
        f"Party: {party} ({name}). Case type: {case_type}. Product: {product}.\n"
        f"Extract: time windows, conditions, proof needed, exclusions, and how to start a claim.\n\n"
        f"PAGE TEXT:\n{plain_text[:28000]}"
    )
    try:
        data = _json_from(_call(system, user))
        facts = data.get("facts") if isinstance(data, dict) else None
        if not isinstance(facts, list):
            return None
        return [f for f in facts if isinstance(f, dict) and f.get("quote") and f.get("field")]
    except Exception as e:  # noqa
        print("[llm.extract_facts] failed:", e)
        return None


def chatbot_answer(user_text: str):
    """The 'before' side of the compare panel: what a model says from memory, no sources."""
    if not available():
        return None
    system = (
        "You are a generic assistant answering a consumer question from memory only. "
        "You have no web access. Answer in 4-6 short sentences, confidently, as a typical chatbot would."
    )
    try:
        return _call(system, user_text, 500).strip()
    except Exception as e:  # noqa
        print("[llm.chatbot_answer] failed:", e)
        return None
