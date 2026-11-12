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
        edgesDS.update(ids.map((eid) => ({ id: eid, width: 2 + 5 * a, color: { color: `rgba(143,211,255,${(0.35 + 0.65 * a).toFixed(2)})` } })));
        if (k < 1) requestAnimationFrame(anim); else edgesDS.update(ids.map((eid) => { const e = edgesDS.get(eid); return { id: eid, width: e.hot ? 2.6 : 2, color: e.hot ? EDGE_RISK : EDGE_COLOR }; }));
      };
      requestAnimationFrame(anim);
    });
    return true;
  };
  const iv = setInterval(() => { try { if (hookGraph()) clearInterval(iv); } catch { /* graph not ready */ } }, 500);
})();
