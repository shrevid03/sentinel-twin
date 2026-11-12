# Demo video script (target 2:50, hard limit under 3:00)

**The one story:** an AI shopping agent pays with PayPal; the digital twin checks every order and leaves a receipt; the red team finds a weakness on a safe copy; the simulator picks a safer policy and prices its cost to good customers; the same attack, and attacks it never saw, are stopped; a human approves anything consequential.

Record at 1920x1080 in Chrome with PayPal sandbox keys and a free Gemini key in `.env` (header badges: **PayPal sandbox · live** and **gemini**). Use your own voice, no copyrighted music. Rehearse each click once.

**Before recording:** click **Reset demo**, let live traffic run for a minute, run the drill once off camera so you know your numbers, then click *Roll back*.

| Time | Screen | Say |
|---|---|---|
| 0:00 to 0:12 | Command center, graph settling | "AI agents are starting to spend money for us. Sentinel Twin makes sure an agent can't be tricked into paying, and that fraud is caught before money moves. Here's the loop, live, on PayPal." |
| 0:12 to 0:45 | Concierge, Hindi, mic: Diwali gift under $40. Show the trace, approve in the PayPal sandbox popup, show "capture COMPLETED", click **Why? (decision receipt)** | "I ask in Hindi for a Diwali gift under 40 dollars. The shopping agent reads my spending mandate and searches, and the twin scores the order on its graph before any PayPal order exists. It creates a real PayPal sandbox order, I approve it, and it's captured exactly once. Every checkout leaves a receipt: each mandate check, the risk split into graph and rules, the policy version, and the PayPal ids." |
| 0:45 to 1:00 | Command center: click a red node, show attention bars | "The twin mirrors every buyer, device and IP. My graph attention network explains each score: this account is risky because of a device shared by flagged accounts." |
| 1:00 to 1:45 | **Defense drill tab.** Click *Run defense drill*. Point at red rows and a "Why" line in step 1, the chosen row in step 2, green zeros in step 3, the scorecard tiles. Click *Apply hardened policy to live* | "Now I attack my own system, on a frozen copy, with synthetic attack traffic. The red team probes five playbooks, then adapts the ones that were intercepted, and it says why. Twenty-six hundred dollars gets through. The simulator tests 216 policies, and every good customer it sends to review costs money, so it can't just block everything. Same attacks replayed: 443 dollars. And on attacks it never tuned on: 2,200 down to 434. One good customer out of 324 goes to review. I apply it." |
| 1:45 to 2:05 | Scroll to step 5, **Why a graph?** | "Why a graph? Same orders, three engines. Rules alone intercept 42 percent of these attacks; with the graph, about three quarters; with the hardened policy, 95. The graph wins on rings and device farms, new accounts sharing devices. Rules are slightly better on card testing, and the screen says so." |
| 2:05 to 2:35 | Investigator: *Investigate riskiest*, show the case report, then the **Review queue**: approve one restriction, reject one, open the audit trail | "The investigator maps the ring and files a case with real graph evidence. But it can't act alone: refunds and restrictions are only proposals. I approve one, reject another, and both land in the audit trail with my name." |
| 2:35 to 2:50 | Back to Command center | "Sentinel Twin: an agent that pays with PayPal, a twin that checks every order, a red team that keeps the defense honest, and a human in charge of every consequential action. Open source, with 18 automated tests." |

**Numbers to say:** read them off your own screen on the day. The ones above come from a real run on 12 Nov 2026 and move with live traffic and GAT training. Don't round in your favour.

Upload to YouTube as **Public** and paste the link into Devpost.
