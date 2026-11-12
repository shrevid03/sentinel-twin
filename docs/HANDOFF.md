# Sentinel Twin: handoff

State as of 12 Nov 2026, late evening IST (PayPal AI Hackathon). Repo: `shrevid03/sentinel-twin`, branch `main`.

## What it is

A digital twin of a merchant's PayPal business, defended by AI agents. An AI shopping agent buys real products and pays with PayPal (sandbox); every order is scored on a graph before any PayPal order exists; a red team attacks a safe copy; a one-click drill finds a safer policy and proves it on the same attacks; a human approves anything irreversible.

## Run it

```bash
cd ~/sentinel-twin
.venv/bin/uvicorn app.main:app --port 8000
```

- `http://localhost:8000/` is the landing page (`static/landing.html`); **Launch live demo** goes to the app.
- `http://localhost:8000/app` is the app (`static/index.html`). `/app#drill`, `/app#concierge`, `/app#investigator` and so on open a tab directly.
- Startup takes ~8 s while the GAT trains. Keys come from `.env` (never commit it). With no keys everything still runs: a scripted "demo brain" and PayPal demo mode, both labelled in the header.

## Architecture

| Path | What |
|---|---|
| `app/main.py` | FastAPI app and all routes |
| `app/twin.py` | The digital twin: accounts, devices, IPs, merchants, orders; risk scoring, policy, `fork()` for safe copies |
| `app/gat.py` | Graph attention network in NumPy with hand-written backprop (gradient-checked in tests) |
| `app/agents.py` | Shopping concierge, investigator and red team; LLM tool loops (Gemini / Groq / Claude) or the demo brain; mandate guard; decision receipts; review queue |
| `app/redteam.py` | Attack playbooks (fraud ring, card testing, ATO, synthetic identity, device farm, prompt injection) |
| `app/drill.py` | Defense drill: attack, search 216 policies, replay the same seeds, plus rules-vs-GAT comparison |
| `app/paypal.py` | PayPal Orders v2 (create, capture once), Payments v2 refunds, webhook signature verification; demo mode without keys |
| `app/channel3.py` | Channel3 live product search (cheapest in-stock USD offer, cached by `C3-` SKU, demo-catalog fallback) |
| `app/catalog.py` | Demo catalog and the poisoned listing used by the prompt-injection attack |
| `app/integrations.py` | Optional Elastic and Zapier event sinks |
| `static/` | `landing.html`; app shell `index.html` + `app.js`, `drill.js`, `receipts.js`, `review.js`, `fx.js` (visual effects), `style.css`; `img/` (product shots and the author's photos); `vendor/` (vis-network, AG Grid, Chart.js, marked, DOMPurify) |

### Key endpoints

- Config and state: `GET /api/config` (brain, PayPal mode, `integrations.channel3`), `/api/stats`, `/api/graph`, `/api/events`, `/healthz`
- Shopping: `POST /api/chat` (returns `products` for Channel3 cards, plus `checkout` and `receipt_id`), `GET/POST /api/mandate`, `POST /api/paypal/orders/{id}/capture`, `GET /api/checkouts`, `/api/receipts`, `/api/receipts/{id}`, `POST /api/paypal/webhook`
- Defense: `POST /api/drill` (`apply: true` needs admin), `GET /api/drill/latest` (feeds the hero strip and gauge), `GET/POST /api/compare` (rules vs GAT), `POST /api/redteam`, `/api/redteam/attack`, `POST /api/whatif`, `POST /api/policy`
- Human in the loop: `POST /api/investigate`, `GET /api/actions`, `POST /api/actions/{id}/approve|reject`, `POST /api/holds/{id}/release|reject`
- `POST /api/reset` rebuilds the demo from `TWIN_SEED` (admin).

### Safety rules (tests cover them)

- Only an **approve** risk decision creates a PayPal order; review holds it for a human, block stops it.
- The spending mandate (per-order limit, monthly budget, blocked categories such as `gift_cards`) is enforced in code, never by the model. A Channel3 gift card is blocked the same way.
- Capture happens once; a repeat capture doesn't double-charge or double-count spend.
- The investigator only *proposes* refunds and restrictions; a reviewer approves them. "Restrict" is merchant-side and simulated, not a PayPal account freeze.
- `ADMIN_TOKEN`: when set, admin actions (apply policy, reset, approve actions) need the `X-Admin-Token` header; the UI prompts for it.
- Red-team prompt-injection probes always use the poisoned demo catalog, never Channel3.

## Results to quote (read your own screen on the day)

- Rules vs graph, same orders: **rules only 42.5%** of attack traffic intercepted, **GAT + rules about 72–81%** (80.8% on the reference run, varies with training), **GAT + hardened policy 95.3%**.
- A drill on 12 Nov: attack $ that got through **$1,808 → $443**; intercept rate **93.9% → 98.5%**.
- GAT test AUC is ~0.99 on this synthetic data.

## Tests

`.venv/bin/python -m pytest -q`: **22 passing** (safety, admin token, drill, GAT gradients, LLM loop, Channel3 with a mocked API, routes `/` and `/app`). Tests blank every key, so they never call PayPal, Gemini or Channel3.

## Gotchas

- **In-memory state.** Checkouts, receipts, the latest drill, cases and the review queue are cleared on every restart. Before recording: start once, run a drill, do one sandbox payment, then don't restart.
- **PayPal sandbox buyer.** Approve in the PayPal popup with a **US personal sandbox buyer** account, ideally in an **Incognito** window. Don't use the business (merchant) sandbox login, or your real PayPal login.
- **Browser cache.** App assets use `?v=N` in `index.html`; bump it when changing JS or CSS.
- **Free Render plan** sleeps after ~15 minutes idle and takes ~1 minute to wake: open the link yourself before judges do.
- Free Gemini keys have rate limits; the demo brain takes over if no key is set.

## Deploy (Render)

`render.yaml` is a Blueprint: free plan, Singapore region, `pip install -r requirements.txt`, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/healthz`, `GAT_EPOCHS=80` for a faster cold start.

1. render.com → **New → Blueprint** → pick `shrevid03/sentinel-twin` → Apply.
2. Enter secrets (names only here, values from your own `.env`): `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `GEMINI_API_KEY`, `CHANNEL3_API_KEY`, `ADMIN_TOKEN` (any password you choose). Optional: `PAYPAL_WEBHOOK_ID`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `ELASTIC_URL`, `ELASTIC_API_KEY`, `ZAPIER_WEBHOOK_URL`.
3. Every push to `main` redeploys automatically.

Public URL: **`https://<your-service>.onrender.com`** (fill in once live)

## Remaining to do

- [ ] Record the demo video (script: `docs/VIDEO_SCRIPT.md`, with the closing line), under 3:00
- [ ] Upload to YouTube as Public
- [ ] Deploy on Render and paste the URL above, in the README and in Devpost
- [ ] Submit on Devpost (text: `docs/DEVPOST.md`; add the video link, Render link, repo link and cover image)
