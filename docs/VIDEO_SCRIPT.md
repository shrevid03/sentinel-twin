# Demo video: full shooting script (target 2:45, hard limit under 3:00)

The whole speech, scene by scene, with what to click and how to film it. About 400 spoken words, which is roughly 2:45 at a calm pace. Read it out loud once with a timer before you record.

---

## Before you film (10 minutes)

**Machine**
- Let the Mac cool down if it's hot. Close every app except Chrome and your recorder. Plug in the charger.
- Turn on **Do Not Disturb** (Control Centre → Focus) so no notifications pop up.
- Start the app once: `cd ~/sentinel-twin && .venv/bin/uvicorn app.main:app --port 8000`. **Don't restart it again until you've finished filming**, because a restart clears the drill and payments.

**Chrome**
- Use a clean window: hide the bookmarks bar (Cmd+Shift+B), close other tabs, zoom at 100% (Cmd+0).
- Window size about 1440x900. Full screen (Ctrl+Cmd+F) looks cleanest.
- Open two tabs: tab 1 is the landing page (http://localhost:8000, or `/static/landing.html` if the server predates the landing page); tab 2 is the app at `/app` (or `/`).
- Check the header pills read **PayPal sandbox · live**, **Gemini · gemini-2.5-flash** and **Channel3 · live products**.

**Warm-up, off camera**
- Run one **defense drill** so you know your numbers, then click **Roll back** on the Defense drill tab.
- In Concierge, untick **Speak replies**.
- Have your **US personal sandbox buyer** login ready (not the business login). If the popup gives trouble, log in to the sandbox buyer once in the same Chrome profile first.

**Recording**
- QuickTime Player → File → New Screen Recording → Options: your mic, and **Show Mouse Clicks**. Or use OBS if you have it.
- Record **each scene as its own clip**. Retakes are then cheap, and you cut them together at the end (iMovie is fine).
- Talk slower than feels natural. Move the mouse slowly and stop it while you're talking about something.
- Option that sounds better: record the clicks silently first, then record the voice-over separately on your phone in a quiet room, closer to the mic.

---

## Scene 1: The hook (0:00–0:15)

**On screen:** the landing page hero, with the smoke drifting. Hold still for 2 seconds, slowly move the mouse across the smoke (it shifts a little), then click **Launch live demo →**.

**Say:**
> "AI agents are about to spend real money for people. That's exciting, and it's dangerous: one tricked agent, one fraud ring, and the money's gone. This is Sentinel Twin. It makes sure fraud is caught before money moves."

**Filming tip:** start recording one second before you speak, so you have room to trim. Don't scroll on the landing page; just the hero, then Launch.

---

## Scene 2: The twin (0:15–0:35)

**On screen:** the app's Command center. Scroll slowly past the **Defense score** gauge and the **Decisions** donut down to the neon graph. Hover one fraud-ring chip, then click it. The graph zooms in and **Why is it risky?** fills with attention bars. Point the mouse at the top bar.

**Say:**
> "This is a digital twin of a PayPal business. Every buyer, device and IP address is a node in a live graph. A graph attention network found these fraud rings, accounts quietly sharing the same devices. I click one, and it shows exactly which neighbours made this account risky."

**Filming tip:** let the zoom finish before you speak the last sentence. If the chip label overlaps, click the chip anyway; it focuses the ring.

---

## Scene 3: Shop by asking, pay with PayPal (0:35–1:15)

**On screen:**
1. Click the **Concierge** tab. Type: *Find a coffee gift under $40*. Press Enter. Real product cards from Channel3 appear with photos.
2. Type: *Buy the first one*. The checkout card appears.
3. Point the mouse at the green **mandate ticks**, then the **approve** pill.
4. Click the yellow **PayPal** button and approve in the sandbox popup.
5. Back in the app, show **capture COMPLETED**. Click **Why? (receipt)** and let the receipt open for 2 seconds.

**Say:**
> "Now the shopping agent. It runs on Gemini, and it searches real products from thousands of retailers through Channel3. I ask it to buy one. Before any PayPal order exists, my spending limits are checked in code, not by the AI, and the twin scores the order on its graph. It's approved, so a real PayPal sandbox order is created. I approve it, and it's captured exactly once. And every checkout leaves a receipt: every check, the risk score, and the PayPal ids."

**Filming tip:** the PayPal popup login is boring and shows an email address. **Cut it out in editing**: stop talking while the popup is open, and trim from the moment you click the yellow button to the moment the popup closes. Never show passwords on screen.

---

## Scene 4: Attack it, fix it, prove it (1:15–1:55)

**On screen:**
1. Click the **Defense drill** tab. Point at the **Attack flow** animation (red arrows get through, blue bounce off).
2. Click **Run defense drill**.
3. In step 1, point at one red row and its *Why* line.
4. In step 2, point at the row marked **chosen**.
5. In step 4, point at the **before → after** tiles.

**Say:**
> "Now I attack my own system, on a frozen copy, never on real customers. An AI red team throws fraud rings, card testing and account takeovers at the twin, and when it gets caught, it changes tactics and explains why. [Your number] dollars get through. The simulator then tests two hundred and sixteen policies, and it charges itself for every good customer it would annoy, so it can't just block everyone. Same attacks, replayed: only [your after number] gets through."

**Filming tip:** read your two numbers off step 4 during your warm-up and write them on a sticky note. The drill takes a few seconds: keep talking over it, or cut the wait.

---

## Scene 5: Why a graph? (1:55–2:10)

**On screen:** scroll down to **5 · Why a graph?** and point at the chart. Then scroll up and click **Apply hardened policy to live**.

**Say:**
> "Why a graph at all? Same orders, three engines. Rules alone catch about forty-two percent. Add the graph and it's around eighty. With the hardened policy, ninety-five. The graph wins on rings and device farms, the fraud rules can't see. I apply it, and the very next checkout is safer."

**Filming tip:** if your screen shows different numbers, say yours. Don't round up.

---

## Scene 6: Humans stay in charge (2:10–2:25)

**On screen:** click **Investigator** → **Investigate riskiest**. Let the case report appear. In **Review queue**, click **Approve** on one proposal, then open **Audit trail**.

**Say:**
> "The investigator agent maps the ring and files a case with real evidence. But it can't act alone. Refunds and restrictions are only proposals, until a person approves them. Every decision lands in the audit trail."

**Filming tip:** the investigator takes a few seconds with Gemini; trim the wait.

---

## Scene 7: Closing (2:25–2:50)

**On screen:** click **Command center**; the gauge now shows your hardened score. Hold for 3 seconds on the neon graph. Then switch to the landing page tab and scroll to the bottom band, "Safe checkout, before money moves.", and hold still to the end.

**Say:**
> "Agents are going to spend real money for people. That only works if every checkout is guarded before money moves. Sentinel Twin gives a merchant a living copy of their business: a graph model that sees fraud rings rules miss, an AI red team that attacks the twin, not customers, and a drill that turns every breach into a tested policy, while a human signs off on anything irreversible. Shop by asking. Pay with PayPal. Safely. This is Sentinel Twin."

**Filming tip:** slow down for the last three short sentences, with a small pause before "This is Sentinel Twin." End on 2 seconds of silence over the final band, then cut.

---

## Editing and upload

- Put the seven clips in order and trim the dead air at the start and end of each. Cut the PayPal login and any long waits.
- Check the total is **under 3:00**. If it's long, trim scene 3 or scene 4 first.
- No copyrighted music. Your voice alone is fine, or very quiet royalty-free music.
- Export 1080p. Upload to YouTube as **Public**, title it "Sentinel Twin: safe AI checkout with PayPal", and paste the link into Devpost.

## If someone asks (honesty notes)

- Attack traffic is synthetic and labelled so on screen.
- Channel3 provides real product data, but the payment is a PayPal **sandbox** order. We don't actually buy from the retailer.
- "Restrict" is a merchant-side restriction inside the twin, not a PayPal account freeze.
- The numbers move a little with live traffic and training: always say the ones on your screen.
