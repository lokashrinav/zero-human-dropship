# ZERO HUMAN — Judge Dashboard Handoff

Checkpoint: 2026-08-15 2:45 PM America/Los_Angeles
Production deployment: `dpl_7kcuApC3HR24wMJ8WFuzSBszz8Vu`

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
- Linq: **LIVE** — https://zero-human-linq-agent.onrender.com serves the Jac-first agent for public phone `+1 415-305-0091`. Partner v3 authentication and the active signed `message.received` webhook subscription are verified. A real inbound request selected the catalog's `LED Strip Lights RGB 16 Colors`, sent the grounded recommendation, and opened the HTTP-200 storefront product page. The follow-up explicit-purchase text is still required to verify the direct trusted Stripe-link send after the UX update.
- Terac: **FULFILLED / LIVE EVIDENCE** — real Terac MCP study `w14sbyed2iixiz76o5ass608` produced 10/10 approved responses. USB-C Cable ranked first at 3.9/5; Laptop Cooling Pad ranked second at 3.8/5 and had the most most-likely selections (3). The immutable before snapshot, aggregate, after snapshot, and MCP audit live in `terac/`. Public feed: https://storefront-omega-three.vercel.app/api/terac-feedback.
- Person A CEO decisions: **LIVE** — the data-backed `terac_reorder` decision moved USB-C Cable from #2 to #1 and Magnetic Phone Mount from #9 to #3 without changing prices, Payment Links, shipping, products, or claimed outcomes. Public feed: https://storefront-omega-three.vercel.app/api/ceo-decisions.
- Band: **DISABLED** — intentionally not part of the active loop and not treated as an error.
- Render: **LIVE** — Linq health, status, and cursor-paginated event endpoints return HTTP 200 publicly.
- Replay: **PENDING** — Playwright QA passed, but no actual Replay verification artifact/endpoint exists.

No unavailable source falls back to fabricated conversations, decisions, Terac results, revenue, or catalog values. A failed panel degrades independently and cannot blank the dashboard.

## Safe static Pioneer proof

The credential-free evidence adapter is `dashboard/src/data/pioneer/index.ts`. Its values were checked against `pioneer-product-intelligence/data/recent_runs.jsonl` and the model constants in `pioneer-product-intelligence/product_intelligence.jac`. It explicitly records `serviceLive: false` and contains no credential.

## Live-source follow-ups

All integration variables are server-side. Never prefix them with `NEXT_PUBLIC_`.

- Linq dashboard source: `LINQ_BASE_URL=https://zero-human-linq-agent.onrender.com`. The public contracts are `GET /api/status` and `GET /api/events?cursor=0&limit=100`.
- Terac one-line follow-up: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' 'https://storefront-omega-three.vercel.app/api/terac-feedback' | npx vercel env add TERAC_FEEDBACK_URL production --yes && npx vercel deploy --prod --yes`
- CEO one-line follow-up: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' 'https://storefront-omega-three.vercel.app/api/ceo-decisions' | npx vercel env add CEO_DECISIONS_URL production --yes && npx vercel deploy --prod --yes`
- Stripe revenue one-line follow-up with a dedicated server-side key: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' '<STRIPE_SECRET_KEY>' | npx vercel env add STRIPE_SECRET_KEY production --sensitive --yes && npx vercel deploy --prod --yes`

The Linq adapter will call `GET /api/status` and `GET /api/events?cursor=0&limit=100`. Exact response contracts, catalog variants, Terac input, and revenue attestation are in [`dashboard/INTEGRATION_CONTRACTS.md`](dashboard/INTEGRATION_CONTRACTS.md).

## 60-second judge flow for current state

1. **0–8s:** Open production. Point to `AUTONOMOUS COMPANY — LIVE`, then the metric row: 10 products are live; revenue truthfully says waiting.
2. **8–18s:** Open one promoted product name to show its real Stripe checkout. Say: “Ten live products and ten real Payment Links; products are never counted as revenue.”
3. **18–30s:** Trace `SOURCE → VALIDATE WITH HUMANS → LIST → SELL → FULFILL → LEARN ↺`. Explain that the active stage waits for a genuine Linq or CEO event.
4. **30–40s:** Point to Pioneer `VERIFIED`: GPT-OSS 120B + Fastino GLiNER2 passed a real three-product run. Clarify that it is verified historical evidence, not an always-on service.
5. **40–50s:** Show Linq's real number and `DEPLOYMENT PENDING`, with zero conversations/events. Do not attempt the live text demo until its public URL and webhook are verified.
6. **50–57s:** Show the empty Terac and CEO panels. Say they intentionally wait for the real human study and resulting autonomous decision.
7. **57–60s:** Sweep the sponsor chips: real/verified, pending, and disabled are visibly distinct.

## Verification

- TypeScript: PASS
- Next.js production build: PASS
- Existing Playwright suite: 12/12 PASS locally at 1440×900 and 390×844
- Existing Playwright suite: 12/12 PASS against production at 1440×900 and 390×844
- Forced aggregate-feed 503: PASS; last safe snapshot remains visible with `FEED DEGRADED`
- Production `/api/dashboard`: HTTP 200, `Cache-Control: no-store`
- Production catalog state: 10 products, 10 active, 10 Stripe links
- Desktop visual QA: 1440×900, no overflow, no console errors
- Mobile visual QA: 390×844, no overflow, no console errors

Replay steps and evidence requirements remain in [`REPLAY_CHECKLIST.md`](REPLAY_CHECKLIST.md).
