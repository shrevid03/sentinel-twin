/* Review queue: a human approves or rejects investigator proposals and held agent checkouts. Loaded after app.js. */
const ACTION_LABEL = { freeze: "Merchant-side restriction (simulated)", refund: "PayPal refund" };

async function loadReview() {
  const q = await api("/api/actions");
  const pendingA = q.actions.filter((a) => a.status === "pending");
  const pendingH = q.holds.filter((h) => h.status === "pending");
  const rows = [
    ...pendingH.map((h) => `<div class="case"><h4>${esc(h.id)} · Held agent checkout ${money(h.total)} <span class="tag">risk ${h.risk}</span></h4>
      <div class="muted">${esc(h.cart.map((c) => `${c.qty} × ${c.name}`).join(", "))}</div>
      <small class="muted">Why held: ${esc(h.factors.join("; ") || "risk above the review threshold")}</small>
      <div class="row" style="margin-top:6px"><button data-rv="hold" data-id="${esc(h.id)}" data-ok="1">Release (create PayPal order)</button>
        <button class="ghost" data-rv="hold" data-id="${esc(h.id)}" data-ok="0">Reject</button>
        <a href="#" class="rcpt-link" data-rcpt="${esc(h.receipt_id)}">Receipt</a></div></div>`),
    ...pendingA.map((a) => `<div class="case"><h4>${esc(a.id)} · ${esc(ACTION_LABEL[a.type] || a.type)}: ${esc(a.target)}</h4>
      <div>${esc(a.reason)} <span class="muted">· proposed by ${esc(a.proposed_by)}${a.case_id ? " in " + esc(a.case_id) : ""}</span></div>
      <ul>${a.evidence.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>
      <div class="row"><button data-rv="action" data-id="${esc(a.id)}" data-ok="1">Approve</button>
        <button class="ghost" data-rv="action" data-id="${esc(a.id)}" data-ok="0">Reject</button></div></div>`),
  ];
  $("#review-queue").innerHTML = rows.join("") || `<p class="muted">Nothing waiting for review.</p>`;
  $("#review-audit").innerHTML = q.audit.length ? `<table class="dtable"><tr><th>When</th><th>Item</th><th>Decision</th><th>Reviewer</th><th>Note</th></tr>
    ${q.audit.map((e) => `<tr><td>${esc(e.at)}</td><td>${esc(e.id)}</td><td>${esc(e.decision)}</td><td>${esc(e.reviewer)}</td><td>${esc(e.note)}</td></tr>`).join("")}</table>`
    : `<p class="muted">No decisions yet.</p>`;
}

document.addEventListener("click", async (e) => {
  const b = e.target.closest("[data-rv]");
  if (!b) return;
  const ok = b.dataset.ok === "1", kind = b.dataset.rv, id = b.dataset.id;
  const note = prompt(`${ok ? "Approve" : "Reject"} ${id}. Optional note for the audit trail:`, "") ?? null;
  if (note === null) return;
  const verb = kind === "hold" ? (ok ? "release" : "reject") : (ok ? "approve" : "reject");
  const path = kind === "hold" ? `/api/holds/${id}/${verb}` : `/api/actions/${id}/${verb}`;
  try {
    await api(path, { reviewer: $("#reviewer").value || "merchant", note });
  } catch (err) { alert(err.message); }
  loadReview(); refresh();
  if (typeof renderCases === "function") renderCases();
});

document.querySelectorAll('#tabs button[data-tab="investigator"]').forEach((b) => b.addEventListener("click", loadReview));
setInterval(() => document.querySelector("#tab-investigator.active") && loadReview(), 5000);

$("#btn-reset").onclick = async () => {
  if (!confirm("Reset the demo? This rebuilds the twin from its seed (about 10 seconds) and clears checkouts, holds, proposed actions, receipts and the policy.")) return;
  const b = $("#btn-reset");
  b.disabled = true; b.textContent = "Resetting…";
  try { await api("/api/reset", {}); location.reload(); }
  catch (e) { alert("Reset failed: " + e.message); b.disabled = false; b.textContent = "Reset demo"; }
};
