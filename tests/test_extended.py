"""Tests for the new case types, entity categories, escalation, and plan generation."""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["EXITLENS_MODE"] = "fixture"
os.environ["EXITLENS_DB"] = str(Path(tempfile.mkdtemp()) / "test_ext.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from backend import config, discovery, heuristics, pipeline, plan


def test_config_data_loaders():
    entities = config.known_entities()
    assert "sellers" in entities and "food_delivery" in entities and "banking" in entities
    assert "Swiggy" in entities["food_delivery"]
    assert "boAt" in entities["brands"]

    aliases = config.brand_aliases()
    assert "amazon" in aliases and "swiggy" in aliases
    assert "swiggy.com" in aliases["swiggy"]

    esc = config.escalation_data()
    assert "India" in esc and "regulators" in esc["India"] and "legal_rights" in esc["India"]
    assert "flight_issue" in esc["India"]["regulators"]

    ct = config.case_type_defs()
    assert len(ct) >= 20
    assert "food_delivery_issue" in ct and "flight_issue" in ct and "telecom_issue" in ct

    assert config.default_country() == "India"
    assert "not legal advice" in config.disclaimer()
    assert config.min_complaint_length() == 8


def test_heuristic_parsing_food_delivery():
    p = heuristics.parse_case_text("I received cold food and spilled order from Swiggy")
    assert p["case_type"] == "food_delivery_issue"
    assert p["platform"] == "Swiggy"
    assert p["seller"] == "Swiggy"


def test_heuristic_parsing_flight():
    p = heuristics.parse_case_text("My flight was cancelled by IndiGo and they refused refund")
    assert p["case_type"] == "flight_issue"
    assert p["airline"] == "IndiGo"


def test_heuristic_parsing_train():
    p = heuristics.parse_case_text("My train was cancelled and IRCTC did not process TDR refund")
    assert p["case_type"] == "train_issue"
    assert p["railway"] == "IRCTC"


def test_heuristic_parsing_ride_hailing():
    p = heuristics.parse_case_text("Uber driver charged extra cash and cancelled the ride")
    assert p["case_type"] == "ride_hailing_issue"
    assert p["platform"] == "Uber"


def test_heuristic_parsing_payment():
    p = heuristics.parse_case_text("UPI payment stuck and money debited on PhonePe")
    assert p["case_type"] == "payment_dispute"
    assert p["platform"] == "PhonePe"


def test_heuristic_parsing_telecom():
    p = heuristics.parse_case_text("Jio broadband down and no signal for three days")
    assert p["case_type"] == "telecom_issue"
    assert p["telco"] == "Jio"


def test_heuristic_parsing_insurance():
    p = heuristics.parse_case_text("Star Health cashless denied and claim rejected without reason")
    assert p["case_type"] == "insurance_claim"
    assert p["insurer"] == "Star Health"


def test_heuristic_parsing_banking():
    p = heuristics.parse_case_text("ATM failed and HDFC Bank debited amount without dispensing cash")
    assert p["case_type"] == "banking_dispute"
    assert p["bank"] == "HDFC Bank"


def test_discovery_queries_and_topics():
    # party-specific queries
    q_airline = discovery.queries_for("airline", "IndiGo", case_type="flight_issue")
    assert any("refund" in q.lower() for q in q_airline)

    q_bank = discovery.queries_for("bank", "SBI", case_type="banking_dispute")
    assert any("grievance" in q.lower() or "charges" in q.lower() for q in q_bank)

    # topic for party
    t_airline = discovery.topic_for("airline", "flight_issue")
    assert "carriage" in t_airline.lower() or "cancellation" in t_airline.lower()

    t_telco = discovery.topic_for("telco", "telecom_issue")
    assert "charter" in t_telco.lower() or "grievance" in t_telco.lower()


def test_parties_generation():
    # Food delivery
    c_food = {"case_type": "food_delivery_issue", "platform": "Zomato", "seller": "Zomato"}
    parties_food = pipeline._parties(c_food)
    assert len(parties_food) == 1 and parties_food[0]["party"] == "platform" and parties_food[0]["name"] == "Zomato"

    # Flight with airline + OTA
    c_flight = {"case_type": "flight_issue", "airline": "IndiGo", "ota": "MakeMyTrip"}
    parties_flight = pipeline._parties(c_flight)
    assert len(parties_flight) == 2
    assert {p["party"] for p in parties_flight} == {"airline", "ota"}

    # Insurance
    c_ins = {"case_type": "insurance_claim", "insurer": "Care Health"}
    parties_ins = pipeline._parties(c_ins)
    assert len(parties_ins) == 1 and parties_ins[0]["party"] == "insurer" and parties_ins[0]["name"] == "Care Health"


def test_plan_building_includes_legal_rights_and_regulator():
    facts = []
    deadlines = []

    # Flight plan should include DGCA regulator and DGCA passenger charter legal rights
    steps_flight = plan.build_plan("flight_issue", facts, deadlines, country="India")
    titles = [s["title"] for s in steps_flight]
    assert any("regulator (DGCA via AirSewa)" in t for t in titles)
    assert any("legal rights" in t.lower() for t in titles)
    assert any("NCH / Consumer Commission" in t for t in titles)
    assert steps_flight[-1]["status"] == "could_not_verify"

    # Payment dispute plan should include RBI Ombudsman regulator
    steps_pay = plan.build_plan("payment_dispute", facts, deadlines, country="India")
    titles_pay = [s["title"] for s in steps_pay]
    assert any("regulator (RBI Integrated Ombudsman)" in t for t in titles_pay)
    assert any("legal rights" in t.lower() for t in titles_pay)


def test_needs_info_for_new_types():
    assert "airline" in pipeline._needs_info({"case_type": "flight_issue"}).lower()
    assert "food" in pipeline._needs_info({"case_type": "food_delivery_issue"}).lower()
    assert "cab" in pipeline._needs_info({"case_type": "ride_hailing_issue"}).lower()
    assert "payment" in pipeline._needs_info({"case_type": "payment_dispute"}).lower()
    assert pipeline._needs_info({"case_type": "train_issue"}) is None


def test_complaint_questions_and_automated_filing():
    # Setup test case in db
    c_id = "test_case_flight_01"
    pipeline.db.save_case({
        "id": c_id,
        "case_type": "flight_issue",
        "airline": "IndiGo",
        "purchase_date": "2026-10-10",
        "user_text": "Flight cancelled 2 hours prior without refund",
        "result": {
            "facts": [
                {"id": "f1", "field": "return_window", "value": "7 days", "quote": "Full refund within 7 days", "source_url": "https://goindigo.in/policy"}
            ]
        }
    })

    # Test questions retrieval
    q_res = pipeline.complaint_questions(c_id)
    assert q_res["case_type"] == "flight_issue"
    assert q_res["entity"] == "IndiGo"
    fields = [q["id"] for q in q_res["questions"]]
    assert "pnr" in fields
    assert "flight_no" in fields

    # Test automated complaint generation
    answers = {
        "user_name": "Test Passenger",
        "user_email": "passenger@example.com",
        "user_phone": "9876543210",
        "details": {
            "pnr": "6E-ABCDEF",
            "flight_no": "6E-204",
            "cancellation_reason": "Flight cancelled at gate without alternate flight provided",
            "desired_remedy": "Full ticket refund of INR 6,200 plus statutory delay penalty",
        }
    }
    complaint = pipeline.automated_complaint(c_id, answers)
    assert complaint["ok"] is True
    assert "Statutory Dispute Notice" in complaint["subject"]
    assert "IndiGo" in complaint["legal_notice"]
    assert "6E-ABCDEF" in complaint["legal_notice"]
    assert "Consumer Protection Act, 2019" in complaint["legal_notice"]
    
    # NCH Docket check
    nch = complaint["nch_docket"]
    assert "consumerhelpline.gov.in" in nch["portal"]
    assert nch["company_name"] == "IndiGo"
    assert nch["transaction_id"] == "6E-ABCDEF"


def test_tracker_metrics():
    c_id = "test_case_tracker_01"
    pipeline.db.save_case({
        "id": c_id,
        "case_type": "defective_product",
        "seller": "Amazon",
        "purchase_date": "2026-10-25",
        "result": {
            "facts": [
                {"id": "f1", "field": "return_window", "value": "7 days"},
                {"id": "f2", "field": "warranty_period", "value": "1 year"},
            ]
        }
    })
    metrics = pipeline.tracker_metrics(c_id)
    assert metrics["case_id"] == c_id
    assert metrics["return_window_days"] == 7
    assert metrics["warranty_window_days"] == 365
    assert metrics["days_elapsed"] is not None
    assert metrics["lifecycle_stage"] in ("MERCHANT_RETURN_WINDOW", "MANUFACTURER_WARRANTY", "STATUTORY_ESCALATION")


def test_tracker_statutory_penalty_upi():
    c_id = "test_case_pay_01"
    pipeline.db.save_case({
        "id": c_id,
        "case_type": "payment_dispute",
        "platform": "PhonePe",
        "purchase_date": "2026-10-15",
        "result": {"facts": []}
    })
    metrics = pipeline.tracker_metrics(c_id)
    assert metrics["accumulated_statutory_penalty"] > 0
    assert "RBI DPSS" in metrics["penalty_statute"]


def test_discover_canonical_host_fallback():
    # When tinyfish returns no results or is in fixture mode, falls back to brand alias or simple domain
    host = discovery.discover_canonical_host(None, "IndiGo")
    assert host == "goindigo.in"

