# Demo video script (target 2:50, hard limit under 3:00)

**The one story:** an AI shopping agent pays with PayPal; the digital twin checks every order; the red team finds a weakness on a safe copy; the simulator picks a safer policy and prices its cost to good customers; the same attack is stopped. Everything else is supporting detail.

Record at 1920x1080 in Chrome with PayPal sandbox keys and a free Gemini key in `.env` (header badges: **PayPal sandbox · live** and **gemini**). Use your own voice, no copyrighted music. Rehearse each click once.

**Before recording:** restart the server so the policy is the default, then let live traffic run for a minute. Run the drill once off camera so you know your numbers, then click *Roll back*.

| Time | Screen | Say |
|---|---|---|
| 0:00 to 0:15 | Command center, graph settling | "AI agents are starting to spend money for us. Sentinel Twin makes sure an agent can't be tricked into paying, and that fraud is caught before money moves. Here's the whole loop, live, on PayPal." |
| 0:15 to 0:50 | Concierge, Hindi, mic: Diwali gift under $40. Show the trace, approve in the PayPal sandbox popup, show "capture COMPLETED" | "I ask in Hindi for a Diwali gift under 40 dollars. The shopping agent reads my spending mandate, searches, and the digital twin scores the order on its graph before any PayPal order exists. Low risk, so it creates a real PayPal sandbox order. I approve it in PayPal, and it's captured exactly once." |
| 0:50 to 1:10 | Command center: click a red node, show attention bars | "The twin mirrors every buyer, device and IP. My graph attention network, written from scratch, explains each score: this account is risky because of a device shared by five flagged accounts." |
| 1:10 to 1:50 | **The defining moment: Defense drill tab.** Click *Run defense drill*. Point at red rows in step 1, the chosen row in step 2, green zeros in step 3, then the scorecard tiles. Click *Apply hardened policy to live* | "Now I attack my own system, on a frozen copy, so no live money is touched. The red team probes five playbooks, then mutates the ones that got caught: a quiet 250-dollar account takeover and a fake identity get through, 1,800 dollars in all. The simulator tests 216 policies, and every good customer it sends to review costs money, so it can't just block everything. Then it replays the identical attacks: 1,800 dollars down to 443, catch rate 96 to 99 percent, one good customer out of 324 sent to review. I apply it with one click." |
| 1:50 to 2:05 | Point at the note under the scorecard | "What's left are fake-identity warm-up orders under 60 dollars. They look like normal shopping, and catching them would cost more good customers than they're worth. The drill tells me that honestly." |
| 2:05 to 2:30 | Investigator: Investigate riskiest, show the case report; Ledger: PayPal API calls grid | "The investigator agent takes the riskiest account, maps its ring, freezes it and files a case report. It can refund through PayPal Payments v2, and only signature-verified PayPal webhooks can change anything." |
| 2:30 to 2:50 | Back to Command center | "Sentinel Twin: an agent that pays with PayPal, a twin that checks every order, and a red team that keeps the defense honest, so small merchants can trust agentic commerce. Open source, with 11 automated tests, including the payment-safety guarantees and the drill." |

**Numbers to say:** read them off your own screen on the day. The ones above come from a real run on 12 Nov 2026 and vary a little with live traffic. Don't round in your favour.

Upload to YouTube as **Public** and paste the link into Devpost.
