# ZERO HUMAN — Judge Dashboard Handoff

Checkpoint: 2026-08-15 12:56 PM America/Los_Angeles  
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
- Linq: **DEPLOYMENT PENDING** — real account and public phone `+1 415-305-0091` are verified; no public base URL, registered webhook, real inbound event, or real outbound event exists yet. Runtime counters/events are zero.
- Terac: **LIVE / RECRUITING** — the real Terac MCP launched study `w14sbyed2iixiz76o5ass608` at `2026-08-15T19:59:36.142Z` for 10 adults to evaluate all 10 live products. Initial submission count: 0. The immutable catalog snapshot is in `terac/before.json`; safe MCP evidence is in `terac/mcp_evidence.json`. Monitor real responses at https://terac.com/zero-human-dropship-msusi2w8/default-project-els56czpojv0q5l5yduyo3vk/opportunities/w14sbyed2iixiz76o5ass608/submissions. No `TERAC_FEEDBACK_URL` exists until real responses are collected and applied.
- Person A CEO decisions: **PENDING** — no real decision feed was found. The dashboard renders zero decisions and no outcomes.
- Band: **DISABLED** — intentionally not part of the active loop and not treated as an error.
- Render: **PENDING** — no public Linq deployment exists.
- Replay: **PENDING** — Playwright QA passed, but no actual Replay verification artifact/endpoint exists.

No unavailable source falls back to fabricated conversations, decisions, Terac results, revenue, or catalog values. A failed panel degrades independently and cannot blank the dashboard.

## Safe static Pioneer proof

The credential-free evidence adapter is `dashboard/src/data/pioneer/index.ts`. Its values were checked against `pioneer-product-intelligence/data/recent_runs.jsonl` and the model constants in `pioneer-product-intelligence/product_intelligence.jac`. It explicitly records `serviceLive: false` and contains no credential.

## Live-source follow-ups

All integration variables are server-side. Never prefix them with `NEXT_PUBLIC_`.

- Linq one-line follow-up after a real deployment exists: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' '<LINQ_BASE_URL>' | npx vercel env add LINQ_BASE_URL production --yes && npx vercel deploy --prod --yes`
- Terac one-line follow-up after the real study endpoint exists: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' '<TERAC_FEEDBACK_URL>' | npx vercel env add TERAC_FEEDBACK_URL production --yes && npx vercel deploy --prod --yes`
- CEO one-line follow-up after Person A exposes the feed: `cd /Users/aradhyamishra/zero-human-dropship-master/dashboard && printf '%s' '<CEO_DECISIONS_URL>' | npx vercel env add CEO_DECISIONS_URL production --yes && npx vercel deploy --prod --yes`
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
