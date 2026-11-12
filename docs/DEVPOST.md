# Devpost submission text (copy each section into the form)

## Tagline
A live digital twin of your PayPal business, defended by a graph attention network and AI agents that shop, investigate and attack it, in 10 Indian languages.

## Inspiration
AI agents are starting to buy things for people. That gives small merchants two new problems: shopping agents can be hijacked by a poisoned listing, and fraud rings hide in networks of shared devices and IPs that per-order rules never see. Big marketplaces have fraud teams, graph analytics and red teams. A small seller in India has none of that, and may not want to work in English. We wanted to give them all three, in their own language.

## What it does
- **Digital twin**: every buyer, device, IP and merchant is a node in a live graph. PayPal checkouts and PayPal webhooks are mirrored into it, and it can be forked to rehearse attacks and policy changes safely.
- **Graph attention network**: scores every account from its neighbourhood and explains each score with attention weights. Every order is scored on the would-be graph before the PayPal order is created.
- **Concierge** (chat and voice in English, Hindi, Tamil, Telugu, Bengali, Marathi, Kannada, Gujarati, Malayalam, Punjabi) hands off to specialist agents.
- **Shopping agent**: reads the buyer's spending mandate, searches, and checks out with PayPal Orders v2. The buyer approves with the PayPal button. The mandate and risk gate are enforced in code, not by the model.
- **Investigator agent**: explains risk, maps linked accounts, looks up PayPal orders, refunds through PayPal, freezes accounts and files case reports. A PayPal dispute webhook opens an investigation automatically.
- **Adaptive red team agent**: attacks a fork of the twin with six playbooks (including prompt injection against the shopping agent), then changes tactics to evade whatever caught it, and reports what got through.
- **What-if simulator**: replays twin traffic plus the red team's attacks under a proposed policy before you apply it.

## How we built it
FastAPI backend and a no-build single-page front end. The GAT is our own NumPy implementation (2 layers, 4 attention heads, hand-derived backprop, gradient-checked in tests). The agents are Claude tool-use loops over real functions on the twin and the PayPal REST API (OAuth, Orders v2 create/get/capture, Payments v2 refunds, webhook signature verification) plus the PayPal JS SDK buttons. Voice uses the Web Speech API. Tables use AG Grid, deployment uses a Render blueprint, the API ships as a Postman collection and an OpenAPI spec for APIMatic, and events can stream to Elastic and Zapier.

## Challenges we ran into
Keeping guardrails out of the model: the prompt-injection attack proved the shopping agent can be talked into anything, so the mandate and risk gate moved into code. Making the red team genuinely adaptive meant running every attack on a deep copy of the twin so live state is never polluted. Writing GAT backprop by hand needed a finite-difference test to trust it.

## Accomplishments we're proud of
The red team found a real blind spot in our own model (low-and-slow synthetic identities), and the what-if simulator showed the fix before we applied it. The whole loop, from voice request in Hindi to a captured PayPal sandbox payment, is explained step by step in the agent trace.

## What we learned
Fraud is a graph problem, and attention weights make graph models explainable enough for a non-expert. Agent safety comes from what the tools allow, not from what the prompt says.

## What's next
Sparse attention for millions of nodes, mirroring PayPal Transaction Search history into the twin, Venmo and Braintree checkout, and letting the red team retrain the GAT on the attacks it invents.

## Built with
python, fastapi, numpy, graph-attention-network, claude, anthropic-api, paypal-orders-api, paypal-payments-api, paypal-webhooks, paypal-js-sdk, web-speech-api, ag-grid, render, postman, apimatic, elastic, zapier, vis-network, chart.js

## Testing instructions (fill in before submitting)
1. Live demo: <Render URL>
2. Or run locally: see README "Run it". Works with no keys in demo mode.
3. PayPal sandbox buyer login for the payment popup: <sandbox personal account email> / <password>
