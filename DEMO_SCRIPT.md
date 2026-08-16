# KOVA — Final Demo Script (~2:30)

> Update the revenue/order numbers from the dashboard RIGHT before going on. As of 6:25 PM: 5 paid orders, 3 real external buyers.

---

## [0:00 – 0:15] — INTRO
*(storefront on screen)*

Welcome to KOVA.

KOVA is an autonomous AI dropshipping business. It finds products, prices them, lists them, sells them, and fulfills them — and it improves that whole process on its own. We turned it on this morning. It's been running itself since, and it's made real money.

## [0:15 – 1:40] — THE DEMO: WATCH IT RUN
*(decision feed on screen)*

This is the company's decision log, live. Fresh agents spin up continuously — each one reads everything the agents before it did, looks at current sales, makes its moves, and logs them. The agents use a library of skill files that improve over time — playbooks the main agent hands to subagents to get tasks done.

Here's today, straight from the log. The company put its catalog in front of ten real people — a human panel through Terac — and used their ratings to reorder the store and change three prices. A few hours later, ops figured out our real fulfillment costs were higher than the agent believed — we were losing money on some items — so the next agent repriced everything, inside hard-coded limits it can't cross: never a huge jump at once, never below margin.

And when it needs something only a human can do — a password, funding a wallet — it doesn't stop. It queues the task with the exact fix, either to us or to a hired Terac worker with written instructions, and keeps working.

*(switch: storefront → Facebook → dashboard)*

Now here's where the money actually flows. The company sells through three doors: the storefront, Facebook Marketplace — where an agent posted every listing through a real browser — and an iMessage line through Linq. Text that number right now and an agent will pitch you a product and send a payment link.

Every checkout runs on Stripe, and a payment is the trigger for fulfillment: the moment it lands, an agent places the order on Amazon, shipped Prime, straight to the buyer's door. We never touch inventory. Today that's [CURRENT REVENUE] across [N] orders — [N] of them from strangers who found us on their own.

## [1:40 – 2:20] — THE STACK
*(dashboard sponsor panels)*

Everything the company does runs through real services, the same ones a human-run business would use.

Customers pay through Stripe — every sale is a real card payment landing in a real account.

We use Terac in two directions. Real human panels serve as the company's market research, and when an agent gets stuck on a task that only a human can do, it can hire a Terac worker by writing out exact instructions.

Through Linq, the company has its own iMessage number. If you text it right now, an agent will market a product to you and send you a payment link, which gives the company an inbound sales channel.

Through Perflo, the company holds its own wallet. It paid another AI service five cents for a product photo, out of its own balance, under a spending cap that we set once. If you take that wallet away, the creative pipeline stops working.

Behind the scenes, Solari's cloud browsers continuously audit the store that customers actually see, and Pioneer's open-weight models write the product intelligence. And when a customer pays, the company fulfills the order itself by placing it on Amazon, shipped directly to the buyer's door.

The storefront was audited with Replay: its first run covered fifteen user journeys and surfaced nine findings — including a clipped hero layout and search inputs screen readers couldn't name — the agents fixed them, redeployed, and the final Replay run came back clean. The judge dashboard went through the same Replay audit and came back clean on the first pass — no fixes required, with the verified report on record.

*(Only if teammate confirms: "The Linq sales service runs deployed on Render, with a Render Workflow that audits the catalog.")*

## [2:20 – 2:30] — CLOSE
*(back to the live feed)*

Today KOVA priced, sold, fulfilled, and fixed itself. Nobody prompted the decisions you just saw — and it's still running right now.

Thanks.

---

## Q&A insurance
- **"What can't it do?"** — "Passwords, two-factor, and putting money in. It queues those for a human and keeps moving. That's a design decision — an agent that types your passwords isn't autonomy, it's a liability."
- **"Why were products priced below cost?"** — "It discovered its own negative margins from real fulfillment data and corrected them the same afternoon. That's the learning loop working."
- **"Is the Perflo thing real?"** — pull the ledger: transaction ba377332, $0.05 USDC over x402 to the image vendor, settled.
- WiFi dies: `tail -f agent_backend/decision_log.jsonl` locally — the feed still scrolls.
