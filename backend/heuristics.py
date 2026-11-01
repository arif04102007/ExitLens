"""No-AI fallbacks: parse the case text and pull candidate rules out of page text.

These keep the app working when ANTHROPIC_API_KEY is missing. Every fact still
goes through the code verifier, so nothing here can invent a policy.
"""
import re

from .config import case_type_defs, default_country, known_entities
from .textutil import split_sentences


def _get_entities():
    return known_entities()


def _build_case_keywords():
    ct = case_type_defs()
    out = []
    # Check specific sector case types before generic cancellation/delivery
    generic = ("subscription_cancel", "delayed_delivery")
    for k, v in ct.items():
        if k not in ("defective_product",) and k not in generic:
            pat = v.get("keywords", "")
            # Make compound keywords like "flight cancel" flexible with .{0,15} between words
            pat = re.sub(r"\b(flight|train|cab|driver|event|show|order|seller)\s+(cancel\w*|delay\w*)\b", r"\1.{0,15}\2", pat)
            pat = re.sub(r"\b(cancel\w*|delay\w*)\s+(flight|train|cab|driver|event|show|order)\b", r"\1.{0,15}\2", pat)
            out.append((k, pat))
    for k in generic:
        if k in ct:
            out.append((k, ct[k].get("keywords", "")))
    return out



CASE_KEYWORDS = _build_case_keywords()

PRODUCT_NOUNS = (
    r"headphones?|earbuds?|earphones?|neckband|speaker|phone|smartphone|laptop|tablet|watch|smartwatch|"
    r"charger|power ?bank|tv|television|fridge|refrigerator|washing machine|ac|mixer|grinder|camera|"
    r"keyboard|mouse|shoes|jacket|bag|router|monitor|printer|fan|cooler|trimmer|kettle|"
    r"food|order|meal|biryani|pizza|burger|groceries|grocery|"
    r"medicine|medicines|drug|drugs|tablets|pills|"
    r"ticket|tickets|flight|train|booking|hotel|room|ride|cab|"
    r"sofa|couch|bed|mattress|wardrobe|table|chair|desk|furniture|"
    r"sim|broadband|wifi|connection|plan|policy|loan|course"
)

# Load entity categories from known_entities.json
KNOWN_SELLERS = _get_entities().get("sellers", [])
KNOWN_BRANDS = _get_entities().get("brands", [])
KNOWN_SERVICES = _get_entities().get("services", [])
KNOWN_FOOD_DELIVERY = _get_entities().get("food_delivery", [])
KNOWN_TRAVEL = _get_entities().get("travel", [])
KNOWN_RIDE_HAILING = _get_entities().get("ride_hailing", [])
KNOWN_ENTERTAINMENT = _get_entities().get("entertainment", [])
KNOWN_PAYMENTS = _get_entities().get("payments", [])
KNOWN_TELECOM = _get_entities().get("telecom", [])
KNOWN_INSURANCE = _get_entities().get("insurance", [])
KNOWN_BANKING = _get_entities().get("banking", [])
KNOWN_HEALTH = _get_entities().get("health", [])
KNOWN_HOTELS = _get_entities().get("hotels", [])
KNOWN_EDTECH = _get_entities().get("edtech", [])
KNOWN_FURNITURE = _get_entities().get("furniture", [])

_AIRLINES = {"IndiGo", "Air India", "SpiceJet", "Vistara", "Akasa Air", "Air India Express", "Go First", "Alliance Air"}
_RAILWAYS = {"IRCTC", "RailYatri", "ConfirmTkt"}
_OTAS = {"MakeMyTrip", "Goibibo", "EaseMyTrip", "Cleartrip", "Yatra", "RedBus", "AbhiBus"}
_HOTEL_OTAS = {"MakeMyTrip", "Booking.com", "Agoda", "Goibibo", "Yatra", "Airbnb"}


def _find_known(text: str, names):
    low = text.lower()
    for n in sorted(names, key=len, reverse=True):
        if re.search(r"(?<![a-z0-9])" + re.escape(n.lower()) + r"(?![a-z0-9])", low):
            return n
    return None


def parse_case_text(text: str, extra_known=None) -> dict:
    extra_known = extra_known or {}
    t = (text or "").strip()
    low = t.lower()
    case_type = "defective_product"
    for ctype, pat in _build_case_keywords():
        if pat and re.search(pat, low, flags=re.I):
            case_type = ctype
            break

    entities = _get_entities()

    def _cat(key):
        return entities.get(key, []) + extra_known.get(key, [])

    seller = _find_known(t, _cat("sellers"))
    brand = _find_known(t, _cat("brands"))
    service = _find_known(t, _cat("services"))
    food_delivery = _find_known(t, _cat("food_delivery"))
    travel = _find_known(t, _cat("travel"))
    ride_hailing = _find_known(t, _cat("ride_hailing"))
    entertainment = _find_known(t, _cat("entertainment"))
    payments = _find_known(t, _cat("payments"))
    telecom = _find_known(t, _cat("telecom"))
    insurance = _find_known(t, _cat("insurance"))
    banking = _find_known(t, _cat("banking"))
    health = _find_known(t, _cat("health"))
    hotels = _find_known(t, _cat("hotels"))
    edtech = _find_known(t, _cat("edtech"))
    furniture = _find_known(t, _cat("furniture"))

    if not seller:
        m = re.search(
            r"(?:bought|purchased|ordered|got|buy|booked|order|ride|cab|flight)\s+(?:it\s+|this\s+|them\s+)?(?:online\s+)?(?:from|on|at|via|through|with)\s+"
            r"([A-Za-z0-9.&'-]+(?:\s+[A-Za-z0-9.&'-]+)?)", t, flags=re.I)
        if m:
            cand = m.group(1).strip()
            if cand.lower() not in {"a", "an", "the", "my", "some", "two", "three", "few", "days", "weeks", "months", "online", "store", "website", "shop", "app"}:
                seller = cand

    product = None
    m = re.search(r"(?:my|the|a|an)\s+((?:[A-Za-z0-9&'-]+\s+){0,3}?)(" + PRODUCT_NOUNS + r")\b", t, flags=re.I)
    if m:
        product = (m.group(1) + m.group(2)).strip()
        lead = m.group(1).strip()
        if lead and not brand:
            candidate = lead.split()[0]
            if candidate[0].isalpha() and candidate.lower() not in {"new", "old", "broken", "faulty", "bluetooth", "wireless"}:
                brand = lead.strip()
    if brand and product and brand.lower() not in product.lower():
        product = f"{brand} {product}"

    country = default_country()

    if case_type == "subscription_cancel":
        m = re.search(r"cancel(?:ling|ing)?\s+(?:my\s+|the\s+|a\s+)?(.+?)\s+(?:subscription|membership|plan)", t, flags=re.I)
        name = service or (m.group(1).strip() if m else None)
        return {
            "case_type": case_type, "product": name, "brand": name, "seller": name,
            "service": name, "country": country, "missing_info": [] if name else ["Which service or subscription is it?"],
        }

    # Resolve entity roles for case types
    platform = None
    airline = None
    ota = None
    railway = None
    telco = None
    insurer = None
    bank = None
    hotel = None

    if case_type == "food_delivery_issue":
        platform = food_delivery
    elif case_type == "ride_hailing_issue":
        platform = ride_hailing
    elif case_type == "payment_dispute":
        platform = payments or banking
        if banking:
            bank = banking
    elif case_type == "ticket_booking_issue":
        platform = entertainment
    elif case_type == "telecom_issue":
        telco = telecom
    elif case_type == "insurance_claim":
        insurer = insurance
    elif case_type == "banking_dispute":
        bank = banking
    elif case_type == "edtech_refund":
        platform = edtech
    elif case_type == "health_pharma_issue":
        platform = health
    elif case_type == "grocery_delivery_issue":
        platform = food_delivery or seller
    elif case_type == "flight_issue":
        if travel in _AIRLINES:
            airline = travel
        elif travel in _OTAS:
            ota = travel
        else:
            airline = travel
    elif case_type == "train_issue":
        railway = travel if travel in _RAILWAYS else (travel or "IRCTC")
    elif case_type == "hotel_booking_issue":
        if hotels in _HOTEL_OTAS:
            platform = hotels
        else:
            hotel = hotels
    elif case_type == "furniture_delivery_issue":
        if furniture and not seller:
            seller = furniture

    # Ensure main seller/service fallback
    effective_seller = seller or platform or airline or telco or insurer or bank or railway or hotel or service

    # Build missing_info question based on case_type
    missing = []
    if case_type == "food_delivery_issue" and not (platform or effective_seller):
        missing.append("Which food delivery app or restaurant did you order from?")
    elif case_type == "flight_issue" and not (airline or ota or effective_seller):
        missing.append("Which airline or booking platform was your flight with?")
    elif case_type == "ride_hailing_issue" and not (platform or effective_seller):
        missing.append("Which cab or ride service was it (e.g. Uber, Ola, Rapido)?")
    elif case_type == "payment_dispute" and not (platform or bank or effective_seller):
        missing.append("Which payment app or bank was involved?")
    elif case_type == "telecom_issue" and not (telco or effective_seller):
        missing.append("Which telecom or broadband provider is it?")
    elif case_type == "insurance_claim" and not (insurer or effective_seller):
        missing.append("Which insurance company is your policy with?")
    elif case_type == "banking_dispute" and not (bank or effective_seller):
        missing.append("Which bank or financial institution is it?")
    elif case_type == "edtech_refund" and not (platform or effective_seller):
        missing.append("Which edtech platform or coaching institute was it?")
    elif case_type == "hotel_booking_issue" and not (platform or hotel or effective_seller):
        missing.append("Which booking platform or hotel was it?")
    elif case_type == "health_pharma_issue" and not (platform or effective_seller):
        missing.append("Which pharmacy app or health service was it?")
    elif case_type == "grocery_delivery_issue" and not (platform or effective_seller):
        missing.append("Which grocery delivery service was it (e.g. Blinkit, Zepto, BigBasket)?")
    elif case_type == "ticket_booking_issue" and not (platform or effective_seller):
        missing.append("Which ticketing platform was it (e.g. BookMyShow)?")
    elif case_type in ("defective_product", "delayed_delivery", "wrong_item_delivered", "counterfeit_product", "seller_cancelled_order", "furniture_delivery_issue") and not effective_seller:
        missing.append("Where did you buy it (which website or shop)?")

    result = {
        "case_type": case_type,
        "product": product,
        "brand": brand,
        "seller": effective_seller,
        "service": service,
        "country": country,
        "missing_info": missing,
    }
    if platform:
        result["platform"] = platform
    if airline:
        result["airline"] = airline
    if ota:
        result["ota"] = ota
    if railway:
        result["railway"] = railway
    if telco:
        result["telco"] = telco
    if insurer:
        result["insurer"] = insurer
    if bank:
        result["bank"] = bank
    if hotel:
        result["hotel"] = hotel

    return result


# ---------- fact extraction from plain text ----------
_FIELD_RULES = [
    ("return_window", r"\b(return|refund|replace|replacement|exchange)\w*\b.*\b(\d+|one|two|three|seven|ten|fourteen|fifteen|thirty)[\s-]*(business |working )?(day|days|week|weeks)\b"),
    ("warranty_period", r"\bwarrant\w*\b.*\b(\d+|one|two|three)[\s-]*(year|years|month|months)\b|\b(\d+|one|two|three)[\s-]*(year|years|month|months)\b.*\bwarrant\w*\b"),
    ("cancellation_notice", r"\bcancel\w*\b.*\b(\d+|one|two|three|seven|thirty)[\s-]*(day|days|hour|hours|week|weeks)\b"),
    ("proof_required", r"\b(invoice|receipt|proof of purchase|order (id|number)|serial number|bill)\b"),
    ("conditions", r"\b(must|should|only if|provided that|eligible|unused|original packaging|undamaged|in its original)\b"),
    ("exclusions", r"\b(not covered|does not cover|do not cover|excluded|exclusion|not eligible|non-returnable|void|not accepted|cannot be returned)\b"),
    ("claim_route", r"(https?://\S+|\b[\w.+-]+@[\w-]+\.[\w.]+\b|\b(toll[- ]free|call us|contact us|raise a|submit a|start a|initiate)\b)"),
]
_MAX_PER_FIELD = {"conditions": 3, "exclusions": 2, "proof_required": 2, "claim_route": 2}


def _short_value(field: str, sentence: str) -> str:
    if field in ("return_window", "warranty_period", "cancellation_notice"):
        m = re.search(r"((?:\d+|one|two|three|seven|ten|fourteen|fifteen|thirty)[\s-]*(?:business |working )?(?:days?|weeks?|months?|years?|hours?))(\s+(?:of|from|after)\s+(?:the\s+)?(?:date\s+of\s+)?(?:delivery|purchase|receipt|order|billing|renewal|activation|shipping|dispatch))?", sentence, flags=re.I)
        if m:
            return (m.group(1) + (m.group(2) or "")).strip()
    s = sentence.strip()
    return s if len(s) <= 140 else s[:137].rstrip() + "..."


def extract_facts_text(plain: str):
    """Return [{'field','value','quote'}] using simple sentence rules."""
    sentences = [s for s in split_sentences(plain) if 25 <= len(s) <= 420]
    out, counts, seen = [], {}, set()
    for field, pat in _FIELD_RULES:
        rx = re.compile(pat, flags=re.I)
        for s in sentences:
            if counts.get(field, 0) >= _MAX_PER_FIELD.get(field, 2):
                break
            if (field, s) in seen or not rx.search(s):
                continue
            if field == "conditions" and re.search(r"\b\d+\s*(day|days|year|years|month|months)\b", s, flags=re.I):
                continue  # already a window sentence
            seen.add((field, s))
            counts[field] = counts.get(field, 0) + 1
            out.append({"field": field, "value": _short_value(field, s), "quote": s})
    return out


def looks_like_policy(plain: str) -> bool:
    """Cheap test used by the Fetch-first tier: does this page actually state rules?"""
    if len(plain) < 400:
        return False
    low = plain.lower()
    hits = sum(k in low for k in ("return", "refund", "warranty", "cancel", "replacement", "exchange"))
    facts = extract_facts_text(plain)
    windows = [f for f in facts if f["field"] in ("return_window", "warranty_period", "cancellation_notice")]
    return hits >= 2 and len(windows) >= 1
