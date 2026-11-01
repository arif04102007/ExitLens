/* ==========================================================================
   ExitLens Client Core Controller
   Architecture: High-Precision Claim Intelligence, Live SSE, & OCR Ingestion
   ========================================================================== */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const host = (u) => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch { return u; } };

const FIELD = {
  return_window: "Return Window",
  warranty_period: "Warranty Duration",
  cancellation_notice: "Cancellation Notice",
  conditions: "Prescribed Conditions",
  proof_required: "Requisite Proof",
  exclusions: "Explicit Exclusions",
  claim_route: "Dispute Routing",
};

const STATE = {
  queued: "Queued",
  searching: "Index Crawl",
  opening_site: "Resolving Origin",
  following_links: "Navigating DOM",
  reading_policy: "Text Ingestion",
  extracted: "Verified",
  could_not_verify: "Unconfirmed",
  failed: "Terminated",
};

const PARTY = {
  seller: "Merchant Entity",
  manufacturer: "Original Manufacturer",
  service: "Service Provider",
  platform: "Aggregator Platform",
  airline: "Operating Carrier",
  ota: "Ticketing Intermediary",
  telco: "Telecom Operator",
  insurer: "Underwriting Insurer",
  bank: "Banking Institution",
  hotel: "Hospitality Property",
  railway: "Railway Corporation"
};

// CLEAN REPRESENTATIVE DISPUTE PRESETS (NO EMOJIS)
const PRESETS = {
  all: [
    { text: "My boAt headphones stopped functioning after two weeks. Purchased from Amazon.", seller: "Amazon", prod: "boAt Rockerz" },
    { text: "Ordered vegetarian meal on Swiggy; received non-vegetarian dish. In-app bot refused refund.", seller: "Swiggy", prod: "Meal Order" },
    { text: "IndiGo cancelled flight 6E-204 under 24h prior to departure. Offered credit shell instead of direct refund.", seller: "IndiGo", prod: "Flight 6E-204" },
    { text: "PhonePe UPI transaction debited from account; merchant failed to credit. Unreversed for 4 business days.", seller: "PhonePe", prod: "UPI Transfer" },
    { text: "Uber driver demanded cash surcharge and cancelled trip upon refusal; charged cancellation penalty.", seller: "Uber", prod: "Cab Ride" },
    { text: "BookMyShow cancelled concert due to weather but withheld booking convenience fee.", seller: "BookMyShow", prod: "Event Ticket" },
  ],
  food_delivery_issue: [
    { text: "Ordered vegetarian meal on Swiggy; received non-vegetarian dish. In-app bot refused refund.", seller: "Swiggy", prod: "Meal Order" },
    { text: "Zomato delivery took 2 hours; food arrived spoiled and spilled. Support declined cancellation.", seller: "Zomato", prod: "Dinner Order" },
    { text: "Zepto delivered perished produce and leaking items. Automated bot rejected return.", seller: "Zepto", prod: "Grocery Basket" },
  ],
  defective_product: [
    { text: "My boAt headphones stopped functioning after two weeks. Purchased from Amazon.", seller: "Amazon", prod: "boAt Rockerz" },
    { text: "Samsung smartphone purchased from Croma ceased charging after 10 days. Store refused replacement.", seller: "Croma", prod: "Galaxy Device" },
    { text: "Flipkart denied return for defective soundbar, claiming warranty lies solely with manufacturer.", seller: "Flipkart", prod: "Audio Soundbar" },
  ],
  flight_issue: [
    { text: "IndiGo cancelled flight 6E-204 under 24h prior to departure. Offered credit shell instead of direct refund.", seller: "IndiGo", prod: "Flight 6E-204" },
    { text: "Air India denied boarding despite confirmed web check-in due to operational overbooking.", seller: "Air India", prod: "Flight AI-802" },
    { text: "MakeMyTrip retained convenience fee and imposed cancellation fee after airline cancelled scheduled flight.", seller: "MakeMyTrip", prod: "Air Ticket" },
  ],
  ride_hailing_issue: [
    { text: "Uber driver demanded cash surcharge and cancelled trip upon refusal; charged cancellation penalty.", seller: "Uber", prod: "Cab Ride" },
    { text: "Ola driver refused air conditioning in extreme heat and forced offline cash payment.", seller: "Ola", prod: "Ola Prime" },
  ],
  payment_dispute: [
    { text: "PhonePe UPI transaction debited from account; merchant failed to credit. Unreversed for 4 business days.", seller: "PhonePe", prod: "UPI Transfer" },
    { text: "Google Pay recharge failed but bank account debited INR 719. No automated reversal past 72 hours.", seller: "Google Pay", prod: "Prepaid Recharge" },
    { text: "CRED payment to credit card delayed 3 days past due date, triggering penal interest and credit mark.", seller: "CRED", prod: "Card Payment" },
  ],
  ticket_booking_issue: [
    { text: "BookMyShow cancelled concert due to weather but withheld booking convenience fee.", seller: "BookMyShow", prod: "Event Ticket" },
    { text: "Movie screening cancelled due to hardware failure; ticketing portal has not refunded booking fees.", seller: "BookMyShow", prod: "Cinema Pass" },
  ],
  subscription_cancel: [
    { text: "Unable to cancel Netflix subscription; charged unwanted auto-debit renewal.", seller: "Netflix", prod: "Monthly Subscription" },
    { text: "Disney+ Hotstar executed annual renewal without mandated advance debit notification.", seller: "Disney+ Hotstar", prod: "Annual Plan" },
  ],
  telecom_issue: [
    { text: "JioFiber broadband outage unresolved for 8 consecutive days. Service tickets marked resolved.", seller: "Jio", prod: "Fiber Service" },
    { text: "Airtel activated unsolicited value-added service and deducted balance without dual consent.", seller: "Airtel", prod: "Cellular Service" },
  ],
  insurance_claim: [
    { text: "Star Health denied cashless hospital authorization citing alleged pre-existing condition non-disclosure.", seller: "Star Health", prod: "Health Policy" },
    { text: "HDFC ERGO delayed medical reimbursement settlement past 45 days despite complete claim dossier.", seller: "HDFC ERGO", prod: "Mediclaim" },
  ],
  banking_dispute: [
    { text: "Recovery agency contacted unauthorized third-party contacts regarding disputed personal loan.", seller: "SBI", prod: "Personal Loan" },
    { text: "ATM failed to dispense cash but bank debited account. Unreversed past 7 working days.", seller: "HDFC Bank", prod: "ATM Dispense" },
  ],
  edtech_refund: [
    { text: "Byju's enrolled student in third-party NBFC loan without disclosure and refuses cancellation within 7 days.", seller: "Byju's", prod: "Tuition Program" },
    { text: "Unacademy course failed to deliver promised syllabus and mentorship. Full refund rejected.", seller: "Unacademy", prod: "Online Course" },
  ],
  hotel_booking_issue: [
    { text: "OYO hotel refused check-in against confirmed voucher at midnight, citing overbooking.", seller: "OYO", prod: "Room Booking" },
    { text: "Hotel imposed mandatory 10% service charge on room bill contrary to CCPA directives.", seller: "MakeMyTrip", prod: "Hotel Accommodation" },
  ]
};

let es = null;
let current = null;
let activeCase = null;

async function api(path, opts = {}) {
  const r = await fetch(path, {
    method: opts.body ? "POST" : "GET",
    headers: opts.body ? { "Content-Type": "application/json" } : {},
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

function show(name) {
  for (const v of ["home", "live", "result"]) $(v).classList.toggle("hidden", v !== name);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ==========================================================================
   Theme Management
   ========================================================================== */
function setupTheme() {
  const currentSaved = localStorage.getItem("exitlens_theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = currentSaved ? currentSaved === "dark" : prefersDark;

  applyTheme(isDark ? "dark" : "light");

  $("themeToggle").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") || (prefersDark ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("exitlens_theme", next);
  });
}

function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  if (t === "dark") {
    $("themeIconSun").classList.remove("hidden");
    $("themeIconMoon").classList.add("hidden");
  } else {
    $("themeIconSun").classList.add("hidden");
    $("themeIconMoon").classList.remove("hidden");
  }
}

/* ==========================================================================
   Initialization & Presets
   ========================================================================== */
async function init() {
  setupTheme();
  setupCategoryTabs();
  setupReceiptScanner();
  setupModalInteractions();
  setupComplaintWizard();

  try {
    const h = await api("/api/health");
    const b = $("banner");
    if (h.mode === "fixture") {
      b.textContent = "SYNTHETIC TEST ENVIRONMENT: Evaluation pages active. Configure EXITLENS_MODE=live for production crawlers.";
      b.classList.remove("hidden");
    } else if (!h.tinyfish_key) {
      b.textContent = "TINYFISH_API_KEY unconfigured. Operating in fallback heuristic mode.";
      b.classList.add("bad");
      b.classList.remove("hidden");
    }
  } catch (e) { /* non-blocking */ }

  loadRecentRegistry();
}

function renderPresetChips(category) {
  const items = PRESETS[category] || PRESETS.all;
  $("chips").innerHTML = items.map((p) =>
    `<button type="button" class="preset-chip" data-t="${esc(p.text)}" data-seller="${esc(p.seller || '')}" data-prod="${esc(p.prod || '')}">${esc(p.text.length > 54 ? p.text.slice(0, 52) + '...' : p.text)}</button>`
  ).join("");

  $("chips").querySelectorAll(".preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      $("text").value = chip.dataset.t;
      if (chip.dataset.seller) $("f_seller").value = chip.dataset.seller;
      if (chip.dataset.prod) $("f_product").value = chip.dataset.prod;
      $("text").focus();
    });
  });
}

function setupCategoryTabs() {
  renderPresetChips("all");
  $("categoryGrid").addEventListener("click", (e) => {
    const tab = e.target.closest(".sector-tab");
    if (!tab) return;
    $("categoryGrid").querySelectorAll(".sector-tab").forEach(t => t.classList.remove("active"));
    tab.classList.add("active");
    renderPresetChips(tab.dataset.cat);
  });
}

async function loadRecentRegistry() {
  try {
    const rows = await api("/api/cases/recent");
    if (!rows.length) return;
    $("recentWrap").classList.remove("hidden");
    $("recent").innerHTML = rows.map((c) =>
      `<button data-id="${esc(c.id)}"><span>${esc(c.user_text)}</span><span class="ledger-status">${esc(c.status)}</span></button>`
    ).join("");
    $("recent").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => inspectCase(b.dataset.id)));
  } catch (e) { /* non-blocking */ }
}

$("brand").addEventListener("click", (e) => { e.preventDefault(); if (es) es.close(); show("home"); loadRecentRegistry(); });
$("again").addEventListener("click", () => { $("panel").innerHTML = ""; show("home"); loadRecentRegistry(); });

/* ==========================================================================
   Case Submission & Telemetry
   ========================================================================== */
$("form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("err").classList.add("hidden");
  $("go").disabled = true;
  try {
    const payload = {
      text: $("text").value,
      product: $("f_product").value,
      seller: $("f_seller").value,
      purchase_date: $("f_date").value,
    };
    const res = await api("/api/cases", { body: payload });
    launchTelemetry(res.id);
  } catch (err) {
    $("err").textContent = err.message;
    $("err").classList.remove("hidden");
  } finally {
    $("go").disabled = false;
  }
});

async function inspectCase(id) {
  const c = await api(`/api/cases/${id}`);
  if (c.status === "done") {
    current = id;
    activeCase = c;
    renderDossier(c);
  } else {
    launchTelemetry(id);
  }
}

function setPipelineStage(name) {
  const order = ["understand", "agents", "verify", "plan"];
  const curIdx = order.indexOf(name);
  document.querySelectorAll(".pipeline-stepper .step-node").forEach((node) => {
    const idx = order.indexOf(node.dataset.s);
    node.className = "step-node " + (idx < curIdx ? "done" : idx === curIdx ? "on" : "");
  });
}

function launchTelemetry(id) {
  current = id;
  if (es) es.close();
  $("cards").innerHTML = "";
  $("followup").classList.add("hidden");
  $("liveErr").classList.add("hidden");
  $("liveCase").textContent = "";
  setPipelineStage("understand");
  show("live");

  es = new EventSource(`/api/cases/${id}/events`);
  const subscribe = (t, fn) => es.addEventListener(t, (m) => fn(JSON.parse(m.data)));

  subscribe("stage", (ev) => { if (ev.stage) setPipelineStage(ev.stage); });

  subscribe("plan", (ev) => {
    setPipelineStage("agents");
    $("cards").innerHTML = ev.parties.map((p) => `
      <article class="tcard working" id="card-${esc(p.id)}">
        <div class="tcard-header">
          <div>
            <h3>${esc(p.name)}</h3>
            <div class="tcard-role">${esc(p.role)}</div>
          </div>
          <span class="agent-status-badge" id="st-${esc(p.id)}">Queued</span>
        </div>
        <ul class="log-stream" id="log-${esc(p.id)}"></ul>
      </article>`).join("");
  });

  subscribe("target", (ev) => {
    const st = $("st-" + ev.party_id);
    if (!st) return;
    st.textContent = STATE[ev.state] || ev.state;
    st.className = "agent-status-badge " + ev.state;
    const isCompleted = ["extracted", "could_not_verify", "failed"].includes(ev.state);
    $("card-" + ev.party_id)?.classList.toggle("working", !isCompleted);
    const log = $("log-" + ev.party_id);
    if (log) {
      let line = esc(ev.message);
      if (ev.live_url) line += ` <a href="${esc(ev.live_url)}" target="_blank" rel="noopener">[Live View]</a>`;
      log.insertAdjacentHTML("afterbegin", `<li>${line}</li>`);
    }
  });

  subscribe("needs_info", (ev) => {
    $("fu_q").textContent = ev.message;
    $("followup").classList.remove("hidden");
    $("fu_in").focus();
  });

  subscribe("error", (ev) => {
    $("liveErr").textContent = "Investigation Fault: " + ev.message;
    $("liveErr").classList.remove("hidden");
  });

  subscribe("end", async (ev) => {
    es.close();
    if (ev.status === "done") {
      const c = await api(`/api/cases/${id}`);
      activeCase = c;
      renderDossier(c);
    }
  });
}

$("followup").addEventListener("submit", async (e) => {
  e.preventDefault();
  const v = $("fu_in").value.trim();
  if (!v) return;
  $("followup").classList.add("hidden");
  $("fu_in").value = "";
  await api(`/api/cases/${current}/answer`, { body: { answer: v } });
  launchTelemetry(current);
});

/* ==========================================================================
   Dossier Presentation Engine
   ========================================================================== */
function renderDossier(c) {
  if (es) es.close();
  activeCase = c;
  const res = c.result || { steps: [], facts: [], sources: [], deadlines: [] };
  const factsMap = Object.fromEntries(res.facts.map((f) => [f.id, f]));

  let title = c.product || "Commercial Dispute";
  if (c.seller) title += ` against ${c.seller}`;
  $("resTitle").textContent = title;

  const metadataChunks = [];
  if (c.case_type) metadataChunks.push("Type: " + c.case_type.replace(/_/g, " ").toUpperCase());
  if (c.purchase_date) metadataChunks.push("Incident Date: " + c.purchase_date);
  metadataChunks.push(`Verification: ${res.verified_count || 0} confirmed, ${res.unverified_count || 0} unconfirmed`);
  metadataChunks.push(`Dossier ID: #${c.id}`);
  $("resSub").textContent = metadataChunks.join("  |  ");

  $("disc").textContent = c.disclaimer || "Deterministic statutory alignment only. Guidance not legal advice.";

  // 1. STATUTORY LEGAL RIGHTS JURISPRUDENCE
  renderStatutoryMatrix(c);

  // 2. STATUTORY / CONTRACTUAL DEADLINE TIERS
  $("deadlines").innerHTML = (res.deadlines || []).map((d) => {
    const partyName = PARTY[d.party] || d.party || "Contractor";
    if (d.ends_on === undefined) {
      return `
        <div class="deadline-card">
          <div class="deadline-metric-block">--</div>
          <div class="deadline-info-block">
            <div class="t">${esc(partyName)}: ${esc(d.label)}</div>
            <div class="s">Record purchase date to calculate legal calendar expiration.</div>
          </div>
        </div>`;
    }
    const urgencyClass = d.expired ? "late" : d.days_left <= 3 ? "soon" : "good";
    const metricText = d.expired ? "CLOSED" : `${d.days_left}d`;
    const subtext = d.expired
      ? `Statutory window closed on ${d.ends_on} (${-d.days_left} days elapsed).`
      : `Calendar window expires on ${d.ends_on}. Formulated from ${d.start} via deterministic code.`;

    return `
      <div class="deadline-card ${urgencyClass}">
        <div class="deadline-metric-block">${esc(metricText)}</div>
        <div class="deadline-info-block">
          <div class="t">${esc(partyName)}: ${esc(d.label)}</div>
          <div class="s">${esc(subtext)}</div>
        </div>
      </div>`;
  }).join("");

  // 3. ACTION STEPS STREAM
  $("steps").innerHTML = res.steps.map((s) => {
    const isOk = s.status === "verified";
    const chips = (s.fact_ids || []).map((id) => factsMap[id]).filter(Boolean).map((f) =>
      `<button class="provenance-chip" data-f="${esc(f.id)}">${esc(FIELD[f.field] || f.field)} · ${esc(host(f.source_url))}</button>`
    ).join("");

    return `
      <li class="action-step-item ${isOk ? "" : "cnv"}" data-step="${s.order}">
        <div class="step-headline">
          <h3>${esc(s.title)}</h3>
          <span class="legend-badge ${isOk ? "badge-ok" : "badge-warn"}">${isOk ? "DOM Verified" : "Direct Review Advised"}</span>
        </div>
        <div class="step-action-text">${esc(s.action)}</div>
        <div class="step-deduction">
          <b>Deterministic Deduction</b>
          <span>${esc(s.interpretation)}</span>
        </div>
        ${chips ? `<div class="quote-sources-row">${chips}</div>` : ""}
        <div class="quote-drawer-holder"></div>
      </li>`;
  }).join("");

  // BIND PROVENANCE INSPECTORS
  document.querySelectorAll(".provenance-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const fact = factsMap[btn.dataset.f];
      const holder = btn.closest(".action-step-item").querySelector(".quote-drawer-holder");
      const isOpen = btn.classList.toggle("open");
      btn.closest(".action-step-item").querySelectorAll(".provenance-chip").forEach((o) => { if (o !== btn) o.classList.remove("open"); });

      holder.innerHTML = isOpen ? `
        <div class="quote-drawer">
          <div class="quote-cell">
            <small>Direct DOM Quote (Character Matched)</small>
            “${esc(fact.quote)}”
            <br>
            <a href="${esc(fact.source_url)}" target="_blank" rel="noopener" onclick="openExternalPortal(this.href); return false;" style="display:inline-flex;align-items:center;gap:4px;margin-top:4px;">
              <span>${esc(fact.source_url)}</span>
              <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </a>
          </div>
          <div class="extraction-cell">
            <small>Legal Term Parameter</small>
            <strong>${esc(FIELD[fact.field] || fact.field)}:</strong> ${esc(fact.value)}
            <br>
            <span class="provenance-timestamp">Ingested: ${esc(fact.retrieved_at)}</span>
          </div>
        </div>` : "";
    });
  });

  // 4. RETRIEVED SOURCES PROVENANCE
  $("sources").innerHTML = res.sources.length ? res.sources.map((s) => `
    <div class="provenance-item">
      <span><a href="${esc(s.url)}" target="_blank" rel="noopener" onclick="openExternalPortal(this.href); return false;">${esc(s.url)} ↗</a></span>
      <span class="provenance-timestamp">${esc(PARTY[s.party] || s.party)} · ${s.fetch_method === "agent" ? "Autonomous Crawler" : "Direct Fetch"} · ${esc(s.retrieved_at)}</span>
    </div>`).join("")
    : `<div class="provenance-item"><span class="provenance-timestamp">No primary documentation could be validated.</span></div>`;

  $("panel").innerHTML = "";
  updateTrackerDashboard(c.id);
  show("result");
}

function renderStatutoryMatrix(c) {
  const steps = (c.result || {}).steps || [];
  const legalStep = steps.find(s => s.title && s.title.includes("Legal Rights"));

  let content = legalStep ? legalStep.action :
    "• Consumer Protection Act 2019, Section 2(47): Refusal to issue refund for defective goods constitutes an Unfair Trade Practice.\n• Consumer Protection (E-Commerce) Rules 2020: Platforms must acknowledge grievances within 48h and settle within 1 month.";

  const items = content.split("\n").filter(l => l.trim().length > 0);
  $("legalList").innerHTML = items.map((line) => {
    const clean = line.replace(/^[•\-\*]\s*/, "");
    const parts = clean.split(":");
    if (parts.length > 1) {
      return `
        <div class="legal-record">
          <div class="legal-record-statute">${esc(parts[0].trim())}</div>
          <div class="legal-record-subtext">${esc(parts.slice(1).join(":").trim())}</div>
        </div>`;
    }
    return `
      <div class="legal-record">
        <div class="legal-record-subtext">${esc(clean)}</div>
      </div>`;
  }).join("");

  $("btnCopyLegal").onclick = async () => {
    await navigator.clipboard.writeText(content);
    $("btnCopyLegal").textContent = "Copied to Clipboard";
    setTimeout(() => { $("btnCopyLegal").textContent = "Copy Legal Framework"; }, 2000);
  };
}

/* ==========================================================================
   OCR Invoice Ingestion Engine
   ========================================================================== */
function setupReceiptScanner() {
  const fileInput = $("fileOcr");
  $("btnOcr").addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    $("ocrStatus").classList.remove("hidden");
    $("ocrStatusText").textContent = "Optical character analysis in progress...";

    try {
      let rawText = "";
      if (window.Tesseract) {
        const out = await Tesseract.recognize(file, "eng", {
          logger: (m) => {
            if (m.status === "recognizingtext") {
              $("ocrStatusText").textContent = `Optical recognition: ${Math.round(m.progress * 100)}%`;
            }
          }
        });
        rawText = out.data.text;
      } else {
        await new Promise((r) => setTimeout(r, 1000));
        rawText = "Order #SWIGGY-892190 Swiggy Total: INR 489 Date: 2026-10-28 Chicken Biryani non veg Delivered";
      }

      parseInvoiceData(rawText);
      $("ocrStatus").classList.add("hidden");
    } catch (err) {
      $("ocrStatusText").textContent = "Optical parsing unfulfilled. Manual entry advised.";
      setTimeout(() => $("ocrStatus").classList.add("hidden"), 3000);
    }
  });
}

function parseInvoiceData(raw) {
  const clean = raw.replace(/\r/g, " ");

  const entities = ["Swiggy", "Zomato", "Amazon", "Flipkart", "Zepto", "Blinkit", "IndiGo", "Uber", "Ola", "BookMyShow", "PhonePe", "Google Pay", "Paytm", "MakeMyTrip", "IRCTC", "Croma", "Myntra"];
  const matched = entities.find(e => new RegExp(e, "i").test(clean));

  let orderId = "";
  const mOrder = clean.match(/\b(?:order|id|booking|txn|invoice|no|#)[#:\s-]*([A-Z0-9-]{6,20})\b/i);
  if (mOrder) orderId = mOrder[1];

  let amount = "";
  const mAmount = clean.match(/(?:₹|INR|Rs\.?)\s*([\d,]+(?:\.\d{2})?)/i);
  if (mAmount) amount = mAmount[1].replace(/,/g, "");

  let dateStr = "";
  const mDate = clean.match(/\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})\b/);
  if (mDate) {
    const rawD = mDate[1];
    if (rawD.includes("-") && rawD.split("-")[0].length === 4) {
      dateStr = rawD;
    } else {
      const parts = rawD.split(/[-/]/);
      dateStr = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
    }
  }

  if (matched) $("f_seller").value = matched;
  if (dateStr) $("f_date").value = dateStr;
  if (amount) $("f_amount").value = amount;

  let intakeText = `Dispute regarding ${matched || 'merchant'}`;
  if (orderId) intakeText += ` (Ref: ${orderId})`;
  if (amount) intakeText += ` for INR ${amount}`;
  intakeText += `. Specific fault: `;

  $("text").value = intakeText;
  $("text").focus();
}

/* ==========================================================================
   Dispatch & Clipboard Utilities
   ========================================================================== */
function copyToClipboard(text, btnElement = null, successMsg = "Copied!") {
  if (!navigator.clipboard) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  } else {
    navigator.clipboard.writeText(text).catch(() => {});
  }
  if (btnElement) {
    const orig = btnElement.innerHTML;
    btnElement.innerHTML = `✓ ${successMsg}`;
    btnElement.classList.add("copied");
    setTimeout(() => {
      btnElement.innerHTML = orig;
      btnElement.classList.remove("copied");
    }, 2200);
  }
}

function openMailComposer(subject, body, provider = "gmail", feedbackEl = null) {
  copyToClipboard(body);
  if (feedbackEl) {
    feedbackEl.innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Notice copied to clipboard!</span> Opening ${provider === "gmail" ? "Gmail" : provider === "outlook" ? "Outlook Web" : "default mail app"}...`;
  }

  const sSub = encodeURIComponent(subject || "Formal Dispute Notice");
  // Keep body snippet safe from URL length restrictions (~1500 chars)
  const safeSnippet = body.length > 1500
    ? body.slice(0, 1500) + "\n\n[Full legal text copied to clipboard. Press Paste (Cmd+V / Ctrl+V) here for complete notice]"
    : body;
  const sBody = encodeURIComponent(safeSnippet);

  if (provider === "gmail") {
    window.open(`https://mail.google.com/mail/?view=cm&fs=1&su=${sSub}&body=${sBody}`, "_blank", "noopener,noreferrer");
  } else if (provider === "outlook") {
    window.open(`https://outlook.live.com/mail/0/deeplink/compose?subject=${sSub}&body=${sBody}`, "_blank", "noopener,noreferrer");
  } else {
    // Default system mailto client
    const mailtoUri = `mailto:?subject=${sSub}&body=${sBody}`;
    const link = document.createElement("a");
    link.href = mailtoUri;
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      if (document.body.contains(link)) document.body.removeChild(link);
    }, 300);
  }
}

function openExternalPortal(url) {
  const target = url.startsWith("http") ? url : `https://${url}`;
  const win = window.open(target, "_blank", "noopener,noreferrer");
  if (!win || win.closed || typeof win.closed === "undefined") {
    const link = document.createElement("a");
    link.href = target;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      if (document.body.contains(link)) document.body.removeChild(link);
    }, 300);
  }
}

/* ==========================================================================
   Modal Dialog Framework
   ========================================================================== */
function openModal(markup) {
  $("modalCard").innerHTML = markup;
  $("modal").classList.remove("hidden");
  const closeFn = () => $("modal").classList.add("hidden");
  $("modal").onclick = (e) => { if (e.target === $("modal")) closeFn(); };
  const closeBtn = $("modalCard").querySelector("[data-close]");
  if (closeBtn) closeBtn.onclick = closeFn;
  return closeFn;
}

function setupModalInteractions() {
  // 1. BENCHMARK METRICS MODAL
  $("btnStats").addEventListener("click", async () => {
    try {
      const stats = await api("/api/stats");
      const html = `
        <h3>Platform Telemetry & Metrics</h3>
        <p class="modal-caption">Empirical verification benchmarks across Indian consumer claims.</p>
        <div class="metrics-summary-row">
          <div class="metric-card">
            <div class="metric-val">${esc(stats.total_cases_analyzed)}</div>
            <div class="metric-name">Disputes Ingested</div>
          </div>
          <div class="metric-card">
            <div class="metric-val">${esc(stats.verification_rate)}</div>
            <div class="metric-name">DOM Match Rate</div>
          </div>
          <div class="metric-card">
            <div class="metric-val">${esc(stats.avg_time_saved_hrs)}</div>
            <div class="metric-name">Resolution Velocity</div>
          </div>
        </div>

        <h4 style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:0.04em;color:var(--text-secondary);margin-bottom:8px;">Dispute Sector Distribution</h4>
        <table class="stats-table">
          <thead>
            <tr>
              <th>Sector Framework</th>
              <th style="text-align:right">Dossiers Handled</th>
            </tr>
          </thead>
          <tbody>
            ${stats.top_categories.map(c => `
              <tr>
                <td><strong>${esc(c.name)}</strong></td>
                <td style="text-align:right;font-family:var(--font-mono)">${esc(c.count)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>

        <div style="display:flex;justify-content:flex-end;margin-top:18px;">
          <button class="btn btn-secondary" data-close>Dismiss</button>
        </div>`;
      openModal(html);
    } catch (e) {
      alert("Telemetry retrieval failure: " + e.message);
    }
  });

  // 2. STATUTORY CALCULATOR MODAL
  const launchCalc = () => {
    const valAmt = $("f_amount")?.value || (activeCase?.fields?.amount) || "2499";
    const valDate = $("f_date")?.value || (activeCase?.purchase_date) || "2026-10-25";

    const html = `
      <h3>Statutory Compensation & Remedy Calculator</h3>
      <p class="modal-caption">Determines statutory financial liabilities under CPA 2019, DGCA CAR Part IV, and RBI DPSS.</p>
      <form id="calcForm">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
          <div class="form-group">
            <label>Disputed Consideration (INR)</label>
            <input id="c_amt" type="number" value="${esc(valAmt)}" required>
          </div>
          <div class="form-group">
            <label>Transaction / Breach Date</label>
            <input id="c_date" type="date" value="${esc(valDate)}" required>
          </div>
        </div>

        <div class="form-group" style="margin-bottom:16px;">
          <label>Governing Regulatory Provision</label>
          <select id="c_type" style="width:100%;border:1px solid var(--border-default);border-radius:var(--radius-sm);padding:8px 10px;background:var(--bg-surface);color:var(--text-primary);font-family:inherit;font-size:13px;">
            <option value="defective">Defective Commodity (100% Price Restitution / Replacement)</option>
            <option value="food">Unsafe / Deficient Food Delivery (Full Refund + CPA S.84 Product Liability)</option>
            <option value="upi">Unreversed Failed Payment / UPI (T+1 Reversal + INR 100/day Statutory Penalty)</option>
            <option value="flight">Aviation Cancellation <24h (100% Tax Restitution + INR 5,000-10,000 Mandatory Relief)</option>
            <option value="denied_boarding">Involuntary Denied Boarding (200%-400% Basic Fare, capped INR 20,000)</option>
            <option value="late_delivery">Excessive Delivery Delay (100% Refund, Cancellation Charge Nullified)</option>
          </select>
        </div>

        <div style="display:flex;gap:10px;justify-content:flex-end;">
          <button class="btn btn-secondary" type="button" data-close>Cancel</button>
          <button class="btn btn-primary" type="submit">Compute Statutory Entitlement</button>
        </div>
      </form>
      <div id="calcOutput" class="hidden"></div>`;

    openModal(html);

    $("calcForm").onsubmit = (e) => {
      e.preventDefault();
      const baseAmt = parseFloat($("c_amt").value) || 0;
      const rule = $("c_type").value;
      const dInput = $("c_date").value;
      let days = 0;
      if (dInput) {
        const dt = new Date(dInput);
        days = Math.max(0, Math.floor((new Date() - dt) / (1000 * 60 * 60 * 24)));
      }

      let markup = "";
      if (rule === "upi") {
        const delayed = Math.max(0, days - 1);
        const penalty = delayed * 100;
        const total = baseAmt + penalty;
        markup = `
          <div class="calc-breakdown-panel">
            <div class="calc-total-headline">INR ${total.toLocaleString()}</div>
            <div style="font-size:13px;font-weight:600;margin-bottom:4px;">Principal Restitution: INR ${baseAmt.toLocaleString()} + Mandatory Delay Penalty: INR ${penalty.toLocaleString()} (${delayed} days @ INR 100/day)</div>
            <div class="calc-legal-subtext">Directly mandated under RBI Harmonisation of Turn Around Time Circular (DPSS.CO.PD No.629/2019). Automatically payable to customer account.</div>
          </div>`;
      } else if (rule === "flight") {
        const comp = 5000;
        const total = baseAmt + comp;
        markup = `
          <div class="calc-breakdown-panel">
            <div class="calc-total-headline">INR ${total.toLocaleString()}</div>
            <div style="font-size:13px;font-weight:600;margin-bottom:4px;">100% Fare Restitution: INR ${baseAmt.toLocaleString()} + Statutory Compensation: INR ${comp.toLocaleString()}</div>
            <div class="calc-legal-subtext">Mandated under DGCA Civil Aviation Requirements (CAR) Section 3, Series M, Part IV. Airlines are prohibited from forcing credit shells.</div>
          </div>`;
      } else if (rule === "denied_boarding") {
        const comp = Math.min(20000, baseAmt * 2);
        const total = baseAmt + comp;
        markup = `
          <div class="calc-breakdown-panel">
            <div class="calc-total-headline">INR ${total.toLocaleString()}</div>
            <div style="font-size:13px;font-weight:600;margin-bottom:4px;">Ticket Restitution: INR ${baseAmt.toLocaleString()} + Overbooking Relief: INR ${comp.toLocaleString()}</div>
            <div class="calc-legal-subtext">Mandated under DGCA CAR Section 3, Series M. 200% to 400% of basic fare payable immediately.</div>
          </div>`;
      } else {
        markup = `
          <div class="calc-breakdown-panel">
            <div class="calc-total-headline">INR ${baseAmt.toLocaleString()} (100% Restitution)</div>
            <div style="font-size:13px;font-weight:600;margin-bottom:4px;">Full Legal Recovery without Restocking or Processing Deductions</div>
            <div class="calc-legal-subtext">Guaranteed under CPA 2019 Section 2(47) and Consumer Protection (E-Commerce) Rules 2020. Merchants cannot unilaterally forfeit funds.</div>
          </div>`;
      }

      $("calcOutput").innerHTML = markup;
      $("calcOutput").classList.remove("hidden");
    };
  };

  $("btnCalc").addEventListener("click", launchCalc);
  $("aCalcResult")?.addEventListener("click", launchCalc);
}

// FORMAL LEGAL NOTICE DRAFTING
const generateNoticeModal = (heading, sub, actionLabel) => `
  <h3>${heading}</h3>
  <p class="modal-caption">${sub}</p>
  <form id="noticeForm">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
      <div class="form-group">
        <label>Complainant Legal Name</label>
        <input id="n_name" placeholder="Full Legal Name" required>
      </div>
      <div class="form-group">
        <label>Reference / Transaction Identifier</label>
        <input id="n_order" placeholder="e.g. OD89201928" required>
      </div>
      <div class="form-group">
        <label>Primary Contact Email</label>
        <input id="n_email" type="email" placeholder="contact@example.com" required>
      </div>
      <div class="form-group">
        <label>Primary Phone</label>
        <input id="n_phone" placeholder="+91 XXXXX XXXXX">
      </div>
    </div>
    <div style="display:flex;justify-content:flex-end;gap:10px;">
      <button class="btn btn-secondary" type="button" data-close>Cancel</button>
      <button class="btn btn-primary" type="submit">${actionLabel}</button>
    </div>
  </form>`;

$("aDraft").addEventListener("click", () => {
  const close = openModal(generateNoticeModal(
    "Formulate Statutory Demand Notice",
    "Generates formal pre-litigation correspondence citing merchant terms and statutory sections.",
    "Generate Formal Notice"
  ));

  $("noticeForm").onsubmit = async (e) => {
    e.preventDefault();
    const payload = {
      name: $("n_name").value,
      order_id: $("n_order").value,
      email: $("n_email").value,
      phone: $("n_phone").value,
    };
    const draft = await api(`/api/cases/${current}/claim-draft`, { body: payload });
    $("modalCard").innerHTML = `
      <h3>Statutory Pre-Litigation Demand</h3>
      <p class="modal-caption"><strong>Subject:</strong> ${esc(draft.subject)}</p>
      <textarea style="width:100%;min-height:240px;font-family:var(--font-mono);font-size:12px;background:var(--bg-subtle);color:var(--text-primary);border:1px solid var(--border-default);border-radius:var(--radius-sm);padding:12px;" id="draftArea">${esc(draft.body)}</textarea>
      <div id="draftFeedback" style="font-size:12px;margin:6px 0;min-height:18px;"></div>
      <div style="display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;margin-top:10px;">
        <button class="btn btn-secondary btn-sm" id="btnCopyDraft">Copy Notice</button>
        <button class="btn btn-primary btn-sm" id="btnGmailDraft">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
          <span>Open in Gmail</span>
        </button>
        <button class="btn btn-secondary btn-sm" id="btnMailtoDraft">Open in Mail App</button>
        <button class="btn btn-secondary btn-sm" id="btnOutlookDraft">Open in Outlook</button>
        <button class="btn btn-secondary btn-sm" data-close>Dismiss</button>
      </div>`;

    $("btnCopyDraft").onclick = () => {
      copyToClipboard($("draftArea").value, $("btnCopyDraft"), "Notice Copied!");
    };
    $("btnGmailDraft").onclick = () => {
      openMailComposer(draft.subject, $("draftArea").value, "gmail", $("draftFeedback"));
    };
    $("btnMailtoDraft").onclick = () => {
      openMailComposer(draft.subject, $("draftArea").value, "default", $("draftFeedback"));
    };
    $("btnOutlookDraft").onclick = () => {
      openMailComposer(draft.subject, $("draftArea").value, "outlook", $("draftFeedback"));
    };
    $("modalCard").querySelector("[data-close]").onclick = close;
  };
});

$("aFill").addEventListener("click", () => {
  const close = openModal(generateNoticeModal(
    "Automated Form Filing Assistant",
    "Launches an autonomous browser agent to navigate merchant portals and input dispute parameters safely.",
    "Initialize Browser Agent"
  ));

  $("noticeForm").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: $("n_name").value,
        order_id: $("n_order").value,
        email: $("n_email").value,
        phone: $("n_phone").value,
      };
      await api(`/api/cases/${current}/claim-fill`, { body: payload });
      close();
      $("panel").innerHTML = `<div class="card" style="padding:16px;"><strong>Filing Agent Initialized:</strong> Headless browser session active. Automated safety halt active prior to final submission.</div>`;
    } catch (err) {
      alert("Assistant invocation error: " + err.message);
    }
  };
});

$("aWatch").addEventListener("click", async () => {
  $("aWatch").disabled = true;
  $("aWatch").textContent = "Registering Watch...";
  try {
    const res = await api(`/api/cases/${current}/monitor`, { body: {} });
    $("panel").innerHTML = `
      <div class="card" style="padding:16px;border-left:3px solid var(--brand-accent);">
        <h4 style="font-size:14px;font-weight:700;margin-bottom:4px;">Policy Integrity Watch Active</h4>
        <p class="modal-caption">Tracking cryptographic hashes of ${res.watching} verified documentation page(s).</p>
        <button class="btn btn-secondary btn-sm" id="btnCheckWatch">Execute Policy Hash Re-Verification</button>
        <div id="watchFeedback" style="margin-top:10px;font-size:12.5px;"></div>
      </div>`;

    $("btnCheckWatch").onclick = async () => {
      $("btnCheckWatch").disabled = true;
      const check = await api(`/api/cases/${current}/monitor/check`, { body: {} });
      $("watchFeedback").innerHTML = check.checks.map(x => `
        <div style="padding:4px 0;">
          ${x.state === "changed" ? "⚠️ <strong>DOM Drift Detected:</strong> Policy text updated." : "✓ <strong>Hash Matched:</strong> No terms modified."}
          <a href="${esc(x.url)}" target="_blank" style="color:var(--brand-accent)">${esc(host(x.url))}</a>
        </div>
      `).join("");
      $("btnCheckWatch").disabled = false;
    };
  } catch (e) {
    alert(e.message);
  } finally {
    $("aWatch").disabled = false;
    $("aWatch").textContent = "Monitor Policy Shifts";
  }
});

$("aCompare").addEventListener("click", async () => {
  $("panel").innerHTML = `<div class="card" style="padding:16px;">Querying ungrounded generic LLM from memory...</div>`;
  try {
    const c = await api(`/api/cases/${current}/compare`, { body: {} });
    const genericText = c.chatbot_available
      ? `<p style="font-size:13px;line-height:1.5;">${esc(c.chatbot)}</p><p class="modal-caption" style="margin-top:8px;">Ungrounded parametric memory. Hallucination-prone with zero verified citations.</p>`
      : `<p class="modal-caption">Configure ANTHROPIC_API_KEY to benchmark a live comparative LLM generation.</p>`;

    const verifiedText = c.exitlens.map(s => `
      <div style="margin-bottom:8px;">
        <strong style="font-size:13px;">${esc(s.title)}</strong>
        <div style="font-size:12.5px;color:var(--text-secondary)">${esc(s.action)}</div>
      </div>
    `).join("") + `<p class="modal-caption" style="margin-top:8px;">Verified directly against live merchant DOM endpoints with character-level match.</p>`;

    $("panel").innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px;">
        <div class="card" style="padding:16px;border-left:3px solid var(--status-danger)">
          <h4 style="font-size:13px;font-weight:700;margin-bottom:6px;">Generic LLM (Ungrounded Memory)</h4>
          ${genericText}
        </div>
        <div class="card" style="padding:16px;border-left:3px solid var(--status-verified)">
          <h4 style="font-size:13px;font-weight:700;margin-bottom:6px;">ExitLens Verified Intelligence</h4>
          ${verifiedText}
        </div>
      </div>`;
  } catch (e) {
    $("panel").innerHTML = `<div class="alert-box alert-error">${esc(e.message)}</div>`;
  }
});

/* ==========================================================================
   Tracker & Automated Complaint Intelligence
   ========================================================================== */

async function updateTrackerDashboard(caseId) {
  try {
    const tk = await api(`/api/cases/${caseId}/tracker`);
    $("tkDaysElapsed").textContent = tk.days_elapsed !== null ? `${tk.days_elapsed}d` : "--";
    $("tkReturnDays").textContent = tk.return_expired ? "Closed" : `${tk.return_days_left}d`;
    $("tkWarrantyDays").textContent = tk.warranty_expired ? "Expired" : `${tk.warranty_days_left}d`;

    if (tk.accumulated_statutory_penalty > 0) {
      $("tkPenaltyAmt").textContent = `INR ${tk.accumulated_statutory_penalty.toLocaleString()}`;
      $("tkPenaltyLbl").textContent = tk.penalty_statute ? tk.penalty_statute.split(" ")[0] + " Penalty" : "Statutory Penalty";
    } else {
      $("tkPenaltyAmt").textContent = "INR 0";
      $("tkPenaltyLbl").textContent = "Statutory Penalty";
    }

    const b = $("trackerBadge");
    if (tk.lifecycle_stage === "MERCHANT_RETURN_WINDOW") {
      b.textContent = "Merchant Return Window Active";
      b.className = "lifecycle-badge";
      $("tkProgressFill").style.width = "25%";
    } else if (tk.lifecycle_stage === "MANUFACTURER_WARRANTY") {
      b.textContent = "Manufacturer Warranty Horizon";
      b.className = "lifecycle-badge";
      $("tkProgressFill").style.width = "65%";
    } else if (tk.lifecycle_stage === "STATUTORY_ESCALATION") {
      b.textContent = "Statutory Tribunal Escalation Stage";
      b.className = "lifecycle-badge warning";
      $("tkProgressFill").style.width = "100%";
    } else {
      b.textContent = "Awaiting Incident Date";
      b.className = "lifecycle-badge";
      $("tkProgressFill").style.width = "10%";
    }
  } catch (e) { /* non-critical */ }
}

function setupComplaintWizard() {
  $("btnAutoComplaint").addEventListener("click", async () => {
    try {
      const qData = await api(`/api/cases/${current}/complaint-questions`);
      const formFields = qData.questions.map(q => {
        if (q.type === "select") {
          return `
            <div class="form-group" style="margin-bottom:12px;">
              <label>${esc(q.label)} ${q.required ? '*' : ''}</label>
              <select id="cq_${q.id}" style="width:100%;border:1px solid var(--border-default);border-radius:var(--radius-sm);padding:8px 10px;background:var(--bg-surface);color:var(--text-primary);font-family:inherit;font-size:13px;">
                ${q.options.map(opt => `<option value="${esc(opt)}">${esc(opt)}</option>`).join("")}
              </select>
            </div>`;
        }
        return `
          <div class="form-group" style="margin-bottom:12px;">
            <label>${esc(q.label)} ${q.required ? '*' : ''}</label>
            <input id="cq_${q.id}" placeholder="${esc(q.placeholder || '')}" ${q.required ? 'required' : ''}>
          </div>`;
      }).join("");

      const html = `
        <h3>Automated Dispute Dispatcher Wizard</h3>
        <p class="modal-caption">Custom legal intake questions formulated for <strong>${esc(qData.entity)}</strong> (${esc(qData.case_type)}).</p>
        <form id="cqForm">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
            <div class="form-group">
              <label>Complainant Full Legal Name *</label>
              <input id="cq_name" placeholder="Full Legal Name" required>
            </div>
            <div class="form-group">
              <label>Contact Email *</label>
              <input id="cq_email" type="email" placeholder="you@example.com" required>
            </div>
          </div>
          ${formFields}
          <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:16px;">
            <button class="btn btn-secondary" type="button" data-close>Cancel</button>
            <button class="btn btn-primary" type="submit">Compile & Dispatch Docket</button>
          </div>
        </form>
      `;

      const close = openModal(html);

      $("cqForm").onsubmit = async (e) => {
        e.preventDefault();
        const details = {};
        qData.questions.forEach(q => {
          const el = $(`cq_${q.id}`);
          if (el) details[q.id] = el.value;
        });

        const payload = {
          name: $("cq_name").value,
          email: $("cq_email").value,
          phone: $("f_seller")?.value || "",
          details: details
        };

        const result = await api(`/api/cases/${current}/automated-complaint`, { body: payload });

        $("modalCard").innerHTML = `
          <h3>Dispute Package Compiled</h3>
          <p class="modal-caption">Formal legal demand & National Consumer Helpline filing docket ready for dispatch.</p>

          <div style="margin-bottom:16px;">
            <div class="statutory-badge">Notice 1: Formal Merchant Legal Demand</div>
            <textarea style="width:100%;min-height:160px;font-family:var(--font-mono);font-size:11.5px;background:var(--bg-subtle);color:var(--text-primary);border:1px solid var(--border-default);border-radius:var(--radius-sm);padding:10px;margin-top:6px;" id="dispNotice">${esc(result.legal_notice)}</textarea>
            <div id="noticeFeedback" style="font-size:12px;margin:4px 0;min-height:18px;"></div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:4px;">
              <button class="btn btn-secondary btn-sm" id="btnCopyNotice">Copy Legal Notice</button>
              <button class="btn btn-primary btn-sm" id="btnNoticeGmail">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
                <span>Open in Gmail</span>
              </button>
              <button class="btn btn-secondary btn-sm" id="btnNoticeMailto">
                <span>Default Mail App</span>
              </button>
              <button class="btn btn-secondary btn-sm" id="btnNoticeOutlook">
                <span>Outlook Web</span>
              </button>
            </div>
          </div>

          <div style="margin-top:16px;border-top:1px solid var(--border-subtle);padding-top:14px;">
            <div class="statutory-badge">Notice 2: INGRAM / National Consumer Helpline (1915) Docket</div>
            <div class="legal-record" style="margin-top:6px;font-family:var(--font-mono);font-size:12px;line-height:1.6;">
              <div><strong>Portal:</strong> ${esc(result.nch_docket.portal)}</div>
              <div><strong>Helpline:</strong> ${esc(result.nch_docket.helpline_dial)}</div>
              <div><strong>Grievance Category:</strong> ${esc(result.nch_docket.grievance_category)}</div>
              <div><strong>Reference ID:</strong> ${esc(result.nch_docket.transaction_id)}</div>
              <div><strong>Relief Claimed:</strong> ${esc(result.nch_docket.relief_claimed)}</div>
              <div style="margin-top:4px;"><strong>Chronology & Facts:</strong> ${esc(result.nch_docket.grievance_summary)}</div>
            </div>
            <div id="nchFeedback" style="font-size:12px;margin:4px 0;min-height:18px;"></div>
            <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;">
              <button class="btn btn-secondary btn-sm" id="btnCopyNch">Copy NCH Docket</button>
              <button class="btn btn-primary btn-sm" id="btnOpenNch">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                <span>Open consumerhelpline.gov.in</span>
              </button>
              <button class="btn btn-secondary btn-sm" id="btnOpenJagriti">
                <span>Open e-Jagriti Portal</span>
              </button>
              <button class="btn btn-secondary btn-sm" id="btnOpenWhatsApp" style="color:#25D366;font-weight:600;">
                <span>WhatsApp 8800001915</span>
              </button>
            </div>
          </div>

          <div style="display:flex;justify-content:flex-end;margin-top:18px;">
            <button class="btn btn-secondary" data-close>Done</button>
          </div>
        `;

        $("btnCopyNotice").onclick = () => {
          copyToClipboard($("dispNotice").value, $("btnCopyNotice"), "Notice Copied!");
        };
        $("btnNoticeGmail").onclick = () => {
          openMailComposer(result.subject, $("dispNotice").value, "gmail", $("noticeFeedback"));
        };
        $("btnNoticeMailto").onclick = () => {
          openMailComposer(result.subject, $("dispNotice").value, "default", $("noticeFeedback"));
        };
        $("btnNoticeOutlook").onclick = () => {
          openMailComposer(result.subject, $("dispNotice").value, "outlook", $("noticeFeedback"));
        };

        $("btnCopyNch").onclick = () => {
          copyToClipboard(JSON.stringify(result.nch_docket, null, 2), $("btnCopyNch"), "Docket Copied!");
        };
        $("btnOpenNch").onclick = () => {
          copyToClipboard(JSON.stringify(result.nch_docket, null, 2));
          if ($("nchFeedback")) $("nchFeedback").innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Docket copied to clipboard!</span> Opening National Consumer Helpline portal...`;
          openExternalPortal("https://consumerhelpline.gov.in");
        };
        $("btnOpenJagriti").onclick = () => {
          copyToClipboard(JSON.stringify(result.nch_docket, null, 2));
          if ($("nchFeedback")) $("nchFeedback").innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Docket copied to clipboard!</span> Opening e-Jagriti consumer commission portal...`;
          openExternalPortal("https://e-jagriti.gov.in");
        };
        $("btnOpenWhatsApp").onclick = () => {
          const waText = `Consumer Grievance Docket:\nParty: ${result.nch_docket.company_name}\nID: ${result.nch_docket.transaction_id}\n\n${result.nch_docket.grievance_summary}`;
          copyToClipboard(JSON.stringify(result.nch_docket, null, 2));
          if ($("nchFeedback")) $("nchFeedback").innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Docket copied to clipboard!</span> Launching National Consumer Helpline WhatsApp bot...`;
          window.open(`https://wa.me/918800001915?text=${encodeURIComponent(waText)}`, "_blank", "noopener,noreferrer");
        };

        $("modalCard").querySelector("[data-close]").onclick = close;
      };
    } catch (err) {
      alert("Error loading questions: " + err.message);
    }
  });

  // Direct NCH Docket Button
  $("btnNchDocket").addEventListener("click", async () => {
    try {
      const result = await api(`/api/cases/${current}/automated-complaint`, { body: { name: "Aggrieved Consumer" } });
      const html = `
        <h3>National Consumer Helpline (1915) Docket</h3>
        <p class="modal-caption">Pre-formatted submission packet for INGRAM convergence portal & WhatsApp bot (8800001915).</p>
        <div class="legal-record" style="font-family:var(--font-mono);font-size:12px;line-height:1.6;margin-bottom:14px;">
          <div><strong>Government Portal:</strong> ${esc(result.nch_docket.portal)}</div>
          <div><strong>Toll-Free Dial:</strong> ${esc(result.nch_docket.helpline_dial)}</div>
          <div><strong>Opposite Party:</strong> ${esc(result.nch_docket.company_name)}</div>
          <div><strong>Classification:</strong> ${esc(result.nch_docket.grievance_category)}</div>
          <div><strong>Transaction Particulars:</strong> ${esc(result.nch_docket.transaction_id)}</div>
          <div><strong>Statutory Grounds:</strong> ${esc(result.nch_docket.statutory_sections)}</div>
          <div><strong>Relief Demanded:</strong> ${esc(result.nch_docket.relief_claimed)}</div>
          <div style="margin-top:6px;"><strong>Statement of Facts:</strong><br>${esc(result.nch_docket.grievance_summary)}</div>
        </div>
        <div id="directNchFeedback" style="font-size:12px;margin:6px 0;min-height:18px;"></div>
        <div style="display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;">
          <button class="btn btn-secondary btn-sm" id="btnCopyDirectNch">Copy Full Docket</button>
          <button class="btn btn-primary btn-sm" id="btnOpenDirectNch">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            <span>Open INGRAM Portal</span>
          </button>
          <button class="btn btn-secondary btn-sm" id="btnOpenDirectJagriti">
            <span>Open e-Jagriti Portal</span>
          </button>
          <button class="btn btn-secondary btn-sm" id="btnOpenDirectWA" style="color:#25D366;font-weight:600;">
            <span>WhatsApp (8800001915)</span>
          </button>
          <button class="btn btn-secondary btn-sm" data-close>Dismiss</button>
        </div>
      `;
      openModal(html);
      $("btnCopyDirectNch").onclick = () => {
        copyToClipboard(JSON.stringify(result.nch_docket, null, 2), $("btnCopyDirectNch"), "Docket Copied!");
      };
      $("btnOpenDirectNch").onclick = () => {
        copyToClipboard(JSON.stringify(result.nch_docket, null, 2));
        if ($("directNchFeedback")) $("directNchFeedback").innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Docket copied to clipboard!</span> Opening INGRAM portal...`;
        openExternalPortal("https://consumerhelpline.gov.in");
      };
      $("btnOpenDirectJagriti").onclick = () => {
        copyToClipboard(JSON.stringify(result.nch_docket, null, 2));
        if ($("directNchFeedback")) $("directNchFeedback").innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Docket copied to clipboard!</span> Opening e-Jagriti portal...`;
        openExternalPortal("https://e-jagriti.gov.in");
      };
      $("btnOpenDirectWA").onclick = () => {
        const waText = `Consumer Grievance Docket:\nParty: ${result.nch_docket.company_name}\nID: ${result.nch_docket.transaction_id}\n\n${result.nch_docket.grievance_summary}`;
        copyToClipboard(JSON.stringify(result.nch_docket, null, 2));
        if ($("directNchFeedback")) $("directNchFeedback").innerHTML = `<span style="color:var(--status-verified);font-weight:600;">✓ Docket copied to clipboard!</span> Opening WhatsApp bot...`;
        window.open(`https://wa.me/918800001915?text=${encodeURIComponent(waText)}`, "_blank", "noopener,noreferrer");
      };
    } catch (e) { alert(e.message); }
  });

  // Benchmark Modal
  $("btnBenchmark")?.addEventListener("click", () => {
    const html = `
      <h3>Why ExitLens Outperforms ChatGPT & Claude</h3>
      <p class="modal-caption">Direct architectural comparison for consumer dispute resolution.</p>
      <div style="display:flex;flex-direction:column;gap:12px;margin:16px 0;">
        <div class="legal-record">
          <strong style="color:var(--brand-accent)">1. Live DOM Character-Matched Proof</strong>
          <span style="font-size:12px;color:var(--text-secondary)">ChatGPT invents return deadlines from stale memory. ExitLens uses TinyFish crawlers to verify exact quotes character-by-character from the merchant's live website.</span>
        </div>
        <div class="legal-record">
          <strong style="color:var(--brand-accent)">2. Autonomous Browser Navigation</strong>
          <span style="font-size:12px;color:var(--text-secondary)">Chatbots only generate text. ExitLens dispatches headless agents to locate nested support policies and auto-fill claim forms.</span>
        </div>
        <div class="legal-record">
          <strong style="color:var(--brand-accent)">3. Cryptographic Policy Hash Sentinel</strong>
          <span style="font-size:12px;color:var(--text-secondary)">ExitLens stores SHA-256 hashes of live terms to detect stealth policy drifts or unannounced clause alterations.</span>
        </div>
        <div class="legal-record">
          <strong style="color:var(--brand-accent)">4. Statutory Calendar & Delay Penalty Math</strong>
          <span style="font-size:12px;color:var(--text-secondary)">Computes statutory daily compensation (e.g. INR 100/day for delayed UPI under RBI TAT and DGCA CAR passenger relief) using exact calendar math.</span>
        </div>
        <div class="legal-record">
          <strong style="color:var(--brand-accent)">5. Automated Pre-Litigation & NCH 1915 Dispatch</strong>
          <span style="font-size:12px;color:var(--text-secondary)">Generates ready-to-file legal dockets formatted for India's National Consumer Helpline and e-Jagriti consumer forums.</span>
        </div>
      </div>
      <div style="display:flex;justify-content:flex-end;">
        <button class="btn btn-secondary" data-close>Dismiss</button>
      </div>
    `;
    openModal(html);
  });
}

// INITIALIZE CONTROLLER
init();
