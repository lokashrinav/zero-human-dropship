---
name: market-blitz
description: Marketing push - FLUX creatives for top products, FB Marketplace listings via browser, share-ready social copy with payment links.
---

Run a marketing push. Argument (optional): specific products; default is every product not yet marketed.

1. `python -m agents.cli observe` from `agent_backend/` — pick targets (unmarketed first, then top margin).
2. Spawn the `growth` subagent with the target list. It should, in order:
   a. Generate one FLUX creative per target product
   b. Post FB Marketplace listings (browser) — store link in description, never raw payment links
   c. Draft social share copy (product + payment link) and save to `marketing/share_copy.md`
3. Browser tasks are sequential (one Chrome). If FB blocks or CAPTCHAs, the subagent stops and reports — the fallback is listing manually.
4. Log the blitz outcome: `python log_decision.py CEO "Market blitz: <n> listings, <n> creatives"`.
