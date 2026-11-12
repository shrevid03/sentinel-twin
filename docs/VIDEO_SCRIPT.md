# Demo video script (target 2:50, hard limit under 3:00)

**The one story:** an AI shopping agent pays with PayPal; the digital twin checks every order; the red team finds a weakness on a safe copy; the what-if simulator measures the fix; the next attack is stopped. Everything else is supporting detail.

Record at 1920x1080 in Chrome with PayPal sandbox keys and a free Gemini key in `.env` (header badges: **PayPal sandbox · live** and **gemini**). Use your own voice, no copyrighted music. Rehearse each click once.

**Before recording:** restart the server so the policy is the default (review at 0.5). In the Red team tab, set the **account_takeover** playbook to amount `250`, foreign `false`.

| Time | Screen | Say |
|---|---|---|
| 0:00 to 0:15 | Command center, graph settling | "AI agents are starting to spend money for us. Sentinel Twin makes sure an agent can't be tricked into paying, and that fraud rings are caught before money moves. Here's the whole loop, live, on PayPal." |
| 0:15 to 0:50 | Concierge, Hindi, mic: Diwali gift under $40. Show the trace, approve in the PayPal sandbox popup, show "capture COMPLETED" | "I ask in Hindi for a Diwali gift under 40 dollars. The shopping agent reads my spending mandate, searches, and the digital twin scores the order on its graph before any PayPal order exists. Low risk, so it creates a real PayPal sandbox order. I approve it in PayPal, and it's captured exactly once." |
| 0:50 to 1:10 | Command center: click a red node, show attention bars | "The twin mirrors every buyer, device and IP. My graph attention network, written from scratch, explains each score: this account is risky because of a device shared by five flagged accounts." |
| 1:10 to 1:35 | Red team: Launch adaptive campaign. Point at the scorecard and report | "Now I attack my own system. The red team works on a fork of the twin, so no live data or money is touched. It tries six playbooks, including a prompt injection telling my agent to buy 2,500 dollars of gift cards, which the in-code mandate blocks. Then it adapts and finds a real gap: a quiet 250-dollar account takeover and low-and-slow synthetic identities get through." |
| 1:35 to 2:05 | **The defining moment.** Fire account_takeover ($250): result *evaded*. What-if: run the hardened policy, read the KPIs. Apply. Fire account_takeover again: result *caught (review)* | "Here's that takeover against today's policy: approved, 250 dollars lost. The what-if simulator replays 458 orders plus the attacks under a hardened policy: fraud missed drops from about 2,500 dollars to under 1,000, catch rate 94 to 98 percent, and zero good customers blocked or sent to review. I apply it and fire the same attack again: stopped before any payment starts." |
| 2:05 to 2:30 | Investigator: Investigate riskiest, show the case report; Ledger: PayPal API calls grid | "The investigator agent takes the riskiest account, maps its ring, freezes it and files a case report. It can refund through PayPal Payments v2, and only signature-verified PayPal webhooks can change anything." |
| 2:30 to 2:50 | Back to Command center | "Sentinel Twin: an agent that pays with PayPal, a twin that checks every order, and a red team that keeps the defense honest, so small merchants can trust agentic commerce. Open source, with 9 automated tests including the payment-safety guarantees." |

**Numbers to say:** read them off your own screen on the day. The ones above come from a real run on 12 Nov 2026 and vary slightly from run to run. Don't round in your favour.

Upload to YouTube as **Public** and paste the link into Devpost.
