/* Decision receipts: why an agent checkout was created, held, blocked or rejected. Loaded after app.js. */
const OUTCOME = {
  paypal_order_created: ["PayPal order created", "pass"], held_for_review: ["Held for human review, no PayPal order", "fail"],
  blocked_by_risk_engine: ["Blocked by the risk engine, no PayPal order", "fail"],
  rejected_by_mandate_guard: ["Rejected by the mandate guard, no PayPal order", "fail"],
  released_by_reviewer: ["Released by a reviewer, PayPal order created", "pass"], rejected_by_reviewer: ["Rejected by a reviewer", "fail"],
};
const yes = (b) => (b ? '<span class="pass">pass</span>' : '<span class="fail">fail</span>');

async function openReceipt(id) {
  const r = await api("/api/receipts/" + encodeURIComponent(id));
  const [label, cls] = OUTCOME[r.outcome] || [r.outcome, ""];
  const m = r.mandate, k = r.risk, pp = r.paypal, rv = r.review;
  $("#modal-title").textContent = `Decision receipt ${r.id}`;
  $("#modal-body").innerHTML = `
    <p><b class="${cls}">${esc(label)}</b> · ${money(r.total)} · created ${esc(r.created_at)} · buyer ${esc(r.buyer)}</p>
    <div class="rc-sec"><h4>Cart</h4>${r.cart.map((c) => esc(`${c.qty} × ${c.name} ($${c.price}, ${c.category})`)).join("<br>")}</div>
    <div class="rc-sec"><h4>Spending mandate at decision time</h4>
      Per-order limit ${money(m.per_order_limit)} · monthly budget ${money(m.monthly_budget)} · spent ${money(m.spent)} · remaining ${money(m.remaining)} · blocked: ${esc(m.blocked_categories.join(", ") || "none")}
      <table class="dtable">${r.mandate_checks.map((c) => `<tr><td>${esc(c.check)}</td><td>${yes(c.pass)}</td><td class="muted">${esc(c.detail)}</td></tr>`).join("")}</table></div>
    ${k ? `<div class="rc-sec"><h4>Risk decision</h4>
      Risk <b>${k.score}</b> = GAT part ${k.gat_part} combined with rules part ${k.rules_part} · decision <b>${esc(k.decision)}</b>
      · policy version <code>${esc(k.policy_version.hash)}</code> (applied ${esc(k.policy_version.applied_at)})
      <div class="muted">Reason codes: ${esc(k.factors.join("; ") || "none, normal for this buyer")}</div></div>` : ""}
    ${pp ? `<div class="rc-sec"><h4>PayPal (${esc(pp.mode === "sandbox" ? "Real PayPal sandbox" : "Demo mode")})</h4>
      Order <code>${esc(pp.order_id)}</code> · status ${esc(pp.status)} · ${esc(pp.approval)} · capture ${esc(pp.capture_id || "not yet")}</div>` : ""}
    ${rv ? `<div class="rc-sec"><h4>Human review</h4>${esc(rv.hold_id)} · ${esc(rv.status)}${rv.reviewer ? ` by ${esc(rv.reviewer)}` : ""}${rv.note ? ` · "${esc(rv.note)}"` : ""}</div>` : ""}
    <div class="rc-sec"><h4>Timeline</h4>${r.timeline.map((t) => `<div><span class="muted">${esc(t.at)}</span> ${esc(t.event)}</div>`).join("")}</div>`;
  $("#modal").hidden = false;
}
document.addEventListener("click", (e) => {
  const a = e.target.closest(".rcpt-link");
  if (a) { e.preventDefault(); openReceipt(a.dataset.rcpt).catch((err) => addMsg("sys", "Receipt error: " + esc(err.message))); }
});
$("#modal-close").onclick = () => { $("#modal").hidden = true; };
$("#modal").onclick = (e) => { if (e.target.id === "modal") $("#modal").hidden = true; };
