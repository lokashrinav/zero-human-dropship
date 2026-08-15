# ZERO HUMAN — Judge Dashboard Handoff

Checkpoint: 2026-08-15 2:21 PM America/Los_Angeles
Production deployment: `dpl_7BNE4hJJjJeWgKBkkT1CqywFNnWF`

## Dashboard

- Production: https://zero-human-control-room.vercel.app
- Local app: `/Users/aradhyamishra/zero-human-dropship-master/dashboard`
- Stable route: `/`
- Aggregate polling route: `/api/dashboard`
- Refresh interval: 4 seconds while the page is visible

## Verified production state

- Dashboard: **LIVE on Vercel**; required alias points to a `READY` production deployment.
- Catalog: **REAL / LIVE** from `https://storefront-omega-three.vercel.app/api/catalog` — 10/10 active products, prices $3.49–$8.99, and 10 distinct `buy.stripe.com` Payment Links.
- Stripe commerce: **REAL COMMERCE** — catalog and checkout links are live.
- Stripe revenue: **WAITING** — revenue and orders remain `null`. Vercel would not export the storefront's sensitive encrypted key, so the dashboard still needs either its own server-only `STRIPE_SECRET_KEY` or an attested `STRIPE_REVENUE_URL`. Products and Payment Links are not counted as revenue.
- Pioneer: **VERIFIED REAL RUN** — GPT-OSS 120B inference PASS, Fastino GLiNER2 validation PASS, three-product pipeline PASS, top ranking `demo-cable (95)`, verified `2026-08-15T19:20:56.289815Z`. This is historical evidence, not a live Pioneer service.
- Linq: **LIVE** at `https://zero-human-linq-agent.onrender.com` — public status/events endpoints are HTTP 200 and the agent is online at `+1 415-305-0091`. A complete real inbound conversation, catalog-grounded recommendation, and trusted Stripe checkout link were verified at `2026-08-15T20:56:57Z`. Render restarted at `2026-08-15T21:12:13Z`, clearing the service's in-memory history; at this checkpoint a fresh real flow reports 1 conversation, 1 recommendation, and 0 payment links sent. The dashboard renders current API values rather than fixed demo counts.
- Terac: **VERIFIED / REAL HUMAN FEEDBACK** — real Terac MCP study `w14sbyed2iixiz76o5ass608` produced 10/10 approved responses and 100 ratings. USB-C Cable ranked first at 3.9/5; Laptop Cooling Pad ranked second at 3.8/5 and had the most most-likely selections (3). Phone Ring Light and Portable Mini Fan tied for lowest at 2.5/5. The immutable before snapshot, aggregate, after snapshot, and MCP audit live in `terac/`. Public feed: https://storefront-omega-three.vercel.app/api/terac-feedback.
- Person A CEO decisions: **LIVE** — the data-backed `terac_reorder` decision moved USB-C Cable from #2 to #1 and Magnetic Phone Mount from #9 to #3 without changing prices, Payment Links, shipping, products, or claimed outcomes. Public feed: https://storefront-omega-three.vercel.app/api/ceo-decisions.
- Band: **DISABLED** — intentionally not part of the active loop and not treated as an error.
- Render: **PENDING PROOF CHIP** — Linq is publicly deployed on Render, but no independent Render status/verification feed is configured for the dashboard sponsor chip.
- Replay: **PENDING** — Playwright QA passed, but no actual Replay verification artifact/endpoint exists.

No unavailable source falls back to fabricated conversations, decisions, Terac results, revenue, or catalog values. A failed panel degrades independently and cannot blank the dashboard.

## Safe static Pioneer proof

The credential-free evidence adapter is `dashboard/src/data/pioneer/index.ts`. Its values were checked against `pioneer-product-intelligence/data/recent_runs.jsonl` and the model constants in `pioneer-product-intelligence/product_intelligence.jac`. It explicitly records `serviceLive: false` and contains no credential.

## Production integration configuration

All integration variables are server-side. Never prefix them with `NEXT_PUBLIC_`.

- `TERAC_FEEDBACK_URL=https://storefront-omega-three.vercel.app/api/terac-feedback`
- `CEO_DECISIONS_URL=https://storefront-omega-three.vercel.app/api/ceo-decisions`
- `LINQ_BASE_URL=https://zero-human-linq-agent.onrender.com`
- Linq follow-up required: **none**; both public endpoints are connected and verified.
- Terac/CEO follow-up required: **none**; both public feeds are connected and verified.
- Stripe revenue one-line follow-up with a dedicated server-side key: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' '<STRIPE_SECRET_KEY>' | npx vercel env add STRIPE_SECRET_KEY production --sensitive --yes && npx vercel deploy --prod --yes`

The Linq adapter will call `GET /api/status` and `GET /api/events?cursor=0&limit=100`. Exact response contracts, catalog variants, Terac input, and revenue attestation are in [`dashboard/INTEGRATION_CONTRACTS.md`](dashboard/INTEGRATION_CONTRACTS.md).

## 60-second judge flow

1. **0–8s:** Open production. Point to `AUTONOMOUS COMPANY — LIVE`, then the metric row: 10 products are live; revenue truthfully says waiting.
2. **8–18s:** Open one promoted product name to show its real Stripe checkout. Say: “Ten live products and ten real Payment Links; products are never counted as revenue.”
3. **18–30s:** Trace `SOURCE → VALIDATE WITH HUMANS → LIST → SELL → FULFILL → LEARN ↺`. Point to `SELL` as the active stage from the real Linq event stream.
4. **30–40s:** Point to Pioneer `VERIFIED`: GPT-OSS 120B + Fastino GLiNER2 passed a real three-product run. Clarify that it is verified historical evidence, not an always-on service.
5. **40–50s:** Show Linq `LIVE` at `+1 415-305-0091`. If the in-memory flow is present, trace `INBOUND MESSAGE → SALES AGENT → PRODUCT SELECTED → CHECKOUT LINK SENT`; after a Render restart, send a fresh inbound text to recreate the live flow.
6. **50–57s:** Show the real 10-person Terac result and the CEO decision: USB-C Cable moved from #2 to #1 while products, prices, copy, availability, and checkout links stayed unchanged. Make no sales-improvement claim.
7. **57–60s:** Sweep the sponsor chips: real/verified, pending, and disabled are visibly distinct.

## Verification

- TypeScript: PASS
- Next.js production build: PASS
- Existing Playwright suite: 12/12 PASS locally at 1440×900 and 390×844
- Existing Playwright suite: 12/12 PASS against production at 1440×900 and 390×844
- Forced aggregate-feed 503: PASS; last safe snapshot remains visible with `FEED DEGRADED`
- Production `/api/dashboard`: HTTP 200, `Cache-Control: no-store`
- Production catalog state: 10 products, 10 active, 10 Stripe links
- Production Linq state: online; complete 1/1/1 sales flow verified before restart, current post-restart checkpoint 1 conversation / 1 recommendation / 0 payment links sent
- Production Terac/CEO state: 10-person study and 1 real `terac_reorder` decision; no fabricated outcome
- Desktop visual QA: 1440×900, no overflow, no console errors
- Mobile visual QA: 390×844, no overflow, no console errors

Replay steps and evidence requirements remain in [`REPLAY_CHECKLIST.md`](REPLAY_CHECKLIST.md).
