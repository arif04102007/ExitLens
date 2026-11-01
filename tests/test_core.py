import os
import sys
import tempfile
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["EXITLENS_MODE"] = "fixture"
os.environ["EXITLENS_DB"] = str(Path(tempfile.mkdtemp()) / "t.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from backend import dates, db, discovery, heuristics, pipeline  # noqa: E402
from backend.textutil import same_site, strip_markdown  # noqa: E402
from backend.verify import quote_in_text  # noqa: E402


# ---------------- verifier ----------------
def test_quote_must_exist():
    page = "Most items can be returned within 7 days of delivery if they are unused."
    assert quote_in_text("returned within 7 days of delivery", page)
    assert not quote_in_text("returned within 30 days of delivery", page)
    assert not quote_in_text("short", page)


def test_quote_normalizes_markdown_and_quotes():
    page = strip_markdown("**Returns:** items can be returned within ‘7 days’ of delivery.")
    assert quote_in_text("items can be returned within '7 days' of delivery.", page)


def test_ellipsis_quote():
    page = "Replacement is available for defective items within 10 days of delivery after inspection."
    assert quote_in_text("Replacement is available ... within 10 days of delivery", page)


def test_same_site():
    assert same_site("https://www.amazon.in/help", "https://amazon.in/x")
    assert same_site("https://a.sony.co.in/x", "https://www.sony.co.in/y")
    assert not same_site("https://evil-amazon.in/x", "https://amazon.in/y")


# ---------------- dates ----------------
def test_window_days():
    assert dates.window_days("7 days from delivery") == 7
    assert dates.window_days("1 year") == 365
    assert dates.window_days("12 months") == 365
    assert dates.window_days("two weeks") == 14
    assert dates.window_days("no idea") is None


def test_deadlines_three_purchase_dates():
    facts = [{"id": "f1", "party": "seller", "field": "return_window", "value": "7 days of delivery", "verified": True}]
    today = date(2026, 11, 1)
    d = dates.compute_deadlines(facts, "2026-10-28", today)[0]
    assert d["ends_on"] == "2026-11-04" and d["days_left"] == 3 and not d["expired"]
    d = dates.compute_deadlines(facts, "2026-10-25", today)[0]
    assert d["ends_on"] == "2026-11-01" and d["days_left"] == 0 and not d["expired"]
    d = dates.compute_deadlines(facts, "2026-10-01", today)[0]
    assert d["expired"] and d["days_left"] == -24


# ---------------- parsing & discovery ----------------
def test_parse_headphones():
    p = heuristics.parse_case_text("My boAt headphones stopped working after two weeks, I bought them from Amazon")
    assert p["case_type"] == "defective_product" and p["seller"] == "Amazon" and p["brand"] == "boAt"


def test_parse_subscription():
    p = heuristics.parse_case_text("I can't cancel my Netflix subscription")
    assert p["case_type"] == "subscription_cancel" and p["service"] == "Netflix"


def test_official_filter():
    res = [
        {"url": "https://www.amazon.in/gp/help/returns", "title": "Returns policy"},
        {"url": "https://coupons.example/amazon-return-policy", "title": "amazon return policy coupons"},
    ]
    out = discovery.rank_official(res, "Amazon")
    assert [o["url"] for o in out] == ["https://www.amazon.in/gp/help/returns"]


def test_heuristic_extraction():
    plain = ("Most items can be returned within 7 days of delivery if they are unused. "
             "Keep your invoice and order ID ready for any claim request.")
    facts = heuristics.extract_facts_text(plain)
    fields = {f["field"] for f in facts}
    assert "return_window" in fields and "proof_required" in fields


# ---------------- full pipeline (fixture pages) ----------------
def _wait(cid, secs=30):
    for _ in range(secs * 10):
        c = db.load_case(cid)
        if c["status"] in ("done", "failed", "needs_info"):
            return c
        time.sleep(0.1)
    raise AssertionError("pipeline timed out")


def test_pipeline_end_to_end():
    case = pipeline.create_case("My Acme Audio headphones stopped working after two weeks, bought from ShopEasy",
                                {"purchase_date": "2026-10-18"})
    pipeline.start_case(case["id"])
    c = _wait(case["id"])
    assert c["status"] == "done", c.get("error")
    res = c["result"]
    # seller needed the agent tier (hub page has no policy), manufacturer was a direct fetch
    methods = {s["party"]: s["fetch_method"] for s in res["sources"]}
    assert methods["seller"] == "agent" and methods["manufacturer"] == "fetch"
    verified = [f for f in res["facts"] if f["verified"]]
    assert any(f["field"] == "return_window" and "7 days" in f["value"] for f in verified)
    assert any(f["field"] == "warranty_period" for f in verified)
    # the coupons blog was filtered out
    assert all("coupons-blog" not in s["url"] for s in res["sources"])
    # every verified fact is really on its page
    assert all(f["quote"] for f in verified)
    assert res["steps"][0]["status"] == "verified" and res["steps"][-1]["status"] == "could_not_verify"
    d = [x for x in res["deadlines"] if x["field"] == "return_window"][0]
    assert d["ends_on"] == "2026-10-25" and d["expired"]


def test_tampered_quote_is_rejected():
    from backend.verify import verify_fact
    f = {"quote": "Items can be returned within 90 days of delivery", "source_url": "https://shopeasy.example/help/returns"}
    page = "Most items can be returned within 7 days of delivery if unused."
    assert verify_fact(f, page, "https://shopeasy.example/help")["verified"] is False


def test_followup_when_seller_missing():
    case = pipeline.create_case("My headphones stopped working", {})
    pipeline.start_case(case["id"])
    c = _wait(case["id"])
    assert c["status"] == "needs_info" and "buy" in c["question"].lower()
    pipeline.answer_followup(case["id"], "ShopEasy")
    c = _wait(case["id"])
    assert c["status"] == "done", c.get("error")


def test_claim_draft_and_monitor():
    case = pipeline.create_case("My Acme Audio headphones stopped working, bought from ShopEasy", {"purchase_date": "2026-10-28"})
    pipeline.start_case(case["id"])
    c = _wait(case["id"])
    draft = pipeline.claim_draft(c, {"name": "Test User", "order_id": "OD123"})
    assert "OD123" in draft["body"] and "Your policy states" in draft["body"]
    assert pipeline.monitor_enable(case["id"])["watching"] >= 1
    assert all(x["state"] == "unchanged" for x in pipeline.monitor_check(case["id"]))
