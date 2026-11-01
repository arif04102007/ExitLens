"""Stage 5 date logic. Deadlines are computed here, in code, never by the AI."""
import re
from datetime import date, datetime, timedelta

WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "fourteen": 14, "fifteen": 15, "thirty": 30,
}


def parse_date(s):
    if not s:
        return None
    if isinstance(s, date):
        return s
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def window_days(value: str):
    """'7 days from delivery' -> 7;  '1 year' -> 365;  '12 months' -> 365;  None if unclear."""
    v = (value or "").lower()
    m = re.search(r"(\d+|" + "|".join(WORD_NUMS) + r")\s*(?:-|\s)?\s*(business\s+|working\s+)?(day|days|week|weeks|month|months|year|years)\b", v)
    if not m:
        return None
    n = m.group(1)
    n = int(n) if n.isdigit() else WORD_NUMS[n]
    unit = m.group(3)
    if unit.startswith("day"):
        return n
    if unit.startswith("week"):
        return n * 7
    if unit.startswith("month"):
        return round(n * 30.4375)
    return n * 365


def compute_deadlines(facts, purchase_date, today=None):
    """One entry per verified return_window / warranty_period fact."""
    start = parse_date(purchase_date)
    today = today or date.today()
    out = []
    for f in facts:
        if f.get("field") not in ("return_window", "warranty_period", "cancellation_notice"):
            continue
        days = window_days(f.get("value", ""))
        if days is None:
            continue
        entry = {
            "fact_id": f["id"],
            "party": f.get("party"),
            "field": f["field"],
            "label": f["value"],
            "days": days,
            "verified": bool(f.get("verified")),
        }
        if start:
            ends = start + timedelta(days=days)
            left = (ends - today).days
            entry.update(
                {
                    "start": start.isoformat(),
                    "ends_on": ends.isoformat(),
                    "days_left": left,
                    "expired": left < 0,
                    "days_since_purchase": (today - start).days,
                }
            )
        out.append(entry)
    return out
