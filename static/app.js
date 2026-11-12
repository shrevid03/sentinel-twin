/* Sentinel Twin front end: plain JS, no build step. */
const $ = (s) => document.querySelector(s);
const adminToken = () => { try { return sessionStorage.getItem("adminToken") || ""; } catch { return ""; } };
const api = async (path, body, retried) => {
  const headers = { "Content-Type": "application/json" };
  if (adminToken()) headers["X-Admin-Token"] = adminToken();
  const r = await fetch(path, body === undefined ? { headers } : { method: "POST", headers, body: JSON.stringify(body) });
  if (r.status === 401 && !retried) {  // public deploy: admin actions need the token
    const t = prompt("This action needs the admin token:");
    if (t) { try { sessionStorage.setItem("adminToken", t); } catch {} return api(path, body, true); }
  }
  if (!r.ok) throw new Error((await r.text()).slice(0, 300));
  return r.json();
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const money = (n) => "$" + Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
const md = (t) => DOMPurify.sanitize(marked.parse(t || ""));
/* Chart.js defaults: light theme, blue/navy series, legends on */
if (window.Chart) {
  Chart.defaults.font.family = '"Plus Jakarta Sans", Inter, system-ui, sans-serif';
  Chart.defaults.color = "#5B6B82"; Chart.defaults.borderColor = "#E3E8EF";
  Chart.defaults.plugins.legend.display = true;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.elements.bar.borderRadius = 6;
  Chart.defaults.elements.line.borderWidth = 2.5; Chart.defaults.elements.point.radius = 0;
}
let CFG = {};
const session = "s-" + Math.random().toString(36).slice(2, 9);

/* ---------------- tabs ---------------- */
document.querySelectorAll("#tabs button").forEach((b) => b.onclick = () => showTab(b.dataset.tab));
function showTab(t) {
  document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("active", x.dataset.tab === t));
  document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("active", x.id === "tab-" + t));
  ({ investigator: loadAccounts, ledger: loadLedger, model: loadModel, whatif: () => initPolicy().then(runWhatIf), redteam: loadRuns })[t]?.();
  if (t === "command" && network) setTimeout(() => network.fit(), 50);
}

/* ---------------- KPIs ---------------- */
function kpi(label, value, cls = "") { return `<div class="kpi ${cls}"><b>${value}</b><span>${label}</span></div>`; }
async function loadStats() {
  const s = await api("/api/stats");
  $("#kpis").innerHTML = [
    kpi("accounts mirrored", s.accounts), kpi("devices · IPs", `${s.devices} · ${s.ips}`),
    kpi("live orders", s.live_orders), kpi("approved", s.approved, "ok"), kpi("sent to review", s.review, "warn"),
    kpi("blocked", `${s.blocked} · ${money(s.blocked_usd)}`, "bad"), kpi("high-risk accounts", s.high_risk_accounts, "bad"),
    kpi("frozen by investigator", s.frozen), kpi("GAT test AUC", s.model.test_auc ?? "–", "ok"),
  ].join("");
}

/* ---------------- graph ---------------- */
let network, nodesDS, edgesDS;
const colorFor = (n) => {
  if (n.status === "frozen") return { background: "#666", border: "#fff" };
  const r = n.risk || 0;
  const base = n.type === "account" ? [61, 155, 255] : n.type === "device" ? [155, 140, 255] : [63, 208, 201];
  const hot = [255, 93, 108];
  const mix = base.map((c, i) => Math.round(c + (hot[i] - c) * Math.min(1, r * 1.1)));
  return { background: `rgb(${mix})`, border: r > 0.5 ? "#D93025" : "#1d2a4a" };
};
async function loadGraph(focus) {
  const g = await api("/api/graph" + (focus ? `?focus=${focus}` : ""));
  const nodes = g.nodes.map((n) => ({
    id: n.id, label: n.type === "account" ? n.label : "", title: `${n.id} · ${n.type} · risk ${n.risk}`,
    shape: n.type === "account" ? "dot" : n.type === "device" ? "square" : "triangle",
    size: n.type === "account" ? 9 + 12 * n.risk : 6, color: colorFor(n), font: { color: "#001435", size: 10 }, raw: n,
  }));
  if (!network) {
    nodesDS = new vis.DataSet(nodes); edgesDS = new vis.DataSet(g.edges.map((e, i) => ({ id: i, ...e, color: { color: "#2a3658" } })));
    network = new vis.Network($("#graph"), { nodes: nodesDS, edges: edgesDS }, {
      physics: { solver: "forceAtlas2Based", forceAtlas2Based: { gravitationalConstant: -32, springLength: 40 }, stabilization: { iterations: 160 } },
      interaction: { hover: true, tooltipDelay: 80 }, edges: { width: 0.6, smooth: false },
    });
    network.on("click", (p) => p.nodes[0] && explain(p.nodes[0]));
  } else {
    nodesDS.clear(); edgesDS.clear(); nodesDS.add(nodes); edgesDS.add(g.edges.map((e, i) => ({ id: i, ...e, color: { color: "#2a3658" } })));
  }
}
async function explain(id) {
  const e = await api("/api/explain/" + id);
  const max = Math.max(...e.top_neighbors.map((n) => n.attention), 0.01);
  $("#explain-card").innerHTML = `<div class="cardhead"><h3>${esc(id)} · GAT risk <span style="color:${e.risk > 0.5 ? "var(--bad)" : "var(--ok)"}">${e.risk.toFixed(2)}</span></h3>
    <div>${id.startsWith("A-") ? `<button class="ghost" onclick="loadGraph('${id}')">Focus</button> <button onclick="investigate('${id}')">Investigate</button>` : ""}</div></div>
    <p class="muted">Attention weights: how much each neighbour shaped this score (avg of 4 heads + output head).</p>
    ${e.top_neighbors.map((n) => `<div class="att"><span>${esc(n.node)} <small class="muted">${n.type}</small></span>
      <div class="track"><div class="bar ${n.risk > 0.5 ? "hot" : ""}" style="width:${(100 * n.attention / max).toFixed(0)}%"></div></div>
      <span>${n.attention.toFixed(2)}</span></div>`).join("")}
    <p class="muted" style="margin-top:8px">${e.top_neighbors.filter((n) => n.risk > 0.5).length} high-risk neighbours · self-attention ${e.self_attention.toFixed(2)}</p>`;
}
$("#btn-burst").onclick = async () => { await api("/api/simulate", { n: 25, fraud_rate: 0.25 }); refresh(); loadGraph(); };
$("#btn-reset-graph").onclick = () => loadGraph();

/* ---------------- feed ---------------- */
let lastSeq = 0;
async function loadFeed() {
  const evs = await api("/api/events?since=" + lastSeq);
  if (!evs.length) return;
  lastSeq = evs[evs.length - 1].seq;
  const ul = $("#feed");
  evs.forEach((e) => ul.insertAdjacentHTML("afterbegin", `<li class="${e.level}"><small class="muted">t+${e.ts}m · ${e.kind}</small><br>${esc(e.text)}</li>`));
  while (ul.children.length > 120) ul.lastChild.remove();
}
$("#auto").onchange = (e) => api("/api/simulate", { auto: e.target.checked });

/* ---------------- trace rendering ---------------- */
function renderTrace(el, trace) {
  el.innerHTML = trace.map((t) => t.type === "thought"
    ? `<li><span class="tag ${t.agent.split(" ")[0]}">${esc(t.agent)}</span><i class="muted">${esc(t.text)}</i></li>`
    : `<li><span class="tag ${t.agent.split(" ")[0]}">${esc(t.agent)}</span><b>${esc(t.tool)}</b> <small class="muted">${t.ms}ms</small><br>
       <code>${esc(JSON.stringify(t.input)).slice(0, 160)}</code><br><code>→ ${esc(typeof t.output === "string" ? t.output : JSON.stringify(t.output)).slice(0, 260)}</code></li>`).join("");
}

/* ---------------- concierge ---------------- */
const SAMPLES = {
  "en-IN": ["Buy a gift for a coffee lover under $40", "How is the twin doing?", "Investigate the riskiest account", "Run the red team"],
  "hi-IN": ["मेरी माँ के लिए दिवाली का तोहफ़ा 40 डॉलर से कम में खरीदो", "ट्विन की स्थिति बताओ", "सबसे जोखिम वाले खाते की जांच करो"],
  "ta-IN": ["காபி பிரியருக்கு 40 டாலருக்குள் ஒரு பரிசு வாங்கு", "மிகவும் ஆபத்தான கணக்கை விசாரி"],
  "te-IN": ["40 డాలర్లలోపు కాఫీ ప్రియుడికి బహుమతి కొనండి", "అత్యంత ప్రమాదకరమైన ఖాతాను దర్యాప్తు చేయండి"],
  "bn-IN": ["৪০ ডলারের মধ্যে একটি উপহার কিনে দাও"], "mr-IN": ["४० डॉलरच्या आत भेटवस्तू घ्या"],
  "kn-IN": ["40 ಡಾಲರ್ ಒಳಗೆ ಉಡುಗೊರೆ ಖರೀದಿಸಿ"], "gu-IN": ["40 ડોલરની અંદર ભેટ ખરીદો"],
  "ml-IN": ["40 ഡോളറിനുള്ളിൽ ഒരു സമ്മാനം വാങ്ങൂ"], "pa-IN": ["40 ਡਾਲਰ ਤੋਂ ਘੱਟ ਵਿੱਚ ਤੋਹਫ਼ਾ ਖਰੀਦੋ"],
};
function setChips() {
  const l = $("#lang").value;
  $("#chips").innerHTML = (SAMPLES[l] || SAMPLES["en-IN"]).map((s) => `<button>${esc(s)}</button>`).join("");
  $("#chips").querySelectorAll("button").forEach((b) => b.onclick = () => sendChat(b.textContent));
}
function addMsg(cls, html) { $("#messages").insertAdjacentHTML("beforeend", `<div class="msg ${cls}">${html}</div>`); $("#messages").scrollTop = 1e9; }
async function sendChat(text) {
  text = (text || $("#msg").value).trim(); if (!text) return;
  $("#msg").value = ""; addMsg("user", esc(text)); addMsg("sys", "Sentinel is working…");
  try {
    const r = await api("/api/chat", { text, session, lang: $("#lang").value });
    $("#messages").lastChild.remove();
    addMsg("bot", esc(r.reply));
    renderTrace($("#trace"), r.trace);
    if (r.checkout) renderPay(r.checkout);
    if (r.receipt_id) addMsg("sys", `<a href="#" class="rcpt-link" data-rcpt="${esc(r.receipt_id)}">Why? (decision receipt ${esc(r.receipt_id)})</a>`);
    if (r.case) renderCases();
    if (r.redteam) renderRun(r.redteam, r.trace);
    speak(r.reply);
    refresh(); loadMandate();
  } catch (e) { $("#messages").lastChild.remove(); addMsg("sys", "Error: " + esc(e.message)); }
}
$("#send").onclick = () => sendChat();
$("#msg").onkeydown = (e) => e.key === "Enter" && sendChat();

/* PayPal checkout: the agent created the order server-side; the buyer approves it here. */
let ppLoaded = null;
function loadPayPalSdk() {
  if (ppLoaded) return ppLoaded;
  ppLoaded = new Promise((res, rej) => {
    const s = document.createElement("script");
    s.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(CFG.paypal_client_id)}&currency=USD&intent=capture&components=buttons`;
    s.onload = res; s.onerror = rej; document.head.appendChild(s);
  });
  return ppLoaded;
}
async function renderPay(co) {
  const slot = $("#paypal-slot");
  slot.innerHTML = `<div class="paybox"><b>Approve ${money(co.total)} with PayPal</b> <small class="muted">order ${esc(co.paypal_order_id)} · risk ${co.risk}</small>
    <div>${co.cart.map((c) => esc(`${c.qty} × ${c.name} ($${c.price})`)).join("<br>")}</div><div id="pp-buttons" style="margin-top:8px"></div></div>`;
  const done = (status) => { slot.innerHTML = `<div class="paybox">✅ PayPal capture <b>${esc(status)}</b> for ${esc(co.paypal_order_id)}</div>`; refresh(); loadMandate(); };
  if (CFG.paypal_mode === "sandbox" && CFG.paypal_client_id) {
    try {
      await loadPayPalSdk();
      paypal.Buttons({
        createOrder: () => co.paypal_order_id,
        onApprove: async (d) => { const r = await api(`/api/paypal/orders/${d.orderID}/capture`, {}); done(r.status); },
        onError: (e) => addMsg("sys", "PayPal error: " + esc(e)),
      }).render("#pp-buttons");
    } catch (e) { $("#pp-buttons").textContent = "Could not load the PayPal SDK."; }
  } else {
    $("#pp-buttons").innerHTML = `<button id="demo-approve">Approve payment (demo mode)</button> <small class="muted">Add PayPal sandbox keys for the real PayPal button.</small>`;
    $("#demo-approve").onclick = async () => { const r = await api(`/api/paypal/orders/${co.paypal_order_id}/capture`, {}); done(r.status); };
  }
}

/* voice: Web Speech API, works in Chrome / Edge for every Indian language listed */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = null;
$("#mic").onclick = () => {
  if (!SR) { addMsg("sys", "Voice input needs Chrome or Edge."); return; }
  if (rec) { rec.stop(); return; }
  rec = new SR(); rec.lang = $("#lang").value; rec.interimResults = true;
  $("#mic").classList.add("rec");
  rec.onresult = (e) => { $("#msg").value = Array.from(e.results).map((r) => r[0].transcript).join(""); };
  rec.onend = () => { $("#mic").classList.remove("rec"); rec = null; if ($("#msg").value.trim()) sendChat(); };
  rec.onerror = (e) => addMsg("sys", "Mic: " + esc(e.error));
  rec.start();
};
function speak(text) {
  if (!$("#speak").checked || !window.speechSynthesis) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.replace(/[*_#`]/g, "").slice(0, 600));
  const lang = $("#lang").value; u.lang = lang;
  const v = speechSynthesis.getVoices().find((v) => v.lang === lang) || speechSynthesis.getVoices().find((v) => v.lang.startsWith(lang.slice(0, 2)));
  if (v) u.voice = v;
  speechSynthesis.speak(u);
}

/* mandate */
async function loadMandate() {
  const m = await api("/api/mandate");
  $("#m-order").value = m.per_order_limit; $("#m-budget").value = m.monthly_budget; $("#m-blocked").value = m.blocked_categories.join(", ");
  $("#m-spent").textContent = `Spent ${money(m.spent)} of ${money(m.monthly_budget)}`;
}
$("#m-save").onclick = async () => {
  await api("/api/mandate", { per_order_limit: +$("#m-order").value, monthly_budget: +$("#m-budget").value,
    blocked_categories: $("#m-blocked").value.split(",").map((s) => s.trim()).filter(Boolean) });
  loadMandate();
};

/* ---------------- investigator ---------------- */
let accGrid;
async function loadAccounts() {
  const rows = (await api("/api/accounts")).sort((a, b) => b.risk - a.risk);
  if (!accGrid) {
    accGrid = agGrid.createGrid($("#acc-grid"), {
      rowData: rows, pagination: true, paginationPageSize: 50,
      columnDefs: [
        { field: "id", width: 90, pinned: "left" }, { field: "name" },
        { field: "risk", width: 110, sort: "desc", valueFormatter: (p) => p.value.toFixed(2), cellStyle: (p) => ({ color: p.value > 0.5 ? "#D93025" : "#1E8E3E", fontWeight: 600 }) },
        { field: "status", width: 95 }, { field: "age_days", headerName: "Age (d)", width: 95 }, { field: "country", width: 90 },
        { field: "email_domain", headerName: "Email" }, { field: "devices", width: 90 }, { field: "ips", width: 75 },
        { field: "orders", width: 85 }, { field: "spend", valueFormatter: (p) => money(p.value), width: 100 },
        { headerName: "", width: 120, cellRenderer: (p) => `<button class="ghost" onclick="investigate('${p.data.id}')">Investigate</button>` },
      ],
      defaultColDef: { sortable: true, filter: true, resizable: true },
    });
  } else accGrid.setGridOption("rowData", rows);
  renderCases();
}
async function investigate(id) {
  showTab("investigator");
  $("#inv-trace").innerHTML = `<li class="muted">Investigator agent is working on ${esc(id || "the riskiest account")}…</li>`;
  const r = await api("/api/investigate", { account: id || null, lang: $("#lang").value });
  renderTrace($("#inv-trace"), r.trace); renderCases(); loadAccounts(); refresh(); loadGraph(r.case.target);
}
window.investigate = investigate; window.loadGraph = loadGraph;
$("#btn-investigate-top").onclick = () => investigate(null);
async function renderCases() {
  const cs = await api("/api/cases");
  $("#cases").innerHTML = cs.length ? cs.map((c) => `<div class="case"><h4>${esc(c.id)} · ${esc(c.title)} <span class="verdict ${esc(c.verdict)}">${esc(c.verdict || "open")}</span></h4>
    <div>${esc(c.summary || "")}</div>
    ${c.evidence ? `<ul>${c.evidence.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>` : ""}
    ${c.actions?.length ? `<small class="muted">Actions: ${esc(c.actions.join("; "))}</small><br>` : ""}
    ${c.recommended_actions ? `<small class="muted">Recommended: ${esc(c.recommended_actions.join("; "))}</small>` : ""}
    ${c.narrative && c.brain !== "demo" ? `<details><summary class="muted">Investigator narrative</summary>${md(c.narrative)}</details>` : ""}</div>`).join("")
    : `<p class="muted">No cases yet. Click Investigate on any account.</p>`;
}

/* ---------------- red team ---------------- */
let rtGrid;
function renderAttacks() {
  $("#attacks").innerHTML = Object.entries(CFG.attacks).map(([k, a]) => `<div class="attack" data-k="${k}"><b>${k.replace(/_/g, " ")}</b><p>${esc(a.description)}</p>
    <div class="params">${Object.keys(a.params).map((p) => `<label>${p} <input data-p="${p}" placeholder="auto"></label>`).join("")}</div>
    <button class="ghost">Fire</button></div>`).join("");
  $("#attacks").querySelectorAll(".attack").forEach((el) => el.querySelector("button").onclick = async (ev) => {
    const params = {}; el.querySelectorAll("input").forEach((i) => i.value && (params[i.dataset.p] = isNaN(+i.value) ? i.value : +i.value));
    ev.target.disabled = true;
    const r = await api("/api/redteam/attack", { attack: el.dataset.k, params });
    ev.target.disabled = false;
    addResults([r.result]);
    if (r.trace?.length) renderTrace($("#rt-trace"), r.trace);
  });
}
function addResults(results, replace) {
  const rows = results.map((r) => ({ attack: r.attack, params: JSON.stringify(r.params || {}), fraud: r.fraud_usd, stopped: r.stopped_usd,
    evaded: r.evaded_usd, detection: r.detection_rate, decided_by: r.decided_by || "", notes: r.why_adapted ? "Why adapted: " + r.why_adapted : (r.notes || "") }));
  if (!rtGrid) {
    rtGrid = agGrid.createGrid($("#rt-grid"), { rowData: rows, columnDefs: [
      { field: "attack" }, { field: "params", flex: 1 }, { field: "fraud", valueFormatter: (p) => money(p.value), width: 100 },
      { field: "stopped", headerName: "Intercepted", headerTooltip: "blocked or sent to review", valueFormatter: (p) => money(p.value), width: 110 },
      { field: "evaded", valueFormatter: (p) => money(p.value), width: 100, cellStyle: (p) => ({ color: p.value > 0 ? "#D93025" : "#1E8E3E" }) },
      { field: "detection", headerName: "Intercept %", width: 110, valueFormatter: (p) => Math.round(p.value * 100) + "%" }, { field: "decided_by", headerName: "Decided by", width: 150 }, { field: "notes", headerName: "Why / notes", flex: 1, tooltipField: "notes" }],
      defaultColDef: { resizable: true, sortable: true } });
  } else if (replace) rtGrid.setGridOption("rowData", rows);
  else rtGrid.applyTransaction({ add: rows, addIndex: 0 });
}
function renderRun(run, trace) {
  const s = run.scorecard;
  $("#rt-score").innerHTML = [kpi("attacks launched", s.attacks_run), kpi("fraud attempted", money(s.fraud_attempted_usd)),
    kpi("intercepted (blocked or review)", money(s.stopped_usd), "ok"), kpi("got through", money(s.evaded_usd), "bad"),
    kpi("resilience", Math.round(s.resilience * 100) + "%", s.resilience > 0.9 ? "ok" : "warn"),
    kpi("weakest spot", (s.weakest[0]?.attack || "–").replace(/_/g, " "), "bad")].join("");
  $("#rt-report").classList.remove("muted"); $("#rt-report").innerHTML = md(run.report);
  addResults(run.results, true);
  if (trace) renderTrace($("#rt-trace"), trace.filter((t) => t.agent !== "concierge"));
}
$("#btn-campaign").onclick = async (e) => {
  e.target.disabled = true; $("#rt-trace").innerHTML = `<li class="muted">Red team agent is attacking a fork of the twin…</li>`;
  try { const r = await api("/api/redteam", { lang: $("#lang").value }); renderRun(r.run, r.trace); }
  finally { e.target.disabled = false; }
};
async function loadRuns() { const rs = await api("/api/redteam/runs"); if (rs[0] && !rtGrid) renderRun(rs[0]); }
$("#btn-to-whatif").onclick = async () => { showTab("whatif"); await initPolicy(); setPolicy({ review_threshold: 0.35, block_threshold: 0.75, max_auto_amount: 600, review_new_device_over: 150, review_spend_multiple: 3.5 }); runWhatIf(); };

/* ---------------- what-if ---------------- */
const POLICY_FIELDS = [
  ["review_threshold", "Review at risk ≥", 0, 1, 0.01], ["block_threshold", "Block at risk ≥", 0, 1, 0.01],
  ["max_auto_amount", "Auto-approve up to $", 50, 3000, 10], ["review_new_device_over", "Review new device over $", 0, 2000, 10],
  ["review_spend_multiple", "Review at N× usual spend (0 off)", 0, 10, 0.5]];
let policyInit = null, wiChart;
function initPolicy() { return policyInit ||= _initPolicy(); }
async function _initPolicy() {
  const s = await api("/api/stats");
  $("#policy-form").innerHTML = POLICY_FIELDS.map(([k, l, lo, hi, st]) => `<label>${l}<input type="range" id="p-${k}" min="${lo}" max="${hi}" step="${st}"><b id="v-${k}"></b></label>`).join("");
  POLICY_FIELDS.forEach(([k]) => $("#p-" + k).oninput = () => $("#v-" + k).textContent = $("#p-" + k).value);
  setPolicy(s.policy);
}
function setPolicy(p) { POLICY_FIELDS.forEach(([k]) => { if (p[k] !== undefined && $("#p-" + k)) { $("#p-" + k).value = p[k]; $("#v-" + k).textContent = p[k]; } }); }
const getPolicy = () => Object.fromEntries(POLICY_FIELDS.map(([k]) => [k, +$("#p-" + k).value]));
async function runWhatIf() {
  await initPolicy();
  const r = await api("/api/whatif?include_redteam=" + $("#wi-rt").checked, getPolicy());
  const keys = [["fraud_blocked_usd", "Fraud blocked $"], ["fraud_reviewed_usd", "Fraud sent to review $"], ["fraud_missed_usd", "Fraud missed $"], ["good_blocked_usd", "Good orders blocked $"]];
  const data = { labels: keys.map((k) => k[1]), datasets: [
    { label: "Current policy", data: keys.map((k) => r.current[k[0]]), backgroundColor: "#003087" },
    { label: "Proposed policy", data: keys.map((k) => r.proposed[k[0]]), backgroundColor: "#009CDE" }] };
  if (wiChart) { wiChart.data = data; wiChart.update(); } else wiChart = new Chart($("#wi-chart"), { type: "bar", data,
    options: { plugins: { legend: { labels: { color: "#001435" } } }, scales: { x: { ticks: { color: "#5B6B82" } }, y: { ticks: { color: "#5B6B82" }, grid: { color: "#E3E8EF" } } } } });
  $("#wi-kpis").innerHTML = [kpi("intercept rate now", Math.round(r.current.catch_rate * 100) + "%"), kpi("intercept rate proposed", Math.round(r.proposed.catch_rate * 100) + "%", "ok"),
    kpi("good orders to review", `${r.current.good_reviewed} → ${r.proposed.good_reviewed}`, "warn"), kpi("orders replayed", r.orders_replayed)].join("");
  $("#wi-note").textContent = `Replayed ${r.orders_replayed} orders, including ${r.attack_orders} red-team attack orders.`;
}
$("#btn-whatif").onclick = runWhatIf;
$("#btn-apply").onclick = async () => { await api("/api/policy", getPolicy()); $("#wi-note").textContent = "Applied to the live twin. Every new order now uses this policy."; refresh(); };

/* ---------------- ledger ---------------- */
let ordGrid, coGrid, apiGrid;
async function loadLedger() {
  const [orders, cos, calls] = await Promise.all([api("/api/orders"), api("/api/checkouts"), api("/api/paypal/calls")]);
  const dec = (p) => ({ color: p.value === "block" ? "#D93025" : p.value === "review" ? "#B06000" : "#1E8E3E", fontWeight: 600 });
  if (!ordGrid) ordGrid = agGrid.createGrid($("#ord-grid"), { rowData: orders, pagination: true, paginationPageSize: 100,
    columnDefs: [{ field: "id", width: 120, pinned: "left" }, { field: "buyer" }, { field: "account", width: 90 }, { field: "merchant_name", headerName: "Merchant" },
      { field: "amount", width: 100, valueFormatter: (p) => "$" + p.value.toFixed(2) }, { field: "decision", width: 105, cellStyle: dec },
      { field: "risk", width: 85 }, { field: "status", width: 120 }, { field: "source", width: 105 }, { field: "ip_country", headerName: "IP ctry", width: 90 },
      { field: "paypal_order_id", headerName: "PayPal order" }, { field: "factors", flex: 1, minWidth: 260 }],
    defaultColDef: { sortable: true, filter: true, resizable: true } });
  else ordGrid.setGridOption("rowData", orders);
  const coRows = cos.map((c) => ({ ...c, items: c.cart.map((x) => x.name).join(", "),
    data: String(c.paypal_order_id).startsWith("DEMO-") ? "Demo mode" : "Real PayPal sandbox" }));
  if (!coGrid) coGrid = agGrid.createGrid($("#co-grid"), { rowData: coRows, columnDefs: [{ field: "paypal_order_id" },
    { field: "receipt_id", headerName: "Receipt", width: 130, cellRenderer: (p) => p.value ? `<a href="#" class="rcpt-link" data-rcpt="${esc(p.value)}">${esc(p.value)}</a>` : "" },
    { field: "data", headerName: "Source", width: 150, cellStyle: (p) => ({ color: p.value === "Real PayPal sandbox" ? "#1E8E3E" : "#B06000", fontWeight: 600 }) }, { field: "total", width: 90 }, { field: "status", width: 120 }, { field: "risk", width: 80 }, { field: "items", flex: 1 }] });
  else coGrid.setGridOption("rowData", coRows);
  if (!apiGrid) apiGrid = agGrid.createGrid($("#api-grid"), { rowData: calls, columnDefs: [{ field: "t", width: 90 }, { field: "method", width: 85 }, { field: "path", flex: 1 }, { field: "status", width: 85 }, { field: "mode", width: 95 }] });
  else apiGrid.setGridOption("rowData", calls);
}
$("#ord-filter").oninput = (e) => ordGrid?.setGridOption("quickFilterText", e.target.value);

/* ---------------- model ---------------- */
let trainChart;
async function loadModel() {
  const m = await api("/api/model");
  $("#model-kpis").innerHTML = [kpi("test AUC", m.test_auc, "ok"), kpi("precision", m.precision), kpi("recall", m.recall),
    kpi("graph nodes", m.graph.nodes), kpi("edges", m.graph.edges), kpi("attention heads", `${m.heads} + 1`)].join("");
  const data = { labels: m.history.map((h) => h.epoch), datasets: [
    { label: "training loss", data: m.history.map((h) => h.loss), borderColor: "#003087", backgroundColor: "#003087", yAxisID: "y" },
    { label: "validation AUC", data: m.history.map((h) => h.val_auc), borderColor: "#009CDE", backgroundColor: "#009CDE", yAxisID: "y1" }] };
  if (trainChart) { trainChart.data = data; trainChart.update(); } else trainChart = new Chart($("#train-chart"), { type: "line", data,
    options: { plugins: { legend: { labels: { color: "#001435" } } }, scales: { x: { ticks: { color: "#5B6B82" } }, y: { ticks: { color: "#5B6B82" } }, y1: { position: "right", min: 0.4, max: 1, ticks: { color: "#5B6B82" } } } } });
}
$("#btn-retrain").onclick = async (e) => { e.target.disabled = true; await api("/api/model/retrain", {}); e.target.disabled = false; loadModel(); refresh(); };

/* ---------------- boot ---------------- */
function refresh() { loadStats(); loadFeed(); }
(async function boot() {
  CFG = await api("/api/config");
  $("#b-paypal").textContent = CFG.paypal_mode === "sandbox" ? "PayPal sandbox · live" : "PayPal · demo mode";
  $("#b-paypal").className = "badge " + (CFG.paypal_mode === "sandbox" ? "on" : "off");
  const BR = { claude: "Claude", gemini: "Gemini", groq: "Groq", ollama: "Ollama (local)" };
  $("#b-brain").textContent = CFG.brain === "demo" ? "AI · demo brain" : `${BR[CFG.brain] || CFG.brain} · ${CFG.model}`;
  $("#b-brain").className = "badge " + (CFG.brain === "demo" ? "off" : "on");
  $("#auto").checked = CFG.auto_traffic;
  $("#lang").innerHTML = Object.entries(CFG.languages).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
  $("#lang").onchange = setChips; setChips();
  addMsg("bot", "Namaste! I'm Sentinel. I can shop for you and pay with PayPal, explain the twin, investigate fraud, or unleash the red team. Pick a language and type or tap the mic.");
  renderAttacks(); loadMandate(); refresh(); loadGraph();
  setInterval(refresh, 4000);
  setInterval(() => document.querySelector("#tab-command.active") && loadGraph(), 30000);
})();
