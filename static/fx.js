/* Visual effects layer: hero particle network, KPI count-up, per-tab smoke hue, graph ripple. Loaded last. */
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* per-tab smoke hue */
  const _showTab = showTab;
  showTab = (t) => { document.body.dataset.tab = t; _showTab(t); };
  document.body.dataset.tab = "command";

  /* hero particle network: ~60 drifting dots joined by faint lines; paused when hidden or off-screen */
  const cv = document.getElementById("hero-net");
  if (cv) {
    const ctx = cv.getContext("2d");
    let W = 0, H = 0, pts = [], running = false, visible = true, raf = 0;
    const N = 60, LINK = 130;
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2), r = cv.getBoundingClientRect();
      if (!r.width || !r.height) return;
      W = r.width; H = r.height; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!pts.length) pts = Array.from({ length: N }, (_, i) => ({ x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35, r: 1.4 + Math.random() * 2.2, c: i % 3 ? "0,112,224" : "0,156,222" }));
    };
    const draw = () => {
      ctx.clearRect(0, 0, W, H);
      for (let i = 0; i < N; i++) {
        const a = pts[i];
        for (let j = i + 1; j < N; j++) {
          const b = pts[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
          if (d2 < LINK * LINK) {
            ctx.strokeStyle = `rgba(0,112,224,${(0.22 * (1 - Math.sqrt(d2) / LINK)).toFixed(3)})`;
            ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      for (const p of pts) { ctx.fillStyle = `rgba(${p.c},.75)`; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill(); }
    };
    const step = () => {
      for (const p of pts) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < -10) p.x = W + 10; else if (p.x > W + 10) p.x = -10;
        if (p.y < -10) p.y = H + 10; else if (p.y > H + 10) p.y = -10;
      }
      draw(); raf = requestAnimationFrame(step);
    };
    const sync = () => {
      if (!W && cv.getBoundingClientRect().width) resize();
      const want = !reduce && visible && !document.hidden && document.querySelector("#tab-command.active");
      if (want && !running) { running = true; raf = requestAnimationFrame(step); }
      else if (!want && running) { running = false; cancelAnimationFrame(raf); }
    };
    resize(); draw();
    new ResizeObserver(() => { if (cv.getBoundingClientRect().width) { resize(); draw(); } }).observe(cv);
    document.addEventListener("visibilitychange", sync);
    new IntersectionObserver((e) => { visible = e[0].isIntersecting; sync(); }).observe(cv);
    const _st = showTab; showTab = (t) => { _st(t); sync(); };
    sync();
  }

  /* KPI count-up on first load */
  const countUp = (root) => {
    if (reduce) return;
    root.querySelectorAll(".kpi b").forEach((b) => {
      const txt = b.textContent, nums = [...txt.matchAll(/\d[\d,]*(\.\d+)?/g)];
      if (!nums.length) return;
      const t0 = performance.now(), dur = 1100;
      const tick = (now) => {
        const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        b.textContent = txt.replace(/\d[\d,]*(\.\d+)?/g, (m) => {
          const v = parseFloat(m.replace(/,/g, "")), dec = (m.split(".")[1] || "").length;
          const cur = v * e;
          return dec ? cur.toFixed(dec) : Math.round(cur).toLocaleString(undefined, { useGrouping: m.includes(",") });
        });
        if (k < 1 && b.isConnected) requestAnimationFrame(tick); else if (b.isConnected) b.textContent = txt;
      };
      requestAnimationFrame(tick);
    });
  };
  const kp = document.getElementById("kpis");
  if (kp) {
    const mo = new MutationObserver(() => { if (kp.querySelector(".kpi b")) { mo.disconnect(); countUp(kp); } });
    mo.observe(kp, { childList: true });
  }

  /* twin graph: ripple a pulse along the clicked node's edges */
  const hookGraph = () => {
    if (!window.network && typeof network === "undefined") return false;
    if (!network) return false;
    network.on("click", (p) => {
      const id = p.nodes[0]; if (!id || reduce) return;
      const ids = network.getConnectedEdges(id); if (!ids.length) return;
      const t0 = performance.now();
      const anim = (now) => {
        const k = Math.min(1, (now - t0) / 900), a = Math.sin(k * Math.PI);
        edgesDS.update(ids.map((eid) => ({ id: eid, width: (1 + 4 * a) * SIZE_K * 0.8, color: { color: `rgba(143,211,255,${(0.35 + 0.65 * a).toFixed(2)})` } })));
        if (k < 1) requestAnimationFrame(anim); else edgesDS.update(ids.map((eid) => { const e = edgesDS.get(eid); return { id: eid, width: (e.hot ? 1.6 : 1) * SIZE_K * 0.8, color: e.hot ? EDGE_RISK : EDGE_COLOR }; }));
      };
      requestAnimationFrame(anim);
    });
    return true;
  };
  const iv = setInterval(() => { try { if (hookGraph()) clearInterval(iv); } catch { /* graph not ready */ } }, 500);
})();

/* ---------- command-center charts: decisions donut, defense gauge, KPI sparklines (real data only) ---------- */
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let donut = null;
  const hist = [];  // stats snapshots since this page opened
  const spark = (vals, color) => {
    if (vals.length < 2) return "";
    const lo = Math.min(...vals), hi = Math.max(...vals), w = 64, h = 20, span = hi - lo || 1;
    const pts = vals.map((v, i) => `${(i / (vals.length - 1) * w).toFixed(1)},${(h - 2 - (v - lo) / span * (h - 4)).toFixed(1)}`).join(" ");
    return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  };
  window.onStats = (s) => {
    hist.push({ live: s.live_orders, approved: s.approved, blocked_usd: s.blocked_usd, rate: s.live_orders ? s.approved / s.live_orders : 0 });
    if (hist.length > 30) hist.shift();
    // per-poll deltas = orders per interval; approval rate and blocked $ as running series
    const per = hist.slice(1).map((h, i) => Math.max(0, h.live - hist[i].live));
    const tiles = document.querySelectorAll("#kpis .kpi");
    const add = (idx, svg) => { const t = tiles[idx]; if (t && svg && !t.querySelector(".spark")) t.insertAdjacentHTML("beforeend", svg); };
    add(2, spark(per, "#0070E0")); add(3, spark(hist.map((h) => h.rate), "#1E8E3E")); add(5, spark(hist.map((h) => h.blocked_usd), "#D93025"));
    const data = [s.approved, s.review, s.blocked], n = s.live_orders;
    document.getElementById("donut-n").textContent = n.toLocaleString();
    const lg = document.getElementById("donut-legend");
    if (lg) lg.innerHTML = [["Approved", "#0070E0", s.approved], ["Sent to review", "#009CDE", s.review], ["Blocked", "#003087", s.blocked]]
      .map(([l, c, v]) => `<span><i style="background:${c}"></i>${l} <b>${v}</b> · ${n ? Math.round(v / n * 100) : 0}%</span>`).join("");
    if (!window.Chart) return;
    if (donut) { donut.data.datasets[0].data = data; donut.update(); return; }
    donut = new Chart(document.getElementById("decision-donut"), { type: "doughnut",
      data: { labels: ["Approved", "Sent to review", "Blocked"], datasets: [{ data, backgroundColor: ["#0070E0", "#009CDE", "#003087"], borderColor: "#fff", borderWidth: 3, hoverOffset: 6 }] },
      options: { cutout: "72%", maintainAspectRatio: false, plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (c) => ` ${c.label}: ${c.raw} (${n ? Math.round(c.raw / n * 100) : 0}%)` } } } } });
  };
  window.renderGauge = (d) => {
    const el = document.getElementById("gauge"); if (!el) return;
    if (!d) { el.innerHTML = `<div class="gauge-empty"><p class="muted">No drill yet. Run one to score how much attack traffic the hardened policy intercepts.</p><button id="gauge-run">Run defense drill</button></div>`;
      document.getElementById("gauge-run").onclick = () => { showTab("drill"); runDrill(); }; return; }
    const s = d.summary || {}, v = d.chosen ? s.catch_rate_after : s.catch_rate_before, before = s.catch_rate_before;
    const pctv = Math.max(0, Math.min(1, v || 0)), ang = -90 + 180 * pctv;
    el.innerHTML = `<svg class="gaugesvg" viewBox="0 0 220 130" role="img" aria-label="Defense score ${(pctv * 100).toFixed(1)} percent">
      <defs><linearGradient id="gg" x1="0" x2="1"><stop offset="0" stop-color="#D93025"/><stop offset=".55" stop-color="#009CDE"/><stop offset="1" stop-color="#1E8E3E"/></linearGradient></defs>
      <path d="M20 115 A90 90 0 0 1 200 115" fill="none" stroke="#E3E8EF" stroke-width="16" stroke-linecap="round"/>
      <path d="M20 115 A90 90 0 0 1 200 115" fill="none" stroke="url(#gg)" stroke-width="16" stroke-linecap="round" pathLength="100" stroke-dasharray="${(pctv * 100).toFixed(1)} 100"/>
      <g class="needle" style="transform:rotate(${reduce ? ang : -90}deg)"><line x1="110" y1="115" x2="110" y2="40" stroke="#003087" stroke-width="3.5" stroke-linecap="round"/><circle cx="110" cy="115" r="7" fill="#003087"/></g>
      </svg><div class="gauge-val"><b>${(pctv * 100).toFixed(1)}%</b><span>of attack $ intercepted${d.chosen && before != null ? ` · was ${(before * 100).toFixed(1)}%` : ""}</span></div>`;
    if (!reduce) requestAnimationFrame(() => requestAnimationFrame(() => { const n = el.querySelector(".needle"); if (n) n.style.transform = `rotate(${ang}deg)`; }));
  };
})();
