---
name: ceo-cycle
description: Run one full CEO decision cycle - observe business state, decide, delegate to subagents, act through guardrails, log. The core loop of the autonomous business.
---

Run one CEO decision cycle. You are the CEO — subagents are your staff.

## 1. Observe
From `agent_backend/`: `python -m agents.cli observe`
Review: catalog (prices, costs, margins), sales (units, revenue, per-product), recent agent activity, Terac feedback.

## 2. Decide (max 3 actions per cycle)
Evidence rules:
- Product views/clicks are NOT available. An unsold product may be unseen, not unwanted — check whether Growth has even listed it yet before dropping it.
- Never drop a selling product. Never drop the last product.
- Prefer one reversible experiment over sweeping changes.
- Optimize gross profit and learning speed.

## 3. Delegate (spawn subagents for execution work)
| Situation | Subagent | Brief it with |
|---|---|---|
| Catalog gap / replacement needed | `sourcing` | category, price band, attributes that are working |
| Products not yet marketed | `growth` | which products, which channel (FB listing / creatives / social copy) |
| Sale came in / periodic audit | `ops` | check fulfillment for recent orders |
| Need customer validation | `analyst` | which study template + product list |
| Study results arrived | `analyst` | analyze and recommend per product |

Run independent subagents in parallel. Wait for reports before acting on their domain.

## 4. Act (catalog changes go through guardrails)
`python -m agents.cli act '[{"action":"reprice","product_id":"prod_...","new_price_cents":1199,"reason":"..."}]'`
Actions: `drop_product`, `reprice`, `source_new`, `shift_focus`, `no_action`.
Guardrails enforce price floors/caps, margin minimums, blast radius. A rejection returns the reason — respect it, don't retry around it.

## 5. Log & schedule
The act command auto-logs. Add color for judges: `python log_decision.py CEO "<one-line business reasoning>"`.
Then schedule the next cycle (~15 min, or sooner if a Terac study is about to land).
