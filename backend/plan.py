"""Stage 5: build the checklist from VERIFIED facts only, in code.

Everything wording-wise that comes from a website is a quote on a fact. Everything in
`interpretation` is ours and is labelled that way in the UI.
"""
from datetime import date

from .config import case_type_defs, default_country, escalation_data

PARTY_LABEL = {
    "seller": "Seller",
    "manufacturer": "Manufacturer",
    "service": "Service",
    "platform": "Platform",
    "airline": "Airline",
    "ota": "Booking Agent (OTA)",
    "railway": "Railway / IRCTC",
    "telco": "Telecom Provider",
    "insurer": "Insurance Company",
    "bank": "Bank",
    "hotel": "Hotel",
}

ESCALATION = (
    "If neither party resolves it, you can contact the National Consumer "
    "Helpline (toll-free 1915, WhatsApp 8800001915, consumerhelpline.gov.in) "
    "or file online via e-Jagriti (e-jagriti.gov.in). Free for claims up to ₹5 Lakhs."
)


def _pick(facts, field, party=None, verified=True):
    out = []
    for f in facts:
        if f["field"] != field:
            continue
        if party and f["party"] != party:
            continue
        if verified and not f.get("verified"):
            continue
        out.append(f)
    return out


def _vals(fs):
    return "\n".join(f"{PARTY_LABEL.get(f['party'], f['party'])}: {f['value']}" for f in fs)


def _status(fs):
    return "verified" if any(f.get("verified") for f in fs) else "could_not_verify"


def _step(order, title, action, interp, fs, force_unverified=False):
    return {
        "order": order,
        "title": title,
        "action": action,
        "interpretation": interp,
        "fact_ids": [f["id"] for f in fs],
        "status": "could_not_verify" if force_unverified else _status(fs),
    }


def _window_step(order, title, facts, deadlines, party, field, missing_msg):
    fs = _pick(facts, field, party)
    if not fs:
        return _step(order, title, missing_msg,
                     "We could not verify this on the official page. Open the official policy yourself before acting.", [])
    d = next((x for x in deadlines if x["fact_id"] in {f["id"] for f in fs} and "ends_on" in x), None)
    if d:
        if d["expired"]:
            action = f"{_vals(fs)}. By your purchase date this window ended on {d['ends_on']} ({-d['days_left']} days ago)."
            interp = "Our reading: this window looks closed, so check secondary warranty or dispute steps. Check whether the policy counts days from delivery rather than purchase."
        else:
            action = f"{_vals(fs)}. Counting from your purchase date, it ends on {d['ends_on']} ({d['days_left']} days left)."
            interp = "Our reading: act before that date. If the policy counts from delivery, you may get a little extra time, but do not rely on it."
    else:
        action = f"{_vals(fs)}."
        interp = "Add your purchase date and we will calculate the exact deadline for you."
    return _step(order, title, action, interp, fs)


def _legal_step(order, case_type, country="India"):
    esc = escalation_data().get(country, escalation_data().get("India", {}))
    rights = esc.get("legal_rights", {}).get(case_type, [])
    if not rights:
        return None
    action = "\n".join(f"• {r['law']}: {r['right']}" for r in rights)
    interp = "Statutory consumer rights under law. Companies' internal policies cannot override these statutory protections."
    return _step(order, "Know your statutory legal rights", action, interp, [], force_unverified=True)


def _regulator_step(order, case_type, country="India"):
    esc = escalation_data().get(country, escalation_data().get("India", {}))
    reg = esc.get("regulators", {}).get(case_type)
    if not reg:
        return None
    action = reg.get("text", "")
    interp = f"If the company fails to resolve your grievance within reasonable time, escalate directly to {reg.get('name')}."
    return _step(order, f"Escalate to regulator ({reg.get('name')})", action, interp, [], force_unverified=True)


def _general_escalation_step(order, country="India"):
    esc = escalation_data().get(country, escalation_data().get("India", {}))
    gen = esc.get("general", {})
    text = gen.get("text", ESCALATION)
    return _step(order, "Escalate if unresolved (NCH / Consumer Commission)", text,
                 "General guidance from ExitLens, not from a policy page. Free for claims up to ₹5 Lakhs on e-Jagriti or call 1915.",
                 [], force_unverified=True)


def build_plan(case_type, facts, deadlines, country=None):
    country = country or default_country()
    steps = []

    if case_type == "subscription_cancel":
        n = _pick(facts, "cancellation_notice", "service")
        r = _pick(facts, "return_window", "service")
        c = _pick(facts, "claim_route", "service")
        cond = _pick(facts, "conditions", "service") + _pick(facts, "exclusions", "service")
        p = _pick(facts, "proof_required", "service")
        steps.append(_window_step(1, "Check notice and billing timing", facts, deadlines, "service",
                                  "cancellation_notice", "No cancellation notice period could be verified on the official page."))
        steps.append(_step(2, "Find the cancel route",
                           _vals(c) if c else "No cancel route could be verified on the official pages.",
                           "Our reading: use the route the service itself describes, from your own account, and keep a screenshot of the confirmation." if c else
                           "We could not verify a cancel route. Look in your account settings under billing or membership.", c))
        steps.append(_step(3, "Know what is refundable",
                           _vals(r + cond) if (r or cond) else "No refund conditions could be verified on the official pages.",
                           "Our reading: refunds usually depend on how recently you were charged and whether the service was used." if (r or cond) else
                           "We could not verify refund rules. Ask support in writing before the next billing date.", r + cond))
        steps.append(_step(4, "Gather your proof",
                           _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep billing emails, the amount charged and the date of each charge." if p else
                           "Generic advice from us, not from the page: keep billing emails and bank statements.", p))

    elif case_type == "delayed_delivery":
        steps.append(_window_step(1, "Check the cancellation and refund window", facts, deadlines, "seller",
                                  "return_window", "No cancellation or refund window could be verified on the official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather your proof", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep the order ID, the promised delivery date and the tracking screenshots." if p else
                           "Generic advice from us, not from the page: keep the order ID, promised date and tracking screenshots.", p))
        c = _pick(facts, "claim_route", "seller")
        steps.append(_step(3, "Raise it with the seller", _vals(c) if c else "No claim route could be verified on the official page.",
                           "Our reading: use this route first and keep the reference number." if c else
                           "We could not verify a route. Use the Help or Orders section of your account.", c))

    elif case_type == "food_delivery_issue":
        steps.append(_window_step(1, "Check platform refund and cancellation window", facts, deadlines, "platform",
                                  "return_window", "No immediate dispute window could be verified on the official page."))
        p = _pick(facts, "proof_required") + _pick(facts, "conditions", "platform")
        steps.append(_step(2, "Document the issue with photos", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: take clear photos of the food, packaging label, and bill immediately." if p else
                           "Generic advice from us, not from the page: photograph the delivered item, bill, and packaging before discarding.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Raise dispute in the app or support", _vals(c) if c else "No claim route could be verified on the platform's official page.",
                           "Our reading: report via order help in the app right away." if c else
                           "We could not verify a route. Go to Help / Order History in your food delivery app.", c))

    elif case_type == "flight_issue":
        steps.append(_window_step(1, "Check airline cancellation and compensation terms", facts, deadlines, "airline",
                                  "return_window", "No refund window could be verified on the airline's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather flight proof and boarding records", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep PNR, boarding passes, flight delay/cancellation SMS/email, and food/hotel receipts." if p else
                           "Generic advice from us, not from the page: save PNR, boarding pass, and cancellation notification.", p))
        c = _pick(facts, "claim_route", "airline") or _pick(facts, "claim_route", "ota")
        steps.append(_step(3, "Submit claim to airline or booking platform", _vals(c) if c else "No claim route could be verified on the official page.",
                           "Our reading: raise the claim directly with the airline or OTA." if c else
                           "We could not verify a route. Contact airline customer support or OTA booking help.", c))

    elif case_type == "train_issue":
        steps.append(_window_step(1, "Check TDR filing and refund timelines", facts, deadlines, "railway",
                                  "return_window", "No TDR timeline could be verified on the railway official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather PNR and ticket details", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep PNR number, chart status, and cancellation / delay proof." if p else
                           "Generic advice from us: note your PNR number, coach/berth details, and date of journey.", p))
        c = _pick(facts, "claim_route", "railway")
        steps.append(_step(3, "File TDR via IRCTC or Railway counter", _vals(c) if c else "No TDR route could be verified on the official page.",
                           "Our reading: file TDR online on IRCTC before the prescribed cut-off time." if c else
                           "We could not verify a route. Log in to irctc.co.in -> My Transactions -> File TDR.", c))

    elif case_type == "ride_hailing_issue":
        steps.append(_window_step(1, "Check fare dispute and cancellation terms", facts, deadlines, "platform",
                                  "return_window", "No dispute window could be verified on the platform's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather ride receipt and route proof", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: save the trip receipt, driver details, payment screenshot, and route taken." if p else
                           "Generic advice from us: keep the trip receipt, ride ID, and driver cancellation charges.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Dispute the fare or report driver in app", _vals(c) if c else "No dispute route could be verified on the platform's official page.",
                           "Our reading: use the Help section under Your Trips in the app." if c else
                           "We could not verify a route. Open the ride app -> Activity / Trips -> Help with a trip.", c))

    elif case_type == "wrong_item_delivered":
        steps.append(_window_step(1, "Check return and replacement window", facts, deadlines, "seller",
                                  "return_window", "No return window could be verified on the seller's official page."))
        p = _pick(facts, "proof_required") + _pick(facts, "conditions", "seller")
        steps.append(_step(2, "Preserve unboxing proof and tags", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: photograph the shipping label, outer box, and wrong item with tags intact." if p else
                           "Generic advice from us: take clear photos/video of the outer box label and the wrong product.", p))
        c = _pick(facts, "claim_route", "seller")
        steps.append(_step(3, "Raise return request for wrong item", _vals(c) if c else "No claim route could be verified on the seller's official page.",
                           "Our reading: select 'Wrong item delivered' under Returns in your order history." if c else
                           "We could not verify a route. Go to Your Orders -> Return/Replace.", c))

    elif case_type == "payment_dispute":
        steps.append(_window_step(1, "Check dispute redressal and reversal timeline", facts, deadlines, "platform",
                                  "return_window", "No reversal window could be verified on the platform's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather transaction and UTR details", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: save UTR / UPI reference number, bank debit SMS, and failed transaction screenshot." if p else
                           "Generic advice from us: save the 12-digit UTR number, transaction date/time, and debit SMS.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Raise dispute with payment app or bank", _vals(c) if c else "No dispute route could be verified on the official page.",
                           "Our reading: report the transaction in the UPI app and with your bank." if c else
                           "We could not verify a route. Raise a dispute in the payment app or contact your bank branch.", c))

    elif case_type == "ticket_booking_issue":
        steps.append(_window_step(1, "Check ticket cancellation and refund policy", facts, deadlines, "platform",
                                  "cancellation_notice", "No ticket cancellation window could be verified on the official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather booking ID and event status", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep booking confirmation, event cancellation announcement, and ticket details." if p else
                           "Generic advice from us: save booking confirmation email, ticket barcode, and proof of event cancellation.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Request ticket refund from platform", _vals(c) if c else "No claim route could be verified on the platform's official page.",
                           "Our reading: submit refund request through your booking account." if c else
                           "We could not verify a route. Contact the ticketing platform's support or customer care.", c))

    elif case_type == "telecom_issue":
        steps.append(_window_step(1, "Check grievance redressal and turnaround standards", facts, deadlines, "telco",
                                  "return_window", "No resolution timeline could be verified on the telco's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather docket numbers and service records", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep service complaint docket numbers, speed test logs, or unauthorized VAS charges proof." if p else
                           "Generic advice from us: note your complaint docket number and dates of service disruption.", p))
        c = _pick(facts, "claim_route", "telco")
        steps.append(_step(3, "Lodge complaint and escalate to Appellate Authority", _vals(c) if c else "No grievance route could be verified on the telco's official page.",
                           "Our reading: first register with Customer Care, then escalate to the Appellate Authority with docket ID." if c else
                           "We could not verify a route. Call customer care or email the telco's Appellate Authority.", c))

    elif case_type == "insurance_claim":
        steps.append(_window_step(1, "Check claim settlement and free-look period", facts, deadlines, "insurer",
                                  "return_window", "No claim settlement timeline could be verified on the insurer's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Assemble claim file and repudiation letter", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: gather policy bond, discharge summary, medical bills, FIR/claim form, and insurer's rejection letter." if p else
                           "Generic advice from us: keep policy schedule, hospital bills/discharge summary, and written rejection letter.", p))
        c = _pick(facts, "claim_route", "insurer")
        steps.append(_step(3, "Submit grievance to Insurer's Grievance Redressal Officer (GRO)", _vals(c) if c else "No GRO route could be verified on the insurer's official page.",
                           "Our reading: insurers must acknowledge within 3 days and resolve within 15 days." if c else
                           "We could not verify a route. Write to the insurer's Grievance Redressal Officer (GRO).", c))

    elif case_type == "banking_dispute":
        steps.append(_window_step(1, "Check dispute timeline and turnaround time", facts, deadlines, "bank",
                                  "return_window", "No resolution timeline could be verified on the bank's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather account statements and dispute slips", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: compile account statement, ATM/card dispute form, written complaint, and acknowledgement." if p else
                           "Generic advice from us: keep account statement showing disputed entry and complaint reference number.", p))
        c = _pick(facts, "claim_route", "bank")
        steps.append(_step(3, "Escalate to Bank's Principal Nodal Officer (PNO)", _vals(c) if c else "No PNO route could be verified on the bank's official page.",
                           "Our reading: escalate to the Principal Nodal Officer if unresolved after 30 days." if c else
                           "We could not verify a route. File grievance on the bank's portal or write to the Principal Nodal Officer.", c))

    elif case_type == "edtech_refund":
        steps.append(_window_step(1, "Check course refund and cooling-off terms", facts, deadlines, "platform",
                                  "cancellation_notice", "No refund window could be verified on the platform's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather enrolment, payment, and loan agreements", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: gather fee receipt, loan agreement/EMI terms, email correspondence, and marketing brochures." if p else
                           "Generic advice from us: collect enrolment receipts, loan papers, and written cancellation requests.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Issue formal refund demand to edtech platform", _vals(c) if c else "No refund route could be verified on the platform's official page.",
                           "Our reading: submit formal written cancellation and demand revocation of education loan EMI." if c else
                           "We could not verify a route. Email the grievance officer and support team demanding pro-rata refund.", c))

    elif case_type == "hotel_booking_issue":
        steps.append(_window_step(1, "Check cancellation and check-in policy", facts, deadlines, "platform",
                                  "cancellation_notice", "No cancellation window could be verified on the official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather booking confirmation and photos", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep booking voucher, photos of room condition or denial of check-in, and receipts." if p else
                           "Generic advice from us: save booking confirmation, hotel communication, and photos of deficiency.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Demand alternate accommodation or refund", _vals(c) if c else "No claim route could be verified on the platform's official page.",
                           "Our reading: escalate immediately via platform support hotline." if c else
                           "We could not verify a route. Contact the booking platform support desk immediately.", c))

    elif case_type == "health_pharma_issue":
        steps.append(_window_step(1, "Check medicine return and dispute policy", facts, deadlines, "platform",
                                  "return_window", "No return window could be verified on the platform's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Preserve prescription, invoice, and medicine box", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: keep original prescription, tax invoice, and medicine strip showing batch/expiry." if p else
                           "Generic advice from us: photograph medicine batch number, expiry date, invoice, and doctor's prescription.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Raise complaint with pharmacy platform", _vals(c) if c else "No claim route could be verified on the platform's official page.",
                           "Our reading: report wrong or expired medicine immediately for recall and refund." if c else
                           "We could not verify a route. Contact pharmacy app customer care.", c))

    elif case_type == "grocery_delivery_issue":
        steps.append(_window_step(1, "Check grocery refund policy and window", facts, deadlines, "platform",
                                  "return_window", "No refund window could be verified on the platform's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Take immediate photos of spoiled/damaged items", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: take photos showing the issue, packaging, and invoice bill." if p else
                           "Generic advice from us: photograph expired/damaged groceries and keep the delivery invoice.", p))
        c = _pick(facts, "claim_route", "platform")
        steps.append(_step(3, "Request refund in grocery app", _vals(c) if c else "No claim route could be verified on the platform's official page.",
                           "Our reading: submit refund request in app within hours of delivery." if c else
                           "We could not verify a route. Open app order history -> Need help with this order.", c))

    elif case_type == "furniture_delivery_issue":
        steps.append(_window_step(1, "Check furniture damage return and warranty policy", facts, deadlines, "seller",
                                  "return_window", "No return window could be verified on the seller's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Document transit damage and assembly report", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: photograph all damaged surfaces and note damage on the delivery/assembly acknowledgement." if p else
                           "Generic advice from us: photograph transit damages and note issues on delivery challan.", p))
        c = _pick(facts, "claim_route", "seller")
        steps.append(_step(3, "Initiate return, replacement or repair with seller", _vals(c) if c else "No claim route could be verified on the seller's official page.",
                           "Our reading: contact seller support before assembly technician leaves." if c else
                           "We could not verify a route. Raise a claim on the seller's website under Orders.", c))

    elif case_type == "counterfeit_product":
        steps.append(_window_step(1, "Check authenticity guarantee and return policy", facts, deadlines, "seller",
                                  "return_window", "No return window could be verified on the seller's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Gather proof of fake / counterfeit product", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: gather side-by-side comparison, serial number check with brand, invoice, and packaging." if p else
                           "Generic advice from us: save invoice, photos of fake packaging/serial number, and brand verification.", p))
        c = _pick(facts, "claim_route", "seller")
        steps.append(_step(3, "Demand return and full refund from seller", _vals(c) if c else "No claim route could be verified on the seller's official page.",
                           "Our reading: report counterfeit product to seller and platform anti-counterfeit team." if c else
                           "We could not verify a route. Contact seller support and report counterfeit goods.", c))

    elif case_type == "seller_cancelled_order":
        steps.append(_window_step(1, "Check order cancellation and refund timeline", facts, deadlines, "seller",
                                  "return_window", "No refund window could be verified on the seller's official page."))
        p = _pick(facts, "proof_required")
        steps.append(_step(2, "Save order confirmation and cancellation notice", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: save order confirmation email, debit transaction details, and unilateral cancellation notice." if p else
                           "Generic advice from us: save order confirmation and cancellation email.", p))
        c = _pick(facts, "claim_route", "seller")
        steps.append(_step(3, "Demand prompt refund and compensation", _vals(c) if c else "No claim route could be verified on the seller's official page.",
                           "Our reading: ask seller for immediate refund and compensatory credit for cancellation." if c else
                           "We could not verify a route. Contact customer service regarding cancelled order refund.", c))

    else:  # defective_product
        steps.append(_window_step(1, "Check the seller's return window", facts, deadlines, "seller",
                                  "return_window", "No return window could be verified on the seller's official page."))
        p = _pick(facts, "proof_required") + _pick(facts, "conditions", "seller")
        steps.append(_step(2, "Gather your proof", _vals(p) if p else "No specific proof requirement was verified.",
                           "Our reading: have the invoice, order ID and clear photos or a short video of the fault ready before you apply." if p else
                           "Generic advice from us, not from the page: keep the invoice, order ID and photos of the fault.", p))
        c = _pick(facts, "claim_route", "seller")
        steps.append(_step(3, "Start the claim with the seller", _vals(c) if c else "No claim route could be verified on the seller's official page.",
                           "Our reading: use this route first and save the reference number." if c else
                           "We could not verify a route. Use the Orders section of your account.", c))
        w = _pick(facts, "warranty_period", "manufacturer")
        wc = _pick(facts, "claim_route", "manufacturer")
        ex = _pick(facts, "exclusions", "manufacturer")
        mp = _pick(facts, "proof_required", "manufacturer")
        allw = w + mp + wc + ex
        steps.append(_step(4, "If the seller refuses, use the manufacturer warranty",
                           _vals(allw) if allw else "No warranty terms could be verified on the manufacturer's official page.",
                           "Our reading: warranty usually covers faults, not damage you caused. Check the exclusions before you apply." if allw else
                           "We could not verify the warranty terms. Open the brand's support page yourself.", allw))

    # Add legal rights step citing applicable laws
    leg = _legal_step(len(steps) + 1, case_type, country)
    if leg:
        steps.append(leg)

    # Add sector-specific regulator step if applicable
    reg = _regulator_step(len(steps) + 1, case_type, country)
    if reg:
        steps.append(reg)

    # General Consumer Commission escalation step
    steps.append(_general_escalation_step(len(steps) + 1, country))

    return steps
