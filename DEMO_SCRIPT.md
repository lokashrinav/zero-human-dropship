# KOVA — Demo Script (~2:30)

> Numbers are real as of 5:25 PM: $16.46 Stripe revenue, 4 orders, 2 real external customers. Update live totals right before you go on — pull from the dashboard.

---

## [0:00–0:15] — COLD OPEN
**SCREEN: storefront hero (storefront-omega-three.vercel.app)**

> "Welcome to KOVA — an autonomous AI dropshipping company. Not an AI tool a human drives — a company. It sources its products, sets its prices, runs its marketing, sells, fulfills, and learns — with zero humans in the loop. Today it ran itself... and made real money."

## [0:15–1:00] — THE ITERATION ENGINE (the killer 45 seconds)
**SCREEN: the decision feed on the dashboard, scrolling today's history**

> "Here's the part that matters: every 15 minutes, a brand-new AI CEO is born with zero memory. It reads the company diary — every decision every agent before it ever made — acts, writes its entry, and dies. The company is immortal; the agents are disposable."

**Point at real feed entries as you talk:**
> "Watch one day of self-iteration: Ten real humans on a Terac panel rated our catalog — the company reordered its own storefront and repriced three products from the data. Then Ops discovered true fulfillment costs were higher than believed — the CEO repriced again, inside hard-coded guardrails: max 35% per cycle, margin floors, three actions max. It renamed two products because their listings were inaccurate. It even found a bug in its own launcher script, patched it, and filed a note asking a human to restart it."

> "When it hits something only a human can do — a password, funding a wallet — it doesn't stop. It files the exact fix on an escalation queue and keeps working. The business has literally never stopped today."

## [1:00–1:45] — THE SURFACES (zero-human, one data layer)
**SCREEN: split or quick cuts — storefront → FB Marketplace listing → dashboard**

> "Everything you see was built and is operated by agents on one shared data layer:
> — The **storefront**: ten live products, real Stripe checkout, product images the agents *bought* — I'll get to that.
> — **Facebook Marketplace**: ten listings posted by an agent driving a real browser, funneling buyers to the store.
> — And this **control room** you're watching: live revenue — **$16.46, four orders, two real customers who found us organically today** — every agent decision, every human-needed escalation. Judges can audit every dollar and every decision back to its reasoning."

## [1:45–2:25] — THE INTEGRATIONS
**SCREEN: dashboard sponsor panels / feed entries as props**

> "The stack, briefly:
> — **Stripe** is the ledger — the only revenue that counts is real money here.
> — **Terac** twice over: real human panels as the company's market research — and when an agent hits a human-shaped wall, it can *hire* a Terac human with exact instructions.
> — **Linq**: the company has a real iMessage number — text it right now (+1 415-305-0091) and an agent sells to you and sends a payment link.
> — **Perflo**: the company has its own wallet. When it needed product creatives, it *paid* an x402 vendor half a cent per image from its own balance, under a spend cap a human armed once. Take the wallet away and the creative pipeline dies — money is load-bearing.
> — **Solari** cloud browsers audit the store; **Pioneer** open-weight models write product intelligence; **CJ Dropshipping** — the company created real supplier orders for today's customers by itself."

## [2:25–2:35] — CLOSE
**SCREEN: back to the feed, live**

> "KOVA priced, sold, fulfilled, hired, spent, and debugged itself today. Nobody prompted the decisions you just saw. And it's not a recording — it's still running right now."

*(If a cycle fires during Q&A — point at it.)*

---

## Live-demo insurance
- Have the dashboard AND the local feed (`tail -f agent_backend/decision_log.jsonl`) open — if WiFi dies, the local feed still scrolls.
- Best interactive moment: a judge texts the Linq number; the reply lands on-screen.
- If asked "what CAN'T it do": answer honestly — passwords, 2FA, and arming money. It queues those for humans and keeps moving. That's a design decision, not a limitation.
- If asked about the loss-making products: "It discovered its own negative margins from fulfillment data and corrected them at guardrail-max speed — that's the learning loop working, not a bug."
