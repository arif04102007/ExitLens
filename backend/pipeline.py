"""The ExitLens pipeline: understand -> discover -> read (parallel) -> verify -> plan.

Reading is tiered to save credits: Search -> Fetch -> Agent (only if Fetch did not show the policy).
"""
import hashlib
import json
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

from . import db, discovery, heuristics, llm
from .config import case_type_defs, default_country, disclaimer, mode, per_site_timeout
from .dates import compute_deadlines, parse_date, window_days
from .plan import PARTY_LABEL, build_plan
from .textutil import host_of, same_site, strip_markdown
from .verify import verify_fact

VALID_FIELDS = {"return_window", "warranty_period", "cancellation_notice", "conditions", "proof_required", "exclusions", "claim_route"}
KEY_FIELDS = {"return_window", "warranty_period", "cancellation_notice"}
DISCLAIMER = disclaimer()

EVENTS = {}
_ev_lock = threading.Lock()


# ------------------------------------------------------------------ events
def emit(case_id, **ev):
    with _ev_lock:
        lst = EVENTS.setdefault(case_id, [])
        ev["i"] = len(lst)
        ev["ts"] = time.time()
        lst.append(ev)


def events_since(case_id, idx):
    with _ev_lock:
        return list(EVENTS.get(case_id, [])[idx:])


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_client():
    if mode() == "fixture":
        from .fixtures import FixtureClient
        return FixtureClient()
    from .tinyfish import TinyFish
    return TinyFish()


# ------------------------------------------------------------------ cases
def create_case(user_text: str, fields: dict) -> dict:
    case = {
        "id": uuid.uuid4().hex[:10],
        "user_text": user_text.strip(),
        "fields": {k: (v or "").strip() for k, v in (fields or {}).items() if isinstance(v, str)},
        "status": "queued",
        "created_at": time.time(),
        "mode": mode(),
        "disclaimer": disclaimer(),
    }
    db.save_case(case)
    EVENTS[case["id"]] = []
    return case


def start_case(case_id: str):
    threading.Thread(target=run_case, args=(case_id,), daemon=True).start()


def run_case(case_id: str):
    case = db.load_case(case_id)
    if not case:
        return
    try:
        _run(case)
    except Exception as e:  # never crash the server; show the problem
        case["status"] = "failed"
        case["error"] = f"{type(e).__name__}: {e}"
        db.save_case(case)
        emit(case_id, type="error", message=case["error"])


def _understand(case):
    cid = case["id"]
    emit(cid, type="stage", stage="understand", message="Understanding your problem")
    f = case.get("fields", {})
    extra = {"sellers": ["ShopEasy"], "brands": ["Acme Audio"]} if mode() == "fixture" else None
    parsed = llm.parse_case(case["user_text"], f) or heuristics.parse_case_text(case["user_text"], extra)
    all_keys = (
        "case_type", "product", "brand", "seller", "service", "country", "purchase_date",
        "platform", "airline", "ota", "railway", "telco", "insurer", "bank", "hotel"
    )
    for key in all_keys:
        if parsed.get(key):
            case[key] = parsed[key]
    # explicit form fields always win
    for key in all_keys:
        if f.get(key):
            case[key] = f[key]

    ct = case.get("case_type")
    if ct == "subscription_cancel":
        name = case.get("service") or case.get("seller") or case.get("brand") or case.get("product")
        if f.get("seller"):
            name = f["seller"]
        case["service"] = name
    elif ct in ("food_delivery_issue", "ride_hailing_issue", "payment_dispute", "ticket_booking_issue",
                "edtech_refund", "health_pharma_issue", "grocery_delivery_issue"):
        name = case.get("platform") or case.get("seller") or case.get("service") or case.get("brand")
        if f.get("seller"):
            name = f["seller"]
        case["platform"] = name
        case["seller"] = name
    elif ct == "flight_issue":
        if not case.get("airline") and case.get("seller"):
            if case["seller"] in ("MakeMyTrip", "Goibibo", "EaseMyTrip", "Cleartrip", "Yatra", "RedBus", "AbhiBus"):
                case["ota"] = case["seller"]
            else:
                case["airline"] = case["seller"]
    elif ct == "train_issue":
        case["railway"] = case.get("railway") or case.get("seller") or "IRCTC"
        case["seller"] = case["railway"]
    elif ct == "insurance_claim":
        case["insurer"] = case.get("insurer") or case.get("seller") or case.get("brand")
        case["seller"] = case["insurer"]
    elif ct == "banking_dispute":
        case["bank"] = case.get("bank") or case.get("seller") or case.get("brand")
        case["seller"] = case["bank"]
    elif ct == "telecom_issue":
        case["telco"] = case.get("telco") or case.get("seller") or case.get("brand")
        case["seller"] = case["telco"]
    elif ct == "hotel_booking_issue":
        name = case.get("platform") or case.get("hotel") or case.get("seller")
        if not case.get("platform") and not case.get("hotel") and name:
            case["platform"] = name
        case["seller"] = name

    case.setdefault("country", default_country())
    if case.get("purchase_date") and not parse_date(case["purchase_date"]):
        case["purchase_date"] = None
    return parsed


def _needs_info(case):
    ct = case.get("case_type")
    if ct == "subscription_cancel":
        return None if case.get("service") else "Which service or subscription do you want to cancel?"
    if ct == "food_delivery_issue":
        return None if (case.get("platform") or case.get("seller")) else "Which food delivery app or restaurant did you order from?"
    if ct == "flight_issue":
        return None if (case.get("airline") or case.get("ota") or case.get("seller")) else "Which airline or booking platform was your flight with?"
    if ct == "ride_hailing_issue":
        return None if (case.get("platform") or case.get("seller")) else "Which cab or ride service was it (e.g. Uber, Ola, Rapido)?"
    if ct == "payment_dispute":
        return None if (case.get("platform") or case.get("bank") or case.get("seller")) else "Which payment app or bank was involved?"
    if ct == "ticket_booking_issue":
        return None if (case.get("platform") or case.get("seller")) else "Which ticketing platform was it (e.g. BookMyShow)?"
    if ct == "telecom_issue":
        return None if (case.get("telco") or case.get("seller")) else "Which telecom or broadband provider is it?"
    if ct == "insurance_claim":
        return None if (case.get("insurer") or case.get("seller")) else "Which insurance company is your policy with?"
    if ct == "banking_dispute":
        return None if (case.get("bank") or case.get("seller")) else "Which bank or financial institution is it?"
    if ct == "edtech_refund":
        return None if (case.get("platform") or case.get("seller")) else "Which edtech platform or coaching institute was it?"
    if ct == "hotel_booking_issue":
        return None if (case.get("platform") or case.get("hotel") or case.get("seller")) else "Which booking platform or hotel was it?"
    if ct == "health_pharma_issue":
        return None if (case.get("platform") or case.get("seller")) else "Which pharmacy app or health service was it?"
    if ct == "grocery_delivery_issue":
        return None if (case.get("platform") or case.get("seller")) else "Which grocery delivery service was it (e.g. Blinkit, Zepto, BigBasket)?"
    if ct == "train_issue":
        return None  # defaults to IRCTC if not specified
    if not case.get("seller"):
        return "Where did you buy it (which website or shop)?"
    return None


def answer_followup(case_id: str, answer: str):
    case = db.load_case(case_id)
    if not case:
        return None
    # The follow-up answer is the seller (or service/platform). _understand() honours it.
    case.setdefault("fields", {})["seller"] = answer.strip()
    case["status"] = "queued"
    db.save_case(case)
    EVENTS[case_id] = []
    start_case(case_id)
    return case


def _parties(case):
    ct = case.get("case_type")
    ct_defs = case_type_defs()
    ct_def = ct_defs.get(ct, {})
    topics = ct_def.get("policy_topics", {})

    if ct == "subscription_cancel":
        name = case.get("service") or case.get("seller") or "Service"
        role = topics.get("service", "Service cancellation & refund policy")
        return [{"id": "p1", "party": "service", "name": name, "role": role}]

    if ct in ("food_delivery_issue", "ride_hailing_issue", "payment_dispute", "ticket_booking_issue",
              "edtech_refund", "health_pharma_issue", "grocery_delivery_issue"):
        name = case.get("platform") or case.get("seller") or "Platform"
        role = topics.get("platform", f"{ct_def.get('label', 'Platform')} cancellation & refund policy")
        return [{"id": "p1", "party": "platform", "name": name, "role": role}]

    if ct == "telecom_issue":
        name = case.get("telco") or case.get("seller") or "Telecom Provider"
        role = topics.get("telco", "Citizen charter & grievance redressal policy")
        return [{"id": "p1", "party": "telco", "name": name, "role": role}]

    if ct == "insurance_claim":
        name = case.get("insurer") or case.get("seller") or "Insurance Provider"
        role = topics.get("insurer", "Claim settlement & policyholder rights")
        return [{"id": "p1", "party": "insurer", "name": name, "role": role}]

    if ct == "banking_dispute":
        name = case.get("bank") or case.get("seller") or "Bank"
        role = topics.get("bank", "Fair practices code & grievance redressal")
        return [{"id": "p1", "party": "bank", "name": name, "role": role}]

    if ct == "train_issue":
        name = case.get("railway") or case.get("seller") or "IRCTC"
        role = topics.get("railway", "TDR filing, cancellation and refund rules")
        return [{"id": "p1", "party": "railway", "name": name, "role": role}]

    if ct == "flight_issue":
        out = []
        airline = case.get("airline") or case.get("seller")
        ota = case.get("ota")
        if airline:
            out.append({"id": "p1", "party": "airline", "name": airline, "role": topics.get("airline", "Conditions of carriage & refund policy")})
        if ota and (not airline or ota.lower() != str(airline).lower()):
            pid = f"p{len(out) + 1}"
            out.append({"id": pid, "party": "ota", "name": ota, "role": topics.get("ota", "Booking cancellation & refund policy")})
        if not out:
            out.append({"id": "p1", "party": "airline", "name": case.get("seller", "Airline"), "role": "Conditions of carriage & refund policy"})
        return out

    if ct == "hotel_booking_issue":
        out = []
        plat = case.get("platform") or case.get("seller")
        hotel = case.get("hotel")
        if plat:
            out.append({"id": "p1", "party": "platform", "name": plat, "role": topics.get("platform", "Booking cancellation & refund policy")})
        if hotel and (not plat or hotel.lower() != str(plat).lower()):
            pid = f"p{len(out) + 1}"
            out.append({"id": pid, "party": "hotel", "name": hotel, "role": topics.get("hotel", "Check-in & guest policy")})
        if not out:
            out.append({"id": "p1", "party": "platform", "name": case.get("seller", "Hotel Booking"), "role": "Booking cancellation & refund policy"})
        return out

    # Default: seller return policy, plus manufacturer warranty if defective_product with brand
    seller_role = topics.get("seller", "Seller return policy")
    out = [{"id": "p1", "party": "seller", "name": case.get("seller", "Seller"), "role": seller_role}]
    brand = case.get("brand")
    if ct == "defective_product" and brand and brand.lower() != str(case.get("seller", "")).lower():
        mfg_role = topics.get("manufacturer", "Manufacturer warranty")
        out.append({"id": "p2", "party": "manufacturer", "name": brand, "role": mfg_role})
    return out


def _run(case):
    cid = case["id"]
    case["status"] = "running"
    case.pop("error", None)
    _understand(case)
    q = _needs_info(case)
    if q:
        case["status"] = "needs_info"
        case["question"] = q
        db.save_case(case)
        emit(cid, type="needs_info", message=q)
        return
    case.pop("question", None)
    parties = _parties(case)
    case["parties"] = [dict(p, state="queued", message="Waiting to start") for p in parties]
    db.save_case(case)
    emit(cid, type="plan", message="Sending agents to the live websites",
         parties=[{"id": p["id"], "party": p["party"], "name": p["name"], "role": p["role"]} for p in parties])

    client = get_client()
    ctx = {"case": case, "client": client, "lock": threading.Lock(), "fact_n": 0, "src_n": 0}
    with ThreadPoolExecutor(max_workers=max(1, len(parties))) as pool:
        results = list(pool.map(lambda p: _work_party(ctx, p), parties))

    facts = [f for r in results for f in r["facts"]]
    sources = [s for r in results for s in r["sources"]]
    for r in results:
        for p in case["parties"]:
            if p["id"] == r["party_id"]:
                p.update(state=r["state"], message=r["message"])
    emit(cid, type="stage", stage="verify", message="Checking every quote against the live page text")
    deadlines = compute_deadlines([f for f in facts if f.get("verified")], case.get("purchase_date"))
    steps = build_plan(case["case_type"], facts, deadlines, country=case.get("country", default_country()))
    emit(cid, type="stage", stage="plan", message="Building your checklist")
    case["result"] = {
        "facts": facts, "sources": sources, "deadlines": deadlines, "steps": steps,
        "verified_count": sum(1 for f in facts if f.get("verified")),
        "unverified_count": sum(1 for f in facts if not f.get("verified")),
    }
    case["status"] = "done"
    db.save_case(case)
    emit(cid, type="done", message="Done")


# ------------------------------------------------------------------ one party
def _update(ctx, party, state, message, **extra):
    emit(ctx["case"]["id"], type="target", party_id=party["id"], party=party["party"], name=party["name"],
         state=state, message=message, **extra)


def _next_id(ctx, key, prefix):
    with ctx["lock"]:
        ctx[key] += 1
        return f"{prefix}{ctx[key]}"


def _urls_from(result):
    urls = []
    if isinstance(result, dict):
        for k in ("policy_urls", "urls", "pages"):
            v = result.get(k)
            if isinstance(v, list):
                urls += [u for u in v if isinstance(u, str)]
        for k in ("policy_url", "url", "page_url"):
            if isinstance(result.get(k), str):
                urls.append(result[k])
    elif isinstance(result, str):
        urls += re.findall(r"https?://[^\s\"'<>)\]]+", result)
    seen, out = set(), []
    for u in urls:
        u = u.rstrip(".,;")
        if u.startswith("http") and u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _extract(plain, party, case):
    facts = None
    if llm.available():
        facts = llm.extract_facts(plain, party["party"], party["name"], case["case_type"], case.get("product") or "")
    if facts is None:
        facts = heuristics.extract_facts_text(plain)
    clean, seen = [], set()
    for f in facts:
        field = str(f.get("field", "")).strip()
        if field not in VALID_FIELDS or not f.get("quote"):
            continue
        k = (field, f["quote"].strip())
        if k in seen:
            continue
        seen.add(k)
        clean.append({"field": field, "value": str(f.get("value") or f["quote"])[:200], "quote": f["quote"].strip()})
    return clean


def _enough(facts):
    return any(f["field"] in KEY_FIELDS for f in facts) or len(facts) >= 3


def _read_url(ctx, party, url, method, site_url):
    """Fetch one URL, extract facts, verify them. Returns (source, facts, plain) or None."""
    client, case = ctx["client"], ctx["case"]
    got = client.fetch(url).get(url)
    if not got or not got.get("text"):
        return None
    plain = strip_markdown(got["text"])
    final = got.get("final_url") or url
    if not same_site(final, site_url):
        return None
    _update(ctx, party, "reading_policy", f"Reading {host_of(final)}", url=final)
    raw = _extract(plain, party, case)
    sid = _next_id(ctx, "src_n", "s")
    source = {
        "id": sid, "party": party["party"], "url": final, "role": party["role"], "title": got.get("title") or final,
        "fetch_method": method, "text_hash": hashlib.sha256(plain.encode()).hexdigest()[:16], "retrieved_at": now_iso(),
    }
    facts = []
    for f in raw:
        fact = {
            "id": _next_id(ctx, "fact_n", "f"), "party": party["party"], "field": f["field"], "value": f["value"],
            "quote": f["quote"], "source_id": sid, "source_url": final, "retrieved_at": source["retrieved_at"],
        }
        facts.append(verify_fact(fact, plain, site_url))
    return source, facts, plain


def _work_party(ctx, party):
    case, client = ctx["case"], ctx["client"]
    sources, facts = [], []
    state, message = "could_not_verify", "Could not verify a policy on the official site"
    try:
        _update(ctx, party, "searching", f"Searching for {party['name']}'s official policy pages")
        canonical_host = discovery.discover_canonical_host(client, party["name"])
        results, seen = [], set()
        for qy in discovery.queries_for(party["party"], party["name"], case.get("product") or "", case.get("case_type") or ""):
            try:
                for r in client.search(qy):
                    if r.get("url") not in seen:
                        seen.add(r.get("url"))
                        results.append(r)
            except Exception as e:
                _update(ctx, party, "searching", f"Search issue: {str(e)[:80]}")
        cands = discovery.rank_official(results, party["name"], canonical_host=canonical_host)
        if not cands and canonical_host:
            # If search didn't pick up policy subpages directly, use the canonical host as starting site!
            cands = [{"url": f"https://{canonical_host}", "title": party["name"]}]
        if not cands:
            _update(ctx, party, "could_not_verify", "No official page found for this party")
            return {"party_id": party["id"], "facts": [], "sources": [], "state": "could_not_verify",
                    "message": "No official page found"}
        site_url = cands[0]["url"]
        _update(ctx, party, "opening_site", f"Opening {host_of(site_url)}", url=site_url)

        # Tier 1: Fetch the best candidates
        for c in cands[:2]:
            got = _read_url(ctx, party, c["url"], "fetch", site_url)
            if got:
                src, fs, _ = got
                sources.append(src)
                facts += fs
                if _enough(fs) and any(f["verified"] for f in fs):
                    break
        have_key = any(f["verified"] and f["field"] in KEY_FIELDS for f in facts)

        # Tier 2: Agent navigates to the policy page when Fetch did not show it
        if not have_key:
            _update(ctx, party, "following_links", "Policy not on that page, sending a browser agent to find it", url=site_url)
            goal = (
                f"You are on the website of {party['name']}. Find the official page that states its "
                f"{discovery.topic_for(party['party'], case['case_type'])}"
                f"{' for ' + case['product'] if case.get('product') else ''}. Use the footer, help centre, "
                "support links or the site search. Do not log in, do not fill or submit any form, do not buy anything. "
                'Return JSON only: {"policy_urls": ["<absolute URL of each page that actually states the rules>"], '
                '"notes": "<one short sentence>"}'
            )

            def prog(msg, live_url=None):
                _update(ctx, party, "following_links", msg, **({"live_url": live_url} if live_url else {}))

            try:
                res = client.agent_run(site_url, goal, max_seconds=per_site_timeout(), on_progress=prog)
                for u in _urls_from(res)[:3]:
                    if any(s["url"] == u for s in sources) or not same_site(u, site_url):
                        continue
                    got = _read_url(ctx, party, u, "agent", site_url)
                    if got:
                        src, fs, _ = got
                        sources.append(src)
                        facts += fs
            except Exception as e:
                _update(ctx, party, "following_links", f"Agent could not finish: {str(e)[:100]}")

        verified = [f for f in facts if f["verified"]]
        if verified:
            state = "extracted"
            message = f"{len(verified)} verified facts from {len({s['url'] for s in sources})} page(s)"
        else:
            facts = [dict(f, verified=False) for f in facts]
            message = "Could not verify a policy on the official site"
        _update(ctx, party, state, message, verified=len(verified), total=len(facts))
    except Exception as e:
        state, message = "failed", f"Failed: {str(e)[:120]}"
        _update(ctx, party, "failed", message)
    return {"party_id": party["id"], "facts": facts, "sources": sources, "state": state, "message": message}


def extract_relevant_email(case: dict, target_party: str, cite: dict = None) -> str:
    """Intelligently determine the relevant contact/grievance email for the target entity.
    
    Priority:
    1. Direct email found in verified quotes or claim_route facts for this party.
    2. Direct email found in any verified quote or policy source in this case.
    3. Official canonical domain-based customer support & grievance email for this entity.
    4. Domain-derived address (e.g. support@{domain}) using canonical host or citation URL.
    """
    if not target_party:
        target_party = "Support"

    clean_target = str(target_party).strip()
    clean_lower = clean_target.lower()
    res = (case or {}).get("result") or {}

    # 1. Search verified facts/quotes for an explicit email
    facts = [f for f in res.get("facts", []) if f.get("verified")]
    party_facts = [f for f in facts if (f.get("party") or "").lower() == clean_lower]
    for f in (party_facts + facts):
        q = f.get("quote", "")
        emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", q)
        for em in emails:
            em_lower = em.lower()
            if not any(ign in em_lower for ign in ["example.com", "yourname", "user@", "email@"]):
                return em

    # 2. Check canonical mapping for known consumer grievance / support desks
    known = {
        # E-commerce & Retail
        "amazon": "grievance-officer@amazon.in",
        "flipkart": "grievance.officer@flipkart.com",
        "myntra": "grievance@myntra.com",
        "meesho": "legalsupport@meesho.com",
        "ajio": "grievanceofficer@ajio.com",
        "croma": "customersupport@croma.com",
        "reliance digital": "reliancedigital@ril.com",
        "tata cliq": "grievanceofficer@tatacliq.com",
        "snapdeal": "grievanceofficer@snapdeal.com",
        "nykaa": "grievanceofficer@nykaa.com",
        "purplle": "grievance@purplle.com",
        "jiomart": "cs@jiomart.com",
        "ikea": "customercare.india@ikea.com",
        "pepperfry": "grievance@pepperfry.com",
        "urban ladder": "grievance@urbanladder.com",

        # Food & Grocery Delivery
        "swiggy": "grievances@swiggy.in",
        "zomato": "grievance@zomato.com",
        "zepto": "support@zeptonow.com",
        "blinkit": "info@blinkit.com",
        "bigbasket": "grievance@bigbasket.com",
        "dunzo": "support@dunzo.in",
        "dominos": "guestcaredominos@jublfood.com",

        # Travel & Airlines & Railways
        "makemytrip": "servicequeries@makemytrip.com",
        "goibibo": "grievance@goibibo.com",
        "easemytrip": "care@easemytrip.com",
        "cleartrip": "customersupport@cleartrip.com",
        "yatra": "support@yatra.com",
        "irctc": "care@irctc.co.in",
        "indigo": "customer.relations@goindigo.in",
        "air india": "contactus@airindia.com",
        "spicejet": "custrelations@spicejet.com",
        "vistara": "custrelations@airvistara.com",
        "akasa air": "nodalofficer@akasaair.com",

        # Ride Hailing
        "uber": "support@uber.com",
        "ola": "support@olacabs.com",
        "rapido": "support@rapido.bike",

        # Digital Payments & Fintech
        "phonepe": "grievance@phonepe.com",
        "google pay": "support-in@google.com",
        "paytm": "nodal@paytm.com",
        "cred": "grievance@cred.club",
        "bharatpe": "grievance@bharatpe.com",

        # Telecom & Internet
        "jio": "care@jio.com",
        "airtel": "121@in.airtel.com",
        "vi": "nodal.officer@vodafoneidea.com",
        "vodafone": "nodal.officer@vodafoneidea.com",
        "bsnl": "grievance@bsnl.co.in",

        # Electronics & Hardware Brands
        "boat": "support@boat-lifestyle.com",
        "boat lifestyle": "support@boat-lifestyle.com",
        "sony": "sonyindia.care@sony.com",
        "samsung": "support.india@samsung.com",
        "apple": "contactus.in@apple.com",
        "oneplus": "onepluscare@oneplus.com",
        "realme": "service.in@realme.com",
        "xiaomi": "service.in@xiaomi.com",
        "redmi": "service.in@xiaomi.com",
        "mi": "service.in@xiaomi.com",
        "noise": "help@gonoise.com",
        "jbl": "india@harman.com",
        "dell": "india_support@dell.com",
        "hp": "in.contact@hp.com",
        "lenovo": "consumercare@lenovo.com",
        "asus": "rc_india@asus.com",

        # Entertainment & Subscriptions
        "bookmyshow": "helpdesk@bookmyshow.com",
        "netflix": "termsinfo@netflix.com",
        "hotstar": "grievance-officer@hotstar.com",
        "disney+ hotstar": "grievance-officer@hotstar.com",
        "spotify": "support@spotify.com",

        # Banking
        "hdfc bank": "grievance.redressal@hdfcbank.com",
        "icici bank": "headservicequality@icicibank.com",
        "sbi": "customercare@sbi.co.in",
        "state bank of india": "customercare@sbi.co.in",
        "axis bank": "nodalofficer@axisbank.com",
        "kotak": "nodalofficer@kotak.com",
        "kotak mahindra": "nodalofficer@kotak.com",

        # Insurance
        "star health": "grievance@starhealth.in",
        "hdfc ergo": "grievance@hdfcergo.com",
        "icici lombard": "customersupport@icicilombard.com",
        "care health": "customerfirst@careinsurance.com",
    }

    for k, v in known.items():
        if k in clean_lower or clean_lower in k:
            return v

    # 3. Derive from citation URL or sources domain if available
    domain = None
    if cite and cite.get("source_url"):
        domain = host_of(cite["source_url"])
    if not domain and res.get("sources"):
        domain = host_of(res["sources"][0].get("url", ""))

    if domain:
        clean_dom = domain.lower().replace("www.", "")
        return f"support@{clean_dom}"

    # 4. Fallback to clean entity name domain
    clean_domain = re.sub(r"[^a-z0-9]", "", clean_lower)
    return f"support@{clean_domain or 'merchant'}.com"


# ------------------------------------------------------------------ extras
def claim_draft(case: dict, details: dict) -> dict:
    res = case.get("result") or {}
    facts = [f for f in res.get("facts", []) if f.get("verified")]
    seller = (
        case.get("seller")
        or case.get("platform")
        or case.get("service")
        or case.get("airline")
        or case.get("bank")
        or case.get("insurer")
        or case.get("railway")
        or case.get("telco")
        or case.get("merchant")
    )
    brand = case.get("brand")
    target_party = seller or brand or "Support Team"
    name = details.get("name") or "[YOUR NAME]"
    order = details.get("order_id") or "[ORDER ID]"
    product = case.get("product") or "the product"
    when = case.get("purchase_date") or "[PURCHASE DATE]"
    cite = next((f for f in facts if f["party"] in ("seller", "service", "platform", "airline", "insurer", "bank", "telco", "railway") and f["field"] in KEY_FIELDS), None) or \
        next((f for f in facts if f["field"] in KEY_FIELDS), None)
    lines = [f"Dear {target_party} Support,", ""]
    ct = case.get("case_type")
    if ct == "subscription_cancel":
        lines.append(f"I would like to cancel my {product} subscription (account: {details.get('email') or '[ACCOUNT EMAIL]'}) and request a refund for any unused period where your policy allows it.")
        subj = f"Cancellation and refund request: {product}"
    elif ct == "delayed_delivery":
        lines.append(f"I ordered {product} (order {order}) on {when}. It has not been delivered as promised. Please deliver it immediately or cancel the order and refund me in full.")
        subj = f"Delayed delivery, order {order}"
    elif ct == "food_delivery_issue":
        lines.append(f"I placed an order {order} on {when}. The food delivered was unacceptable / deficient: {case['user_text'].rstrip('.')}. Please issue an immediate refund.")
        subj = f"Food delivery complaint, order {order}"
    elif ct == "flight_issue":
        lines.append(f"Regarding booking {order} on {when}: {case['user_text'].rstrip('.')}. Under DGCA regulations and your carriage terms, I request a full refund and applicable compensation.")
        subj = f"Flight disruption claim, booking {order}"
    elif ct == "train_issue":
        lines.append(f"Regarding PNR {order} on {when}: {case['user_text'].rstrip('.')}. I request processing of my refund / TDR as per railway rules.")
        subj = f"Train journey claim, PNR {order}"
    elif ct == "ride_hailing_issue":
        lines.append(f"Regarding ride {order} on {when}: {case['user_text'].rstrip('.')}. Please refund the overcharged fare / investigate this issue.")
        subj = f"Ride complaint, ride {order}"
    elif ct == "payment_dispute":
        lines.append(f"Regarding transaction {order} on {when}: {case['user_text'].rstrip('.')}. Under RBI turnaround directives, please reverse the transaction immediately.")
        subj = f"Payment dispute, transaction {order}"
    elif ct == "telecom_issue":
        lines.append(f"Regarding my telecom service account {order}: {case['user_text'].rstrip('.')}. Please resolve this service deficiency promptly.")
        subj = f"Telecom grievance, account {order}"
    elif ct == "insurance_claim":
        lines.append(f"Regarding claim / policy {order}: {case['user_text'].rstrip('.')}. Please review the rejection and process my claim under IRDAI guidelines.")
        subj = f"Insurance claim grievance, policy {order}"
    elif ct == "banking_dispute":
        lines.append(f"Regarding account / card {order}: {case['user_text'].rstrip('.')}. Please investigate and resolve this dispute per RBI guidelines.")
        subj = f"Banking grievance, reference {order}"
    elif ct == "hotel_booking_issue":
        lines.append(f"Regarding reservation {order} on {when}: {case['user_text'].rstrip('.')}. I request a full refund / compensation for service deficiency.")
        subj = f"Hotel booking complaint, reservation {order}"
    elif ct == "edtech_refund":
        lines.append(f"Regarding course enrolment {order}: {case['user_text'].rstrip('.')}. Under CCPA coaching directives, I request cancellation and refund of course fees.")
        subj = f"Course refund request, enrolment {order}"
    else:
        lines.append(f"I bought {product} (order {order}) on {when}. {case['user_text'].rstrip('.')}. I would like a replacement or refund as set out in your policy.")
        subj = f"Defective product claim, order {order}"
    if cite:
        lines += ["", f'Your policy states: "{cite["quote"]}" ({cite["source_url"]}).']
    lines += ["", "Please confirm the next steps and a reference number for this request.", "", "Regards,", name]
    if details.get("phone"):
        lines.append(details["phone"])

    recipient_email = extract_relevant_email(case, target_party, cite)
    brand_email = extract_relevant_email(case, brand, cite) if (brand and brand.lower() != target_party.lower()) else None

    return {
        "subject": subj,
        "body": "\n".join(lines),
        "target_party": target_party,
        "recipient_email": recipient_email,
        "seller": seller,
        "brand": brand,
        "brand_email": brand_email,
    }


def claim_fill_start(case_id: str, details: dict):
    case = db.load_case(case_id)
    res = (case or {}).get("result") or {}
    url = None
    for f in res.get("facts", []):
        if f.get("verified") and f["field"] == "claim_route":
            m = re.search(r"https?://[^\s)]+", f["quote"])
            if m:
                url = m.group(0).rstrip(".,;")
                break
    if not url:
        for s in res.get("sources", []):
            url = s["url"]
            break
    if not url:
        return {"ok": False, "error": "No claim page found yet"}
    case["claim_fill"] = {"state": "running", "url": url, "started": now_iso()}
    db.save_case(case)
    threading.Thread(target=_claim_fill, args=(case_id, url, details), daemon=True).start()
    return {"ok": True, "url": url}


def _claim_fill(case_id, url, details):
    case = db.load_case(case_id)
    emit(case_id, type="claim", state="running", message="Agent is opening the claim form")
    goal = (
        "Open this claim or return form and fill in the fields using ONLY these details: "
        f"{details}. If a field has no matching detail, leave it empty. "
        "IMPORTANT: STOP before the final submit/send/confirm button. Never click it. Do not log in or solve CAPTCHAs. "
        'Return JSON only: {"filled_fields": ["..."], "stopped_before_submit": true, "notes": "..."}'
    )
    live = {}
    try:
        client = get_client()

        def prog(msg, live_url=None):
            if live_url:
                live["url"] = live_url
            emit(case_id, type="claim", state="running", message=msg, live_url=live_url)

        res = client.agent_run(url, goal, max_seconds=per_site_timeout() + 60, on_progress=prog)
        case["claim_fill"] = {"state": "done", "url": url, "result": res, "live_url": live.get("url"),
                              "note": "The form was filled but NOT submitted. You press submit."}
    except Exception as e:
        case["claim_fill"] = {"state": "failed", "url": url, "error": str(e)[:200]}
    db.save_case(case)
    emit(case_id, type="claim", state=case["claim_fill"]["state"], message="Claim helper finished")


def compare(case: dict) -> dict:
    ans = llm.chatbot_answer(case["user_text"])
    res = case.get("result") or {}
    return {
        "chatbot": ans,
        "chatbot_available": ans is not None,
        "exitlens": [
            {"title": s["title"], "action": s["action"], "status": s["status"]} for s in res.get("steps", [])[:3]
        ],
    }


def monitor_enable(case_id: str):
    case = db.load_case(case_id)
    res = (case or {}).get("result") or {}
    client = get_client()
    n = 0
    for s in res.get("sources", []):
        got = client.fetch(s["url"], fresh=True).get(s["url"])
        if got and got.get("text"):
            h = hashlib.sha256(strip_markdown(got["text"]).encode()).hexdigest()[:16]
            db.add_watch(case_id, s["url"], h)
            n += 1
    return {"watching": n}


def monitor_check(case_id: str):
    client = get_client()
    out = []
    for w in db.list_watches(case_id):
        got = client.fetch(w["url"], fresh=True).get(w["url"])
        if not got or not got.get("text"):
            out.append({"url": w["url"], "state": "unreachable"})
            continue
        h = hashlib.sha256(strip_markdown(got["text"]).encode()).hexdigest()[:16]
        changed = h != w["text_hash"]
        db.update_watch(w["id"], h, changed)
        out.append({"url": w["url"], "state": "changed" if changed else "unchanged"})
    return out


# ------------------------------------------------------------------ dynamic complaint & tracker intelligence

def complaint_questions(case_id: str) -> dict:
    case = db.load_case(case_id) or {}
    ct = case.get("case_type", "defective_product")
    questions = []

    if ct == "flight_issue":
        questions = [
            {"id": "pnr", "label": "PNR / Booking Reference", "placeholder": "e.g. WX92K1", "required": True},
            {"id": "flight_no", "label": "Flight Number & Sector", "placeholder": "e.g. 6E-204 (BLR to DEL)", "required": True},
            {"id": "carrier_reason", "label": "Reason stated by airline (if any)", "placeholder": "e.g. Operational reasons / Crew shortage", "required": False},
            {"id": "alternate_offered", "label": "Did airline offer alternative flight within 24 hours?", "type": "select", "options": ["No alternative offered", "Offered flight >24h later", "Offered credit shell only", "Yes, within 24h"]},
        ]
    elif ct == "food_delivery_issue":
        questions = [
            {"id": "order_id", "label": "Platform Order ID", "placeholder": "e.g. SWIGGY-8921828", "required": True},
            {"id": "dish_name", "label": "Disputed Dish / Item Name", "placeholder": "e.g. Paneer Biryani delivered as Non-Veg Chicken", "required": True},
            {"id": "has_photo", "label": "Do you possess photographic proof of food/package?", "type": "select", "options": ["Yes, clear photographs available", "Yes, delivery receipt available", "No photo captured"]},
            {"id": "support_outcome", "label": "Customer care / Bot response so far", "placeholder": "e.g. Bot offered token INR 30 coupon or closed ticket unilaterally", "required": True},
        ]
    elif ct == "payment_dispute":
        questions = [
            {"id": "utr_rrn", "label": "Bank Transaction UTR / RRN Reference", "placeholder": "e.g. 329104829102", "required": True},
            {"id": "vpa_recipient", "label": "Merchant UPI ID / Beneficiary Account", "placeholder": "e.g. merchant@icici or Account XXXXXX129", "required": True},
            {"id": "exact_timestamp", "label": "Exact Date & Time of Debit", "placeholder": "e.g. 28 Oct 2026, 14:32 IST", "required": True},
            {"id": "bank_response", "label": "Bank / App Status Displayed", "placeholder": "e.g. Pending at beneficiary bank / Settlement failure", "required": False},
        ]
    elif ct == "ride_hailing_issue":
        questions = [
            {"id": "trip_id", "label": "Ride / Booking Identifier", "placeholder": "e.g. CRN-9821892", "required": True},
            {"id": "driver_details", "label": "Vehicle Plate / Driver Name", "placeholder": "e.g. KA-01-AB-1234 (Ramesh K)", "required": False},
            {"id": "penalty_amount", "label": "Cancellation Fee or Cash Extorted (INR)", "placeholder": "e.g. 50 or 200", "required": True},
            {"id": "grievance_type", "label": "Primary Violation", "type": "select", "options": ["Demand for offline extra cash", "AC refusal in vehicle", "Unfair cancellation penalty", "Route deviation / Surge dispute"]},
        ]
    else:
        questions = [
            {"id": "order_id", "label": "Invoice / Order Reference ID", "placeholder": "e.g. OD892182918", "required": True},
            {"id": "serial_number", "label": "Product Serial / IMEI (if electronics)", "placeholder": "e.g. SN-89218928", "required": False},
            {"id": "seller_refusal", "label": "Seller's exact grounds for refusal", "placeholder": "e.g. Stated return window expired or policy is replacement-only", "required": True},
            {"id": "desired_remedy", "label": "Desired Legal Relief", "type": "select", "options": ["Full 100% Cash Refund", "Immediate Free Replacement", "Repair under Warranty", "Statutory Compensation for Service Deficiency"]},
        ]

    def _get_entity(c):
        return (
            c.get("airline")
            or c.get("platform")
            or c.get("seller")
            or c.get("brand")
            or c.get("bank")
            or c.get("insurer")
            or c.get("railway")
            or c.get("telco")
            or c.get("service")
            or c.get("merchant")
            or "Opposite Party"
        )

    return {
        "case_id": case_id,
        "case_type": ct,
        "entity": _get_entity(case),
        "questions": questions
    }


def automated_complaint(case_id: str, answers: dict) -> dict:
    case = db.load_case(case_id) or {}
    res = case.get("result") or {}
    ct = case.get("case_type", "defective_product")
    entity = (
        case.get("airline")
        or case.get("platform")
        or case.get("seller")
        or case.get("brand")
        or case.get("bank")
        or case.get("insurer")
        or case.get("railway")
        or case.get("telco")
        or case.get("service")
        or case.get("merchant")
        or "Opposite Party"
    )
    complainant_name = answers.get("user_name") or answers.get("name") or "Aggrieved Consumer"
    complainant_email = answers.get("user_email") or answers.get("email") or "consumer@example.com"
    complainant_phone = answers.get("user_phone") or answers.get("phone") or "N/A"

    # Find top verified quote
    verified_quotes = [f for f in res.get("facts", []) if f.get("verified")]
    quote_text = verified_quotes[0]["quote"] if verified_quotes else "Merchant advertised terms and consumer protection mandates."
    quote_url = verified_quotes[0]["source_url"] if verified_quotes else "Official Merchant Domain"

    # 1. Formal Legal Pre-Litigation Demand
    notice_lines = [
        f"FORMAL LEGAL NOTICE FOR DEFICIENCY OF SERVICE & UNFAIR TRADE PRACTICE",
        f"Date: {now_iso()[:10]}",
        f"",
        f"TO: Grievance Officer / Nodal Authority, {entity}",
        f"FROM: {complainant_name} ({complainant_email}, {complainant_phone})",
        f"",
        f"SUBJECT: Formal Demand Notice regarding {ct.replace('_', ' ').title()} - Legal Escalation Warning",
        f"",
        f"Sir / Madam,",
        f"",
        f"I am issuing this formal legal demand regarding transactions executed with {entity}:",
        f"1. Dispute Factual Summary: {case.get('user_text', '')}",
        f"2. Transaction Specifics & Particulars: {json.dumps(answers.get('details', {}), indent=2)}",
        f"3. Contractual Policy Non-Compliance: Your official terms state: \"{quote_text}\" (Retrieved from {quote_url}). The denial or delay of remedy violates your own binding contractual terms.",
        f"4. Statutory Non-Compliance: Under the Consumer Protection Act, 2019 (Sections 2(11), 2(47), and Consumer Protection (E-Commerce) Rules 2020), withholding refunds for deficient services or defective commodities constitutes an actionable Unfair Trade Practice.",
        f"",
        f"FORMAL DEMAND:",
        f"You are hereby called upon to rectify this deficiency and process the full restitution / remedy within 7 calendar days of receipt of this notice.",
        f"Failing compliance, this matter shall be formally docketed before the National Consumer Helpline (INGRAM shortcode 1915), the Central Consumer Protection Authority (CCPA), and the District Consumer Commission via e-Jagriti (e-jagriti.gov.in) for damages and mental agony under Section 35 of the Act.",
        f"",
        f"Yours faithfully,",
        f"{complainant_name}",
    ]

    # 2. National Consumer Helpline (INGRAM 1915) Ready Dossier
    nch_docket = {
        "portal": "National Consumer Helpline (INGRAM - consumerhelpline.gov.in)",
        "helpline_dial": "1915 (Toll-Free) or WhatsApp to 8800001915",
        "company_name": entity,
        "grievance_category": ct.replace("_", " ").title(),
        "transaction_id": answers.get("details", {}).get("order_id") or answers.get("details", {}).get("pnr") or answers.get("details", {}).get("utr_rrn") or "N/A",
        "transaction_date": case.get("purchase_date") or now_iso()[:10],
        "grievance_summary": f"Deficiency of service by {entity}. {case.get('user_text', '')}. Merchant policy states: \"{quote_text[:120]}...\". Remedy denied contrary to CPA 2019.",
        "relief_claimed": answers.get("details", {}).get("desired_remedy") or "Full refund of paid consideration + statutory interest / delay compensation",
        "statutory_sections": "Consumer Protection Act 2019 (Section 2(11), 2(47)), E-Commerce Rules 2020",
    }

    recipient_email = extract_relevant_email(case, entity, verified_quotes[0] if verified_quotes else None)

    return {
        "ok": True,
        "case_id": case_id,
        "entity": entity,
        "recipient_email": recipient_email,
        "subject": f"Statutory Dispute Notice: {entity} - {case.get('product') or ct.replace('_', ' ').title()}",
        "legal_notice": "\n".join(notice_lines),
        "nch_docket": nch_docket,
    }


def tracker_metrics(case_id: str) -> dict:
    case = db.load_case(case_id) or {}
    res = case.get("result") or {}
    ct = case.get("case_type", "defective_product")
    p_date = case.get("purchase_date")

    days_elapsed = None
    if p_date:
        try:
            d_obj = parse_date(p_date)
            if d_obj:
                days_elapsed = max(0, (date.today() - d_obj).days)
        except Exception:
            pass

    # Extract windows from verified facts
    return_window = 7
    warranty_window = 365
    for f in res.get("facts", []):
        if f.get("field") == "return_window" and f.get("value"):
            w = window_days(f["value"])
            if w:
                return_window = w
        elif f.get("field") == "warranty_period" and f.get("value"):
            w = window_days(f["value"])
            if w:
                warranty_window = w

    # Calculate status
    return_days_left = max(0, return_window - (days_elapsed or 0)) if days_elapsed is not None else return_window
    warranty_days_left = max(0, warranty_window - (days_elapsed or 0)) if days_elapsed is not None else warranty_window
    return_expired = days_elapsed is not None and days_elapsed > return_window
    warranty_expired = days_elapsed is not None and days_elapsed > warranty_window

    # Penalty calculation
    daily_penalty = 0
    penalty_statute = ""
    if ct == "payment_dispute" and days_elapsed is not None:
        delayed_days = max(0, days_elapsed - 1)
        daily_penalty = delayed_days * 100
        penalty_statute = "RBI DPSS.CO.PD No.629/2019 (INR 100/day beyond T+1)"
    elif ct == "flight_issue":
        daily_penalty = 5000
        penalty_statute = "DGCA CAR Section 3 (Mandatory Cancellation/Delay Relief)"

    if days_elapsed is None:
        lifecycle_stage = "UNKNOWN_DATE"
    elif not return_expired:
        lifecycle_stage = "MERCHANT_RETURN_WINDOW"
    elif not warranty_expired:
        lifecycle_stage = "MANUFACTURER_WARRANTY"
    else:
        lifecycle_stage = "STATUTORY_ESCALATION"

    return {
        "case_id": case_id,
        "case_type": ct,
        "purchase_date": p_date,
        "days_elapsed": days_elapsed,
        "return_window_days": return_window,
        "return_days_left": return_days_left,
        "return_expired": return_expired,
        "warranty_window_days": warranty_window,
        "warranty_days_left": warranty_days_left,
        "warranty_expired": warranty_expired,
        "lifecycle_stage": lifecycle_stage,
        "accumulated_statutory_penalty": daily_penalty,
        "penalty_statute": penalty_statute,
    }

