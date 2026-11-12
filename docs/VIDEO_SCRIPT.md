# Demo video script (target 2:45, hard limit under 3:00)

**The one story:** an AI shopping agent buys a real product and pays with PayPal; the digital twin checks every order on its graph and leaves a receipt; the red team finds a weakness on a safe copy; a safer policy is chosen and proven on the same attacks; a human approves anything consequential.

Record at 1440x900 or 1920x1080 in Chrome. The header pills should read **PayPal sandbox · live**, **Gemini · gemini-2.5-flash** and **Channel3 · live products**. Use your own voice, no copyrighted music. Rehearse each click once.

**Before recording (off camera, then don't restart the app):**
1. Run one defense drill so you know your numbers, then click *Roll back* on the Defense drill tab.
2. In Concierge, turn off *Speak replies* if you'll talk over it.
3. Have your PayPal **sandbox buyer** login ready for the popup.

| Time | Click by click | Say |
|---|---|---|
| **0:00 to 0:25** · Landing, then Command center | Open the landing page (http://localhost:8000, or `/static/landing.html` on a server started before the landing page existed), hold on the smoky hero for 2 seconds, click **Launch live demo →**. Then start on the app hero. Scroll slowly past the **Defense score** gauge and **Decisions** donut to the twin graph. Click a coral **Ring** label (for example "Ring 1 · 8 accounts · 4 shared"). The graph zooms in and **Why is it risky?** fills with attention bars. | "AI agents are starting to spend money for us. Sentinel Twin is a digital twin of a PayPal business that catches fraud before money moves. Every buyer, device and IP is a node, and a graph attention network has found these fraud rings: accounts sharing devices. I click one, and it explains exactly which neighbours made this account risky." |
| **0:25 to 1:05** · Concierge | Click **Try the shopping agent**. Type: *Find a coffee gift under $40*. Real **Channel3** product cards appear with photos and retailers. Type: *Buy the* [first item]. Point at the checkout card: green **mandate ticks**, the **approve** pill, then click the yellow **PayPal** button and approve in the sandbox popup. Show **capture COMPLETED**, then click **Why? (receipt)**. | "The shopping agent runs on Gemini and searches real products from twenty-five thousand retailers through Channel3. I ask it to buy one. Before any PayPal order exists, my spending mandate is checked in code, not by the model, and the twin scores the order on its graph. It's approved, so a real PayPal sandbox order is created. I approve it, and it's captured exactly once. Every checkout leaves a receipt: each mandate check, the risk split into graph and rules, the policy version and the PayPal ids." |
| **1:05 to 1:50** · Defense drill | Click the **Defense drill** tab. Point at the **Attack flow** (red arrows get through, blue bounce off). Click **Run defense drill**. Point at a red row and its *Why* line in step 1, the **chosen** row in step 2, the **before → after** tiles in step 4. | "Now I attack my own system, on a frozen copy, with synthetic attack traffic. The red team probes, then adapts whatever got caught, and it says why. [Say your number] dollars get through. The simulator tests 216 policies and prices every good customer sent to review, so it can't just block everything. The same attacks replayed: [after number]. And on attacks it never saw, it still holds." |
| **1:50 to 2:10** · Why a graph? | Scroll to **5 · Why a graph?** Point at the chart. Scroll back up and click **Apply hardened policy to live**. | "Why a graph? Same orders, three engines: rules alone, rules plus the graph, and the hardened policy. The graph wins on rings and device farms, new accounts that share devices. Where rules do better, the screen says so. I apply it, and the next checkout uses the safer policy." |
| **2:10 to 2:35** · Investigator | Click **Investigator**, then **Investigate riskiest**. Show the case report. In **Review queue**, click approve on one proposal, then open **Audit trail**. | "The investigator agent maps the ring and files a case with real graph evidence. But it can't act alone: refunds and restrictions are only proposals. I approve this one, and it lands in the audit trail with my name." |
| **2:35 to 2:45** · Close | Click **Command center**. The gauge now shows your hardened score. | "Sentinel Twin: an agent that pays with PayPal, a twin that checks every order, a red team that keeps the defense honest, and a human in charge. Open source, with 21 automated tests." |

**Numbers to say:** read them off your own screen on the day. They move with live traffic and training. A real run on 12 Nov 2026 showed $1,808 → $443 got through and an intercept rate of 93.9% → 98.5%. Don't round in your favour.

**Honesty notes (if asked):** attack traffic is synthetic and labelled so. Channel3 provides live product data, but payment is a PayPal **sandbox** order and we don't buy from the retailer. "Restrict" is a merchant-side restriction inside the twin, not a PayPal account freeze.

## Closing line (final ~25s)

Use this in place of the short close at 2:35. It runs about 25 seconds, so trim ~15 seconds from the Concierge or drill beats to stay under 3:00. Show the Command center (gauge and neon graph), then cut to the landing page's final band for the last line.

> "Agents are going to spend real money for people. That only works if every checkout is guarded before money moves. Sentinel Twin gives a merchant a living copy of their business: a graph model that sees fraud rings rules miss, an AI red team that attacks the twin, not customers, and a drill that turns every breach into a tested policy, while a human signs off on anything irreversible. Shop by asking. Pay with PayPal. Safely. This is Sentinel Twin."

Upload to YouTube as **Public** and paste the link into Devpost.
