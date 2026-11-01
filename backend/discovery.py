"""Stage 2: turn search results into a short list of OFFICIAL policy pages."""
import re

from .config import brand_aliases, case_type_defs
from .textutil import host_of

ALIASES = brand_aliases()
JUNK = ("coupon", "deal", "review", "reddit", "quora", "youtube.com/watch", "pinterest", "blog", "forum", "medium.com", "trustpilot", "mouthshut")
KEYWORDS = {"policy": 3, "warranty": 3, "return": 3, "refund": 3, "cancel": 3, "terms": 2, "help": 1, "support": 1, "claim": 2}


def _get_aliases():
    return brand_aliases() or ALIASES


def _token(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def discover_canonical_host(client, name: str) -> str:
    """Dynamically queries TinyFish live search to discover the canonical official domain for ANY entity."""
    if not name:
        return ""
    if client:
        try:
            results = client.search(f"{name} official website") or []
            for r in results[:6]:
                u = r.get("url") or ""
                h = host_of(u)
                if not h:
                    continue
                blob = f"{u} {r.get('title', '')} {r.get('snippet', '')}".lower()
                if any(j in blob for j in JUNK):
                    continue
                return h
        except Exception:
            pass
    # Fallback to known aliases cache if available
    low = (name or "").lower().strip()
    aliases = _get_aliases()
    found = aliases.get(low)
    if found and isinstance(found, list) and len(found) > 0:
        return found[0]
    return ""


def is_official(url: str, name: str, canonical_host: str = "") -> bool:
    host = host_of(url)
    if not host:
        return False
    if canonical_host:
        if host == canonical_host or host.endswith("." + canonical_host) or canonical_host.endswith("." + host):
            return True
    clean = re.sub(r"[^a-z0-9]", "", host)
    low = (name or "").lower().strip()
    aliases = _get_aliases()
    for a in aliases.get(low, []):
        if host == a or host.endswith("." + a):
            return True
    tok = _token(name)
    if tok and tok in clean:
        return True
    first = re.sub(r"[^a-z0-9]", "", low.split()[0]) if low.split() else ""
    return len(first) >= 4 and first in clean


def rank_official(results, name: str, max_urls: int = 3, canonical_host: str = ""):
    scored = []
    for r in results or []:
        url = r.get("url") or ""
        blob = f"{url} {r.get('title', '')} {r.get('snippet', '')}".lower()
        if not url.startswith("http") or not is_official(url, name, canonical_host=canonical_host):
            continue
        if any(j in blob for j in JUNK):
            continue
        score = sum(w for k, w in KEYWORDS.items() if k in blob)
        if canonical_host and host_of(url) == canonical_host:
            score += 5
        scored.append((score, url, r))
    scored.sort(key=lambda t: -t[0])
    seen, out = set(), []
    for _, url, r in scored:
        if url in seen:
            continue
        seen.add(url)
        out.append({"url": url, "title": r.get("title") or url})
        if len(out) >= max_urls:
            break
    return out


def queries_for(party: str, name: str, product: str = "", case_type: str = ""):
    ct_defs = case_type_defs()
    if case_type and case_type in ct_defs:
        templates = ct_defs[case_type].get("search_queries", {}).get(party)
        if templates:
            return [t.format(name=name) for t in templates]

    if party == "seller":
        return [f"{name} return policy", f"{name} returns and refunds help"]
    if party == "manufacturer":
        return [f"{name} warranty policy India", f"{name} warranty claim support"]
    if party == "airline":
        return [f"{name} refund policy cancelled flight", f"{name} conditions of carriage passenger rights"]
    if party == "ota":
        return [f"{name} flight cancellation refund policy", f"{name} booking help refund"]
    if party == "railway":
        return [f"{name} cancellation refund rules", f"{name} TDR refund policy"]
    if party == "telco":
        return [f"{name} customer grievance redressal policy", f"{name} citizen charter complaints"]
    if party == "insurer":
        return [f"{name} claim settlement grievance policy", f"{name} policyholder rights help"]
    if party == "bank":
        return [f"{name} customer grievance redressal policy", f"{name} schedule of charges complaints"]
    if party == "hotel":
        return [f"{name} guest cancellation policy", f"{name} reservation refund policy"]
    if party == "platform":
        return [f"{name} cancellation refund policy", f"{name} customer support help"]
    return [f"{name} cancel subscription refund policy", f"{name} cancel membership help"]


def topic_for(party: str, case_type: str) -> str:
    ct_defs = case_type_defs()
    if case_type and case_type in ct_defs:
        topic = ct_defs[case_type].get("policy_topics", {}).get(party)
        if topic:
            return topic
    if party == "seller":
        return "delivery, cancellation, return and refund policy" if case_type == "delayed_delivery" else "return, replacement and refund policy"
    if party == "manufacturer":
        return "warranty policy and how to make a warranty claim"
    if party == "airline":
        return "conditions of carriage, cancellation and refund policy"
    if party == "ota":
        return "booking cancellation and refund policy"
    if party == "railway":
        return "TDR filing, cancellation and refund rules"
    if party == "telco":
        return "citizen charter, grievance redressal and quality of service policy"
    if party == "insurer":
        return "claim settlement, grievance redressal and policyholder rights"
    if party == "bank":
        return "schedule of charges, fair practices code and grievance redressal"
    if party == "hotel":
        return "check-in, cancellation and guest policy"
    if party == "platform":
        return "cancellation, terms and refund policy"
    return "cancellation, billing and refund policy"
