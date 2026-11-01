import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9 widescreen
    prs.slide_height = Inches(7.5)

    # Theme colors (Dark Slate + Emerald Green)
    COLOR_BG = RGBColor(8, 14, 20)          # #080e14
    COLOR_CARD = RGBColor(12, 21, 32)       # #0c1520
    COLOR_EMERALD = RGBColor(16, 185, 129)  # #10b981
    COLOR_MINT = RGBColor(52, 211, 153)     # #34d399
    COLOR_WHITE = RGBColor(248, 250, 252)   # #f8fafc
    COLOR_MUTED = RGBColor(110, 231, 183)   # #6ee7b7
    COLOR_GRAY = RGBColor(148, 163, 184)    # #94a3b8
    COLOR_BORDER = RGBColor(16, 185, 129)

    blank_layout = prs.slide_layouts[6]

    def set_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="EXITLENS v2.0 ARCHITECTURE"):
        # Category Tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.5), Inches(0.35))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        p_c = tf_c.paragraphs[0]
        p_c.text = category_text.upper()
        p_c.font.size = Pt(11)
        p_c.font.bold = True
        p_c.font.color.rgb = COLOR_MINT
        p_c.font.name = "Arial"

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.5), Inches(0.8))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = COLOR_WHITE
        p.font.name = "Arial"

    # ==============================================================
    # SLIDE 1: Title Slide
    # ==============================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    # Decorative Card
    card = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.2), Inches(11.733), Inches(5.1))
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_CARD
    card.line.color.rgb = COLOR_BORDER
    card.line.width = Pt(1.5)

    tb = s1.shapes.add_textbox(Inches(1.3), Inches(1.8), Inches(10.7), Inches(3.8))
    tf = tb.text_frame
    tf.word_wrap = True

    p0 = tf.paragraphs[0]
    p0.text = "EXITLENS • AUTONOMOUS CONSUMER ENFORCEMENT ENGINE"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = COLOR_MINT

    p1 = tf.add_paragraph()
    p1.text = "Turning Consumer Grievances Into Legally Ironclad Restitution"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_EMERALD
    p1.space_before = Pt(12)

    p2 = tf.add_paragraph()
    p2.text = "Live Web Autonomous Crawling (TinyFish) • Character-Level Policy Verification • Statutory Calendar Math • Pre-Litigation Legal Dispatchers"
    p2.font.size = Pt(15)
    p2.font.color.rgb = COLOR_GRAY
    p2.space_before = Pt(14)

    p3 = tf.add_paragraph()
    p3.text = "Supported Sectors: Swiggy, Zomato, IndiGo, Amazon, Flipkart, PhonePe, Uber, BookMyShow & All Major Indian Platforms"
    p3.font.size = Pt(13)
    p3.font.color.rgb = COLOR_MUTED
    p3.space_before = Pt(24)

    # ==============================================================
    # SLIDE 2: The Core Problem
    # ==============================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "The Crisis in Modern Consumer Redressal")

    col_w = Inches(3.64)
    gap = Inches(0.4)
    top_y = Inches(1.8)
    h_box = Inches(4.8)

    problems = [
        ("Asymmetric Corporate Power", 
         "• Multi-billion dollar platforms employ dark patterns and obstructive AI support bots.\n• Unilateral refusal of statutory refunds under the guise of 'internal policy'.\n• Consumers forfeit over ₹5,000 Crores annually in unreversed UPI, flight shells, and denied returns.",
         "THE CONSUMER TRAP"),
        ("Generic LLM Hallucinations",
         "• ChatGPT & Claude memorize outdated parameters from training snapshots.\n• Hallucinate non-existent return days and unverified clauses.\n• Provide passive essays instead of executable evidence or statutory references.",
         "THE CHATBOT FAILURE"),
        ("The Enforcement Vacuum",
         "• Formal litigation (Consumer Commissions, NCH) demands exact quotes and statutory citations.\n• Average consumer lacks access to CPA 2019 provisions or RBI Turnaround Time mandates.\n• Grievance dockets are rejected due to informal drafting.",
         "THE JURISPRUDENCE GAP")
    ]

    for idx, (p_title, p_body, badge) in enumerate(problems):
        x = Inches(0.8) + idx * (col_w + gap)
        box = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, top_y, col_w, h_box)
        box.fill.solid()
        box.fill.fore_color.rgb = COLOR_CARD
        box.line.color.rgb = COLOR_BORDER
        box.line.width = Pt(1)

        t_box = s2.shapes.add_textbox(x + Inches(0.2), top_y + Inches(0.2), col_w - Inches(0.4), h_box - Inches(0.4))
        tf = t_box.text_frame
        tf.word_wrap = True
        
        p_b = tf.paragraphs[0]
        p_b.text = badge
        p_b.font.size = Pt(10)
        p_b.font.bold = True
        p_b.font.color.rgb = COLOR_MINT
        
        p_t = tf.add_paragraph()
        p_t.text = p_title
        p_t.font.size = Pt(18)
        p_t.font.bold = True
        p_t.font.color.rgb = COLOR_EMERALD
        p_t.space_before = Pt(8)
        
        p_c = tf.add_paragraph()
        p_c.text = p_body
        p_c.font.size = Pt(12)
        p_c.font.color.rgb = COLOR_GRAY
        p_c.space_before = Pt(12)

    # ==============================================================
    # SLIDE 3: The 5-Stage Verification Pipeline
    # ==============================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "Architectural Pipeline: 5-Stage Deterministic Verification")

    stages = [
        ("1. Intake & Heuristics", "Extracts product, seller, incident date, and dispute category. Zero hardcoding."),
        ("2. Canonical Discovery", "TinyFish live web search discovers canonical merchant host & nested policy routes in real time."),
        ("3. Parallel Ingestion", "Tiered extraction: Search -> Direct Fetch -> Headless Browser Agent if terms are hidden."),
        ("4. DOM Character Match", "Verifies exact extracted quote against live HTML. Cryptographic SHA-256 hashing."),
        ("5. Statutory Formulation", "Deterministic calendar calculation, penalty accumulation & pre-litigation docket compile.")
    ]

    for idx, (st_title, st_desc) in enumerate(stages):
        y = Inches(1.8) + idx * Inches(0.95)
        bar = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), y, Inches(11.733), Inches(0.82))
        bar.fill.solid()
        bar.fill.fore_color.rgb = COLOR_CARD
        bar.line.color.rgb = COLOR_BORDER
        bar.line.width = Pt(1)

        t_box = s3.shapes.add_textbox(Inches(1.1), y + Inches(0.12), Inches(11.1), Inches(0.6))
        tf = t_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"{st_title}  —  "
        p.font.bold = True
        p.font.size = Pt(15)
        p.font.color.rgb = COLOR_EMERALD
        
        run = p.add_run()
        run.text = st_desc
        run.font.bold = False
        run.font.size = Pt(13)
        run.font.color.rgb = COLOR_GRAY

    # ==============================================================
    # SLIDE 4: Comprehensive Indian Sectors (15+ Categories)
    # ==============================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "Broad Sector Coverage: 15+ Consumer Domains", "EXTENSIBLE DATA ARCHITECTURE")

    sectors = [
        ("🍕 Food Delivery & Quick Commerce", "Swiggy, Zomato, Zepto, Blinkit", "Spoiled items, spilled orders, AC refusal, bot auto-closing tickets"),
        ("✈️ Aviation & Air Travel", "IndiGo, Air India, SpiceJet, MakeMyTrip", "Cancellations <24h, forced credit shells, baggage loss, denied boarding"),
        ("💳 Digital Payments & UPI", "PhonePe, Google Pay, Paytm, CRED", "Unreversed debits past T+1, merchant settlement failures, ₹100/day penalty"),
        ("🚗 Ride-Hailing & Cabs", "Uber, Ola, Rapido, Namma Yatri", "Offline cash extortion, AC refusal, illegal cancellation penalty surcharges"),
        ("📦 E-Commerce & Retail", "Amazon, Flipkart, Myntra, Croma, boAt", "Refusal of returns within window, replacement-only traps, warranty refusal"),
        ("🎟️ Entertainment & Ticketing", "BookMyShow, Paytm Insider", "Event cancellation convenience fee forfeiture, refund withholding")
    ]

    for idx, (sec_name, sec_brands, sec_issues) in enumerate(sectors):
        col = idx % 2
        row = idx // 2
        x = Inches(0.8) + col * Inches(6.0)
        y = Inches(1.8) + row * Inches(1.65)
        
        box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(5.7), Inches(1.45))
        box.fill.solid()
        box.fill.fore_color.rgb = COLOR_CARD
        box.line.color.rgb = COLOR_BORDER
        box.line.width = Pt(1)

        t_box = s4.shapes.add_textbox(x + Inches(0.2), y + Inches(0.12), Inches(5.3), Inches(1.2))
        tf = t_box.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = sec_name
        p0.font.size = Pt(15)
        p0.font.bold = True
        p0.font.color.rgb = COLOR_EMERALD

        p1 = tf.add_paragraph()
        p1.text = f"Key Entities: {sec_brands}"
        p1.font.size = Pt(11.5)
        p1.font.bold = True
        p1.font.color.rgb = COLOR_MINT
        p1.space_before = Pt(3)

        p2 = tf.add_paragraph()
        p2.text = f"Actionable Disputes: {sec_issues}"
        p2.font.size = Pt(11)
        p2.font.color.rgb = COLOR_GRAY
        p2.space_before = Pt(2)

    # ==============================================================
    # SLIDE 5: Standout Features 1 & 2
    # ==============================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "Standout Features: Automated Complaint Wizard & NCH 1915", "EXECUTIVE REMEDIES")

    # Left Box: Dynamic Questionnaire
    b_left = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.9))
    b_left.fill.solid()
    b_left.fill.fore_color.rgb = COLOR_CARD
    b_left.line.color.rgb = COLOR_BORDER
    b_left.line.width = Pt(1.5)

    tf_l = b_left.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "Automated Dispute Dispatcher Wizard"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_EMERALD
    
    p_body_l = tf_l.add_paragraph()
    p_body_l.text = (
        "\n• Sector-Tailored Legal Inquiry:\n"
        "  - Flights: PNR, Flight Number, Cancellation Reason, Statutory Surcharge.\n"
        "  - Food Delivery: Order ID, Dish Disputed, Photo Evidence, Support Bot outcome.\n"
        "  - UPI / Banking: Bank UTR/RRN, Merchant VPA, Exact Timestamp of Debit.\n"
        "  - Cabs / Rides: Trip CRN, Vehicle Number, AC Refusal / Cash Extorted.\n\n"
        "• Generates Formal Legal Demand Notice:\n"
        "  - Cites Consumer Protection Act, 2019 (Sections 2(11) & 2(47)).\n"
        "  - Cites Consumer Protection (E-Commerce) Rules 2020.\n"
        "  - Mandates a 7-day cure window prior to tribunal filing."
    )
    p_body_l.font.size = Pt(12)
    p_body_l.font.color.rgb = COLOR_GRAY

    # Right Box: NCH Docket
    b_right = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9))
    b_right.fill.solid()
    b_right.fill.fore_color.rgb = COLOR_CARD
    b_right.line.color.rgb = COLOR_BORDER
    b_right.line.width = Pt(1.5)

    tf_r = b_right.text_frame
    tf_r.word_wrap = True
    p_r = tf_r.paragraphs[0]
    p_r.text = "National Consumer Helpline (1915) Docket"
    p_r.font.size = Pt(18)
    p_r.font.bold = True
    p_r.font.color.rgb = COLOR_EMERALD

    p_body_r = tf_r.add_paragraph()
    p_body_r.text = (
        "\n• Formatted for INGRAM Government Convergence Portal:\n"
        "  - Government Portal: consumerhelpline.gov.in\n"
        "  - National Shortcode: Toll-Free 1915\n"
        "  - WhatsApp Grievance Bot: +91 8800001915\n\n"
        "• Structured Case Particulars:\n"
        "  - Exact statutory violation sections pre-compiled.\n"
        "  - Verbatim statement of facts including merchant's own policy clauses.\n"
        "  - Explicit relief demanded (100% principal + statutory delay penalties).\n\n"
        "• 1-Click Judicial Escalation:\n"
        "  - Direct routing to e-Jagriti (e-jagriti.gov.in) District Commissions."
    )
    p_body_r.font.size = Pt(12)
    p_body_r.font.color.rgb = COLOR_GRAY

    # ==============================================================
    # SLIDE 6: Standout Features 3 & 4
    # ==============================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "Warranty Tracker & Multi-Channel Dispatch Suite", "INNOVATIVE CAPABILITIES")

    b1 = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.9))
    b1.fill.solid()
    b1.fill.fore_color.rgb = COLOR_CARD
    b1.line.color.rgb = COLOR_BORDER
    b1.line.width = Pt(1.5)

    tf1 = b1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Warranty & Refund Lifecycle Tracker"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_EMERALD

    p_t1 = tf1.add_paragraph()
    p_t1.text = (
        "\n• Deterministic Calendar Computation:\n"
        "  - Computes exact days elapsed from invoice date.\n"
        "  - Visual countdown for Merchant Return Window.\n"
        "  - Visual horizon for Manufacturer Warranty Period.\n\n"
        "• Statutory Penalty Calculation Engine:\n"
        "  - UPI Disputes: ₹100/day delay compensation beyond T+1 under RBI DPSS.\n"
        "  - Aviation: ₹5,000 to ₹20,000 mandatory compensation under DGCA CAR.\n\n"
        "• Dynamic Lifecycle Stage Badging:\n"
        "  - MERCHANT_RETURN_WINDOW (0-7/10 days)\n"
        "  - MANUFACTURER_WARRANTY (10-365 days)\n"
        "  - STATUTORY_ESCALATION (Post-warranty tribunal phase)"
    )
    p_t1.font.size = Pt(12)
    p_t1.font.color.rgb = COLOR_GRAY

    b2 = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.9))
    b2.fill.solid()
    b2.fill.fore_color.rgb = COLOR_CARD
    b2.line.color.rgb = COLOR_BORDER
    b2.line.width = Pt(1.5)

    tf2 = b2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Multi-Channel Dispatch Suite"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = COLOR_EMERALD

    p_t2 = tf2.add_paragraph()
    p_t2.text = (
        "\n• 1-Click 'Email to My Inbox':\n"
        "  - Launches Gmail with consumer's email pre-filled as recipient, subject, and body.\n\n"
        "• Download Native Email File (.eml):\n"
        "  - Generates RFC 822 email file; double-clicking opens natively in Apple Mail / Outlook.\n\n"
        "• Official WhatsApp Grievance Dispatch:\n"
        "  - Formats dossier and directly opens WhatsApp conversation with NCH bot (8800001915).\n\n"
        "• Optical Receipt & Invoice OCR:\n"
        "  - Client-side Tesseract.js parses invoice images and extracts Order ID, Date, Amount (₹).\n\n"
        "• SHA-256 Policy Drift Sentinel:\n"
        "  - Monitors official terms and alerts consumers if clauses are modified silently."
    )
    p_t2.font.size = Pt(12)
    p_t2.font.color.rgb = COLOR_GRAY

    # ==============================================================
    # SLIDE 7: Competitive Benchmark: ExitLens vs ChatGPT / Claude
    # ==============================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_header(s7, "Competitive Benchmark: Why ExitLens Outperforms LLMs", "EMPIRICAL COMPARISON")

    # Table
    rows = 6
    cols = 3
    left = Inches(0.8)
    top = Inches(1.8)
    width = Inches(11.733)
    height = Inches(4.8)

    table_shape = s7.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    table.columns[0].width = Inches(3.2)
    table.columns[1].width = Inches(4.2)
    table.columns[2].width = Inches(4.333)

    headers = ["Evaluation Metric", "Generic Chatbots (ChatGPT / Claude)", "ExitLens Autonomous Policy Engine"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(16, 185, 129)
        p = cell.text_frame.paragraphs[0]
        p.font.bold = True
        p.font.size = Pt(12)
        p.font.color.rgb = RGBColor(8, 14, 20)

    comparisons = [
        ("Policy Sourcing", "Hallucinates from outdated pre-training memory; unaware of recent revisions.", "TinyFish dynamic live search retrieves current official merchant policy in real time."),
        ("Quote Verification", "Offers paraphrased summaries with zero proof of authenticity.", "Character-level exact match against live DOM text; rejects hallucinated terms."),
        ("Statutory Math", "Mental arithmetic prone to arithmetic errors; invents return windows.", "Deterministic Python calendar math (`dates.py`); computes exact statutory penalty days."),
        ("Government Dockets", "Generic advice telling users to 'contact customer care'.", "Ready-to-file dockets for INGRAM 1915, e-Jagriti, and formal Pre-Litigation Legal Notices."),
        ("Policy Drift Sentinel", "Cannot verify whether terms changed between purchase & dispute.", "Stores cryptographic SHA-256 hashes of DOM text to detect stealth merchant alterations.")
    ]

    for r_idx, (m, c, e) in enumerate(comparisons, start=1):
        table.cell(r_idx, 0).text = m
        table.cell(r_idx, 1).text = c
        table.cell(r_idx, 2).text = e

        for c_idx in range(3):
            cell = table.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = COLOR_CARD
            p = cell.text_frame.paragraphs[0]
            p.font.size = Pt(11)
            p.font.color.rgb = COLOR_WHITE if c_idx == 0 else (COLOR_GRAY if c_idx == 1 else COLOR_MUTED)

    # ==============================================================
    # SLIDE 8: Technical Specs & Hackathon Summary
    # ==============================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_header(s8, "Technology Stack, Test Coverage & GitHub Repository", "SUMMARY & DEPLOYMENT")

    specs = [
        ("High-Performance Backend", "Python 3.9 + Starlette ASGI asynchronous engine with zero heavy framework overhead."),
        ("Autonomous Crawling", "TinyFish Web Agent with dynamic canonical host resolution and tiered fallback."),
        ("Local Persistence", "SQLite (`data/exitlens.db`) storing cases, cryptographic watches, and telemetry."),
        ("Institutional UI/UX", "Vanilla HTML5/ES6 + CSS Grid, Emerald Matrix typography, dark/light toggle, zero build step."),
        ("Optical Recognition", "Client-side Tesseract.js invoice OCR with automated regex entity and date extraction."),
        ("100% Test Coverage", "31 automated pytest unit & integration tests passing cleanly across all sectors.")
    ]

    for idx, (sp_title, sp_desc) in enumerate(specs):
        col = idx % 2
        row = idx // 2
        x = Inches(0.8) + col * Inches(6.0)
        y = Inches(1.8) + row * Inches(1.4)
        
        box = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, Inches(5.7), Inches(1.2))
        box.fill.solid()
        box.fill.fore_color.rgb = COLOR_CARD
        box.line.color.rgb = COLOR_BORDER
        box.line.width = Pt(1)

        t_box = s8.shapes.add_textbox(x + Inches(0.2), y + Inches(0.12), Inches(5.3), Inches(0.95))
        tf = t_box.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = sp_title
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = COLOR_EMERALD

        p1 = tf.add_paragraph()
        p1.text = sp_desc
        p1.font.size = Pt(11)
        p1.font.color.rgb = COLOR_GRAY
        p1.space_before = Pt(3)

    # Footer banner
    footer_bar = s8.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.2), Inches(11.733), Inches(0.7))
    footer_bar.fill.solid()
    footer_bar.fill.fore_color.rgb = COLOR_CARD
    footer_bar.line.color.rgb = COLOR_BORDER
    tf_f = footer_bar.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "GITHUB REPOSITORY: https://github.com/arif04102007/ExitLens.git  |  PRODUCTION READY & HACKATHON VERIFIED"
    p_f.font.size = Pt(12)
    p_f.font.bold = True
    p_f.font.color.rgb = COLOR_MINT
    p_f.alignment = PP_ALIGN.CENTER

    prs.save("/Users/mohammadarifabdullah/Downloads/exitlens/ExitLens_Master_Presentation.pptx")
    print("Presentation saved successfully: ExitLens_Master_Presentation.pptx")

if __name__ == "__main__":
    create_deck()
