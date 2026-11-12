/* Defense drill tab: attack, search, replay, scorecard. Loaded after app.js (uses $, api, esc, money, kpi, refresh). */
let drillRes = null, drillChart = null;
const pct = (x) => (x == null ? "–" : (x * 100).toFixed(1) + "%");
const KNOB = { review_threshold: "review ≥ ", block_threshold: "block ≥ ", max_auto_amount: "auto-approve ≤ $",
  review_new_device_over: "new-device review > $", review_spend_multiple: "review at spend × " };
const changed = (p, base) => Object.keys(KNOB).filter((k) => p[k] !== base[k]).map((k) => KNOB[k] + p[k]).join(", ") || "no change";
const fmtParams = (p) => Object.entries(p || {}).filter(([k]) => k !== "victim").map(([k, v]) => `${k}=${v}`).join(", ");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function attackRows(rows, round) {
  return rows.map((r) => `<tr class="${r.evaded_usd > 0 ? "breach" : ""}"><td>${esc(r.attack)}</td><td class="muted">${round}</td>
    <td>${esc(fmtParams(r.params))}</td><td class="n">${money(r.fraud_usd)}</td><td class="n ev">${money(r.evaded_usd)}</td>
    <td class="n">${Math.round((r.detection_rate || 0) * 100)}%</td></tr>`).join("");
}

async function runDrill() {
  const btn = $("#btn-drill");
  btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span>Running drill…`;
  document.querySelectorAll(".drill-step").forEach((x) => x.classList.remove("show"));
  $("#drill-status").textContent = "";
  try {
    const d = drillRes = await api("/api/drill", { seed: 7 });
    const s = d.summary;

    $("#d-attacks").innerHTML = `<table class="dtable"><tr><th>Attack</th><th>Round</th><th>Params</th><th class="n">Attempted</th><th class="n">Got through</th><th class="n">Detected</th></tr>
      ${attackRows(d.probes, "probe")}${attackRows(d.adapted, "adapted")}</table>`;
    $("#ds-1").classList.add("show");
    await sleep(600);

    const searchLine = (d.log.find((l) => l.step === "search") || {}).text || "";
    $("#d-search").textContent = searchLine.charAt(0).toUpperCase() + searchLine.slice(1) +
      `. Score = fraud $ caught minus false-positive cost ($${d.review_cost_usd} per good order reviewed, plus the full value of good orders blocked).`;
    const base = d.before_policy;
    const rows = [{ policy: base, ...d.baseline, today: true }, ...d.top_candidates];
    $("#d-cands").innerHTML = `<table class="dtable"><tr><th>Policy (changed knobs)</th><th class="n">Catch rate</th><th class="n">Good orders reviewed</th><th class="n">FP cost</th><th class="n">Net benefit</th></tr>
      ${rows.map((c, i) => {
        const chosen = !c.today && i === 1 && d.chosen;
        return `<tr class="${chosen ? "chosen" : ""}"><td>${c.today ? "<b>Today's policy</b>" : esc(changed(c.policy, base))}${chosen ? ' <span class="tag">chosen</span>' : ""}</td>
        <td class="n">${pct(c.catch_rate)}</td><td class="n">${c.good_reviewed}</td><td class="n">${money(c.false_positive_cost_usd)}</td><td class="n">${money(c.net_benefit_usd)}</td></tr>`;
      }).join("")}</table>`;
    $("#ds-2").classList.add("show");
    await sleep(600);

    if (d.chosen) {
      $("#d-verify").innerHTML = `<table class="dtable"><tr><th>Attack (same seed)</th><th>Params</th><th class="n">Got through before</th><th class="n">After</th></tr>
        ${d.breaches.map((b, i) => {
          const v = d.verify[i] || {};
          return `<tr><td>${esc(b.attack)}</td><td>${esc(fmtParams(b.params))}</td><td class="n bad">${money(b.evaded_usd)}</td>
            <td class="n ${v.evaded_usd > 0 ? "bad" : "ok"}">${money(v.evaded_usd)}</td></tr>`;
        }).join("")}</table>`;
      $("#d-fresh").textContent = `Held-out check (fresh random seeds the policy was never tuned on): ${money(s.fresh_evaded_after_usd)} of ${money(s.fresh_attempted_usd)} got through.`;
    } else {
      $("#d-verify").innerHTML = `<p class="muted">No policy beat today's once false positives were priced in, so there is nothing to replay.</p>`;
      $("#d-fresh").textContent = "";
    }
    $("#ds-3").classList.add("show");
    await sleep(600);

    const arrow = (a, b) => `${a} → ${b ?? "–"}`;
    const after = (v, f) => (d.chosen ? f(v) : null);
    $("#d-kpis").innerHTML = [
      kpi(`Attack $ that got through<small>same seeded attacks</small>`, arrow(money(s.breach_evaded_before_usd), after(s.breach_evaded_after_usd, money)), "ok"),
      kpi(`Catch rate<small>replayed traffic plus attacks</small>`, arrow(pct(s.catch_rate_before), after(s.catch_rate_after, pct)), "ok"),
      kpi(`Good customers sent to review<small>of ${s.legit_orders} good orders · blocked ${money(s.legit_blocked_before_usd)} → ${money(s.legit_blocked_after_usd)}</small>`,
        arrow(s.legit_reviewed_before, s.legit_reviewed_after), "warn"),
      kpi(`False-positive cost<small>$${d.review_cost_usd} per review plus blocked value</small>`, arrow(money(s.fp_cost_before_usd), after(s.fp_cost_after_usd, money)), "warn"),
    ].join("");
    $("#ds-4").classList.add("show");  // show before drawing so Chart.js can measure the canvas
    const data = { labels: ["Attack $ that got through", "False-positive cost $"], datasets: [
      { label: "Before", data: [s.breach_evaded_before_usd, s.fp_cost_before_usd], backgroundColor: "#ff5d6c" },
      { label: "After", data: [s.breach_evaded_after_usd ?? 0, s.fp_cost_after_usd ?? 0], backgroundColor: "#2ecc8f" }] };
    if (drillChart) { drillChart.data = data; drillChart.update(); } else {
      drillChart = new Chart($("#d-chart"), { type: "bar", data, options: {
        plugins: { legend: { labels: { color: "#cdd6ee" } } },
        scales: { x: { ticks: { color: "#93a0bd" } }, y: { ticks: { color: "#93a0bd" }, grid: { color: "#24304f" } } } } });
    }
    drillChart.resize();
    await sleep(600);
    renderCompare(d.compare);
    $("#drill-status").textContent = `Drill finished in ${d.seconds}s on a frozen copy of the twin (seed ${d.seed}). Nothing live has changed yet.`;
    $("#btn-drill-apply").disabled = !d.chosen;
  } catch (e) {
    $("#drill-status").textContent = "Drill failed: " + e.message;
  }
  btn.disabled = false;
  btn.textContent = "Run defense drill";
}

/* step 5: rules only vs GAT + rules vs GAT + rules hardened, on identical orders */
let cmpChart = null;
const ENGINE = { rules_only: "Rules only (no graph)", gat_rules: "GAT + rules", gat_rules_hardened: "GAT + rules, hardened policy" };
const ATTACK_LABEL = { "live fraud traffic": "Live fraud traffic (accounts the GAT trained on)", fraud_ring: "Fraud rings",
  device_farm_evasion: "Device farms", card_testing: "Card testing", account_takeover: "Account takeover", synthetic_identity: "Synthetic identity" };
function renderCompare(c) {
  if (!c) return;
  const names = Object.keys(c.engines);
  $("#d-engines").innerHTML = `<table class="dtable"><tr><th>Engine</th><th class="n">Unseen attacks intercepted</th><th class="n">All fraud intercepted</th>
    <th class="n">Fraud blocked / reviewed</th><th class="n">Good orders reviewed</th><th class="n">Good $ blocked</th><th class="n">FP cost</th></tr>
    ${names.map((n) => { const e = c.engines[n], u = c.unseen_attacks[n]; return `<tr class="${n === "gat_rules_hardened" ? "chosen" : ""}"><td>${ENGINE[n]}</td>
      <td class="n"><b>${pct(u.intercept_rate)}</b> <small class="muted">of ${money(u.total_usd)}</small></td><td class="n">${pct(e.intercept_rate)}</td>
      <td class="n">${money(e.fraud_blocked_usd)} / ${money(e.fraud_reviewed_usd)}</td><td class="n">${e.good_reviewed} of ${e.good_total}</td>
      <td class="n">${money(e.good_blocked_usd)}</td><td class="n">${money(e.false_positive_cost_usd)}</td></tr>`; }).join("")}</table>`;
  const kinds = Object.keys(c.by_attack).filter((k) => k !== "live fraud traffic");
  const colors = { rules_only: "#93a0bd", gat_rules: "#3d9bff", gat_rules_hardened: "#2ecc8f" };
  const data = { labels: kinds.map((k) => ATTACK_LABEL[k] || k), datasets: names.map((n) => ({ label: ENGINE[n],
    data: kinds.map((k) => Math.round((c.by_attack[k][n] || 0) * 100)), backgroundColor: colors[n] })) };
  const opts = { plugins: { legend: { labels: { color: "#cdd6ee" } } }, scales: { x: { ticks: { color: "#93a0bd" } },
    y: { max: 100, ticks: { color: "#93a0bd", callback: (v) => v + "%" }, grid: { color: "#24304f" } } } };
  $("#ds-5").classList.add("show");
  if (cmpChart) { cmpChart.data = data; cmpChart.update(); } else cmpChart = new Chart($("#d-cmp-chart"), { type: "bar", data, options: opts });
  cmpChart.resize();
  const winsFor = (a, b) => kinds.filter((k) => (c.by_attack[k][a] || 0) > (c.by_attack[k][b] || 0)).map((k) => ATTACK_LABEL[k] || k);
  const g = winsFor("gat_rules", "rules_only"), r = winsFor("rules_only", "gat_rules");
  $("#d-byattack").innerHTML = `<p>The graph wins on <b>${esc(g.join(", ") || "none")}</b>: fresh accounts tied together by shared devices and IPs.
    ${r.length ? `Rules alone do better on <b>${esc(r.join(", "))}</b>.` : ""} Where both are equal, the attack looks normal on the graph too, and only the policy layer helps.</p>
    ${c.by_attack["live fraud traffic"] ? `<p class="muted">"Live fraud traffic" (${money(c.by_attack["live fraud traffic"].total_usd)}) comes from accounts the GAT was trained on, so it is left out of the unseen-attack figure and the chart.</p>` : ""}`;
  const a = c.account_auc;
  $("#d-auc").textContent = a ? `Account-level held-out AUC on ${a.test_accounts} test accounts: same features with no graph ${a.features_only_no_graph}, GAT ${a.gat}. On this synthetic data, the graph's value shows up per transaction (new accounts joining a known ring), not in ranking already-known accounts.` : "";
}

$("#btn-drill").onclick = runDrill;
$("#btn-drill-apply").onclick = async () => {
  if (!drillRes?.after_policy) return;
  await api("/api/policy", drillRes.after_policy);
  $("#drill-status").textContent = "Hardened policy applied to the live twin: " + changed(drillRes.after_policy, drillRes.before_policy) + ".";
  $("#btn-drill-rollback").disabled = false;
  refresh();
};
$("#btn-drill-rollback").onclick = async () => {
  if (!drillRes) return;
  await api("/api/policy", drillRes.before_policy);
  $("#drill-status").textContent = "Rolled back to the previous live policy.";
  $("#btn-drill-rollback").disabled = true;
  refresh();
};
