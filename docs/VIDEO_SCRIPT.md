# Demo video script (target 2:45, hard limit under 3:00)

Record at 1440x900 or 1920x1080 in Chrome with the PayPal sandbox keys and a free Gemini key set. Use your own voice or no music (no copyrighted music). Rehearse each click once before recording.

| Time | Screen | Say |
|---|---|---|
| 0:00 to 0:15 | Command center, graph settling | "AI agents are starting to shop for us. That opens two holes for small merchants: agents can be tricked, and fraud rings hide in networks that per-order rules can't see. Sentinel Twin closes both." |
| 0:15 to 0:35 | Hover KPIs, click a red node, show the attention bars | "This is a live digital twin of a PayPal business: every buyer, device and IP is a node. A graph attention network I wrote from scratch scores each account from its neighbours. Here it shows why: this account's score comes from a device shared by five risky accounts." |
| 0:35 to 1:10 | Concierge tab, choose Hindi, tap mic, speak the Diwali gift request. Show the trace, then approve in the PayPal sandbox popup | "Anyone in India can use it in their own language, by voice. I ask in Hindi for a Diwali gift under 40 dollars. The shopping agent reads my spending mandate, searches, checks the twin's risk gate and creates a real PayPal sandbox order. I approve it in PayPal and it's captured." |
| 1:10 to 1:45 | Red team tab, Launch adaptive campaign. Scroll the trace and results grid | "Now the red team. It attacks a fork of the twin with six playbooks, including a prompt injection that tells my shopping agent to buy 2,500 dollars of gift cards. The guard is in code, so it's blocked. Then the red team adapts: smaller amounts, older accounts. Low-and-slow synthetic identities get through. It found a real gap." |
| 1:45 to 2:10 | Click "Test a hardened policy". Show the chart, then Apply | "Before I change anything real, the what-if simulator replays the twin's traffic and those attacks under a hardened policy. The catch rate goes up (read the two numbers on screen) without blocking good customers. Then I apply it." |
| 2:10 to 2:35 | Investigator tab, Investigate riskiest, show the case report, then the Ledger with PayPal API calls | "The investigator agent takes the riskiest account, asks the GAT why, maps the ring through shared devices, freezes it and files a case report. It can refund through PayPal, and a PayPal dispute webhook opens an investigation automatically." |
| 2:35 to 2:50 | Back to Command center | "Sentinel Twin: a digital twin, a graph attention network and four agents on PayPal, so small merchants get a fraud team, a red team and a shopping assistant in their own language. Open source and deployable on Render in one click." |

Upload to YouTube as **Public** (or Unlisted only if the rules allow; Public is safest) and paste the link into Devpost.
