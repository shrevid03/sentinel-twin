# Devpost submission text (copy each section into the form)

## Tagline
An AI shopping agent that pays with PayPal, a digital twin that checks every order, and a red team that keeps the defense honest.

## Inspiration
AI agents are starting to spend money for people. For a small merchant on PayPal that creates two new risks: a shopping agent can be talked into paying by a poisoned listing, and fraud rings hide in networks of shared devices and IPs that per-order rules never see. Big marketplaces answer this with fraud teams, graph analytics and red teams. We wanted one system that gives a small merchant all three, in their own language.

## What it does
Sentinel Twin detects a potential attack, explains the risk, tests its defenses against evolving threats, and stops unsafe transactions before money moves:

1. **An agent buys a real product and pays with PayPal.** The shopping agent (Gemini) reads the buyer's spending mandate and searches real products from 25,000+ retailers through **Channel3** (with a demo catalog fallback), then checks out with PayPal Orders v2. The buyer approves with the official PayPal button in the sandbox and the server captures it exactly once: a real **PayPal sandbox capture**, shown as COMPLETED in the Ledger and on the Command center.
2. **The twin checks every order first.** Every buyer, device, IP and merchant is a node in a live graph. A graph attention network scores the order on the would-be graph and explains why. Only an *approve* decision creates a PayPal order: *review* holds it for a human, *block* stops it. Every agent checkout leaves a **decision receipt**.
3. **A red team attacks a safe copy.** An adaptive red team agent runs six playbooks (fraud rings, card testing, account takeover, synthetic identities, device farms, prompt injection) on a fork of the twin, then changes tactics to evade whatever caught it.
4. **The what-if simulator measures the fix.** It replays recent traffic plus the red team's attacks under a proposed policy, and reports fraud intercepted (blocked or sent to review), fraud missed and good customers affected.
5. **The safer policy goes live before the next checkout.** This is policy hardening; the GAT itself is not retrained.
6. **A human approves anything consequential.** The investigator agent maps the ring with real graph evidence and files a case, but refunds and account restrictions are only proposals until the merchant approves them in a review queue with an audit trail.

Everything works by chat or voice in 10 Indian languages.

**A UI that tells the story.** A light, fintech-style redesign with original artwork: a command center with a defense-score gauge and decisions donut, and the twin drawn as a constellation in blue fog. The GAT's fraud rings show as labelled coral clusters you can click to explain, and the Defense drill shows an animated attack flow (arrows through the shield before hardening, deflected after) from the real drill result. All graphics are inline SVG, CSS and canvas, with no extra dependencies, and they respect reduced-motion settings.

## The result that matters: one click, the Defense drill
The Defense drill tab runs the whole loop in about 4 seconds on one frozen copy of the twin, with synthetic attack traffic. The red team attacks and explains each adaptation; the simulator searches 216 policies while pricing false positives ($4 per good order reviewed, plus the full value of any good order blocked, and never more than 8% of good customers reviewed); then the identical seeded attacks are replayed under the winner, and unseen attacks run under both policies.

One run on the live app (seed 7, 12 Nov 2026, synthetic twin data):
- Attack dollars that got through, same seeded attacks: **$2,629 before, $443 after**.
- **Unseen attacks** (fresh seeds, never tuned on): **$2,211 before, $434 after**, of $5,808 attempted.
- Intercept rate (blocked or sent to review) on replayed traffic plus attacks: **93.9% to 99.0%**. After the fix, $3,253 of the replayed attack fraud is blocked and $2,187 is sent to review.
- Good customers sent to review: **0 to 1 of 324**. Good orders blocked: $0 both times. False-positive cost: $0 to $4.
- What still gets through: synthetic-identity warm-up orders under $60. They look like normal shopping, and catching them would cost more good customers than they're worth. The drill reports this instead of hiding it.

## Why a graph? Rules only vs GAT, on identical orders
Unseen red-team attack traffic ($9,409 attempted), intercepted by:
- **Rules only** (new device, foreign IP, spend jump, velocity, account age): **42.5%**
- **GAT + rules**: **72% to 81%** across runs
- **GAT + rules, hardened policy**: **95.3%**

The graph wins on **fraud rings** (rules 0%, GAT 34% to 67%) and **device farms** (rules 15%, GAT 100%): new accounts that look clean alone but share devices or IPs. **Rules alone are slightly better on card testing** (98% vs 95%), and the graph adds nothing on account takeover or synthetic identities, where only the policy helps. On held-out synthetic accounts, a no-graph model matches the GAT's AUC (0.99), so we don't claim the graph is better at ranking known accounts; its value is per transaction.

## Safety guarantees, enforced in code and covered by tests
- The spending mandate and the risk gate run in code, not in the prompt. A prompt-injected agent that tries to buy $2,500 of gift cards is blocked.
- A *review* decision never creates a PayPal order; a reviewer releases or rejects the held checkout.
- Refunds and account restrictions proposed by the investigator need merchant approval. Approval runs exactly once, rejection changes nothing, and every decision is in an audit trail.
- Every agent checkout has a decision receipt: mandate checks, the risk split into graph and rules parts, reason codes, policy version, PayPal order and capture ids, and any reviewer decision.
- A capture happens at most once: repeated requests never charge again or double-count spend. The mandate is re-checked at capture time, and only agent-created orders can be captured.
- Only PayPal-verified webhooks can change state. Disputes open investigations; refunds update the twin.
- A public deploy can require an admin token for policy changes, retraining, reset and review decisions, and **Reset demo** gives every judge a clean start.

## Live vs simulated
- **Real:** PayPal sandbox orders, buyer approval, capture, refunds and webhook verification (with sandbox keys; labelled "Real PayPal sandbox"), and LLM agents (with a free Gemini key).
- **Simulated:** the fraud population and all red-team attack traffic (labelled "Synthetic attack traffic"), and the account restriction, which is merchant-side inside the twin, not a PayPal account freeze. Without keys, PayPal runs in a labelled demo mode and a scripted brain drives the agents.

## How we built it
FastAPI backend and a no-build single-page front end. The GAT is our own NumPy implementation (2 layers, 4 attention heads, hand-derived backprop, gradient-checked in tests). The agents are LLM tool-use loops (free Gemini or Groq, local Ollama, or Claude) over real functions on the twin and the PayPal REST API: OAuth, Orders v2 create/get/capture, Payments v2 refunds and webhook signature verification, plus the PayPal JS SDK buttons. With no keys, a labelled demo mode runs the same flows. Voice uses the Web Speech API, the ledgers use AG Grid, and the API ships as a Postman collection and an OpenAPI spec.

## Challenges we ran into
Keeping guardrails out of the model: the prompt-injection attack proved the shopping agent can be talked into anything, so the mandate, risk gate and capture checks all live in code. Running every attack on a deep copy of the twin so live state is never polluted. Writing GAT backprop by hand needed a finite-difference test before we could trust it.

## Accomplishments we're proud of
Our own red team found a real blind spot in our own model, and the simulator showed a measured fix, including its cost to good customers and its effect on attacks it never saw, before we applied it. We also measured where the graph helps and where it doesn't, and published both. The whole loop, from a voice request in Hindi to a captured PayPal sandbox payment, is visible step by step in the agent trace.

## What we learned
Fraud is a graph problem, and attention weights make a graph model explainable to a non-expert. Agent safety comes from what the tools allow, not from what the prompt says.

## Honest limitations
The twin's population is synthetic and seeded, because sandbox accounts don't produce realistic fraud, so the GAT's high test AUC is on synthetic data, and a no-graph model matches it there. Agent checkouts are scored for one demo buyer. The drill hardens the decision policy; it does not retrain the GAT. Real PayPal orders made through the app are mirrored into the twin.

## What's next
Catching warm-up orders from synthetic identities, sparse attention for millions of nodes, mirroring PayPal transaction history into the twin, and letting the red team retrain the GAT on the attacks it invents.

## Built with
python, fastapi, numpy, graph-attention-network, gemini, groq, ollama, claude, paypal-orders-api, paypal-payments-api, paypal-webhooks, paypal-js-sdk, web-speech-api, ag-grid, render, postman, apimatic, vis-network, chart.js, channel3, paypal-sandbox, svg, canvas

## Testing instructions (fill in before submitting)
1. Live demo: https://sentinel-twin.onrender.com (app at /app; free Render plan: if it has been idle, the first load takes about a minute while it wakes up).
2. Or run locally: see README "Run it". It works with no keys in demo mode.
3. PayPal sandbox buyer login for the payment popup: <sandbox personal account email> / <password>
4. Click **Reset demo** (top right) for a clean start.
5. To see the defining moment: open the Defense drill tab and click Run defense drill (about 4 seconds), read the scorecard and "Why a graph?", then Apply hardened policy to live.
6. Investigator tab: Investigate riskiest, then approve or reject the proposals in the Review queue. In the Concierge chat, click "Why? (decision receipt)" after a checkout.
