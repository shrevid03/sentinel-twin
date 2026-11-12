# Devpost submission text (copy each section into the form)

## Tagline
An AI shopping agent that pays with PayPal, a digital twin that checks every order, and a red team that keeps the defense honest.

## Inspiration
AI agents are starting to spend money for people. For a small merchant on PayPal that creates two new risks: a shopping agent can be talked into paying by a poisoned listing, and fraud rings hide in networks of shared devices and IPs that per-order rules never see. Big marketplaces answer this with fraud teams, graph analytics and red teams. We wanted one system that gives a small merchant all three, in their own language.

## What it does
Sentinel Twin detects a potential attack, explains the risk, tests its defenses against evolving threats, and stops unsafe transactions before money moves:

1. **An agent pays with PayPal.** The shopping agent reads the buyer's spending mandate, searches, and checks out with PayPal Orders v2. The buyer approves with the PayPal button and the server captures.
2. **The twin checks every order first.** Every buyer, device, IP and merchant is a node in a live graph. A graph attention network scores the order on the would-be graph and explains why. Only an *approve* decision creates a PayPal order: *review* and *block* never do.
3. **A red team attacks a safe copy.** An adaptive red team agent runs six playbooks (fraud rings, card testing, account takeover, synthetic identities, device farms, prompt injection) on a fork of the twin, then changes tactics to evade whatever caught it.
4. **The what-if simulator measures the fix.** It replays recent traffic plus the red team's attacks under a proposed policy, and reports fraud stopped, fraud missed and good customers affected.
5. **The safer policy goes live before the next checkout.** An investigator agent then maps the ring, freezes accounts, refunds through PayPal and files a case report.

Everything works by chat or voice in 10 Indian languages.

## The result that matters: one click, the Defense drill
The Defense drill tab runs the whole loop in about 4 seconds on one frozen copy of the twin. The red team attacks, the simulator searches 216 policies while pricing false positives ($4 per good order reviewed, plus the full value of any good order blocked, and never more than 8% of good customers reviewed), and then the identical seeded attacks are replayed under the winner.

One real run (seed 7, 12 Nov 2026, synthetic twin data):
- Attack dollars that got through, same seeded attacks: **$1,808 before, $443 after**.
- Catch rate on replayed traffic plus attacks: **95.9% to 99.0%**.
- Good customers sent to review: **0 to 1 of 324**. Good orders blocked: $0 both times. False-positive cost: $0 to $4.
- Held-out check on fresh seeds the policy was never tuned on: $434 of $5,808 got through.
- The quiet $250 account takeover, the fraud ring and both card-testing attacks went to $0.
- What still gets through: synthetic-identity warm-up orders under $60. They look like normal shopping, and catching them would cost more good customers than they're worth. The drill reports this instead of hiding it.

## Safety guarantees, enforced in code and covered by tests
- The spending mandate and the risk gate run in code, not in the prompt. A prompt-injected agent that tries to buy $2,500 of gift cards is blocked.
- A *review* decision never creates a PayPal order.
- A capture happens at most once: repeated requests never charge again or double-count spend. The mandate is re-checked at capture time, and only agent-created orders can be captured.
- Only PayPal-verified webhooks can change state. Disputes open investigations; refunds update the twin.

## How we built it
FastAPI backend and a no-build single-page front end. The GAT is our own NumPy implementation (2 layers, 4 attention heads, hand-derived backprop, gradient-checked in tests). The agents are LLM tool-use loops (free Gemini or Groq, local Ollama, or Claude) over real functions on the twin and the PayPal REST API: OAuth, Orders v2 create/get/capture, Payments v2 refunds and webhook signature verification, plus the PayPal JS SDK buttons. With no keys, a labelled demo mode runs the same flows. Voice uses the Web Speech API, the ledgers use AG Grid, and the API ships as a Postman collection and an OpenAPI spec.

## Challenges we ran into
Keeping guardrails out of the model: the prompt-injection attack proved the shopping agent can be talked into anything, so the mandate, risk gate and capture checks all live in code. Running every attack on a deep copy of the twin so live state is never polluted. Writing GAT backprop by hand needed a finite-difference test before we could trust it.

## Accomplishments we're proud of
Our own red team found a real blind spot in our own model, and the simulator showed a measured fix, including its cost to good customers, before we applied it. The whole loop, from a voice request in Hindi to a captured PayPal sandbox payment, is visible step by step in the agent trace.

## What we learned
Fraud is a graph problem, and attention weights make a graph model explainable to a non-expert. Agent safety comes from what the tools allow, not from what the prompt says.

## Honest limitations
The twin's population is synthetic and seeded, because sandbox accounts don't produce realistic fraud, so the GAT's high test AUC is on synthetic data. Real PayPal orders made through the app are mirrored into the twin.

## What's next
Catching warm-up orders from synthetic identities, sparse attention for millions of nodes, mirroring PayPal transaction history into the twin, and letting the red team retrain the GAT on the attacks it invents.

## Built with
python, fastapi, numpy, graph-attention-network, gemini, groq, ollama, claude, paypal-orders-api, paypal-payments-api, paypal-webhooks, paypal-js-sdk, web-speech-api, ag-grid, render, postman, apimatic, vis-network, chart.js

## Testing instructions (fill in before submitting)
1. Live demo: <Render URL>
2. Or run locally: see README "Run it". It works with no keys in demo mode.
3. PayPal sandbox buyer login for the payment popup: <sandbox personal account email> / <password>
4. To see the defining moment: open the Defense drill tab and click Run defense drill (about 4 seconds), then Apply hardened policy to live.
