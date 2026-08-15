# Storefront handoff

## LIVE

- Production URL: https://storefront-omega-three.vercel.app
- Deployment: `dpl_6T2YKTQZv9oywZj596hsyHT9uMQy` (`READY`, production)
- Git repo/path: `/Users/aradhyamishra/zero-human-dropship-master/storefront`

## WORKING

- 10 active, real Stripe products and prices synced from live Stripe state.
- 10 existing Payment Links reused without duplicates; each link is active, contains exactly its selected product/price, and has Stripe shipping-address collection enabled for the US.
- Real catalog is served from `/api/catalog` and stored in `catalog.json`; neither contains secrets.
- Product pages link directly to the matching secure Stripe checkout. Demo products, fixture prices, and fixture imagery are not presented as real.
- Linq CTA reads `NEXT_PUBLIC_LINQ_PHONE` or `NEXT_PUBLIC_SALES_AGENT_URL` and remains disabled until one is configured.
- Shipping and returns disclosures are available at `/shipping` and `/returns`.
- Terac study `w14sbyed2iixiz76o5ass608` fulfilled with 10 approved responses. The catalog is deterministically reordered from the approved-response ranking; no commerce values changed.
- Public evidence feeds are live at `/api/terac-feedback` and `/api/ceo-decisions`.

## VERIFIED

- Stripe API: 10/10 selected Payment Links are active, exact one-product/one-price matches, and set `shipping_address_collection.allowed_countries` to `["US"]`.
- Deployed browser: mobile homepage → Laptop Cooling Pad with Fan → its live Stripe Checkout; the checkout visibly rendered email, full name, US country, address, city, ZIP, state, and payment sections. No payment was submitted.
- QA: production build; Biome; TypeScript; 36/36 tests; no mobile overflow at 390 px; storefront console 0 errors; `/`, `/products`, product, `/api/catalog`, `/shipping`, and `/returns` return HTTP 200.
- Security: `.env.local` is git-ignored with mode 0600; source scan found no live key value; `/api/catalog` exposes only the approved safe fields.
- Terac deployment: 43/43 tests, production build, prerendered header, mobile QA at 390×844, zero production console errors, 10 active products, 10 distinct real Payment Links, and HTTP 200 for both evidence feeds.

## CATALOG SYNC

Canonical catalog: `/Users/aradhyamishra/zero-human-dropship-master/storefront/catalog.json`

Safe API: `https://storefront-omega-three.vercel.app/api/catalog`

Re-sync after a Stripe catalog change with `bun scripts/sync-stripe-catalog.ts --apply`, using server-only `STRIPE_SECRET_KEY`.

## NEED FROM OPERATOR

- Rotate the live Stripe key that was pasted into chat, then replace `STRIPE_SECRET_KEY` in Vercel.
- Configure `SUPPORT_EMAIL`.
- Linq worker: configure `NEXT_PUBLIC_LINQ_PHONE` and/or `NEXT_PUBLIC_SALES_AGENT_URL`, then redeploy.

The 10 Stripe products currently have no uploaded images; add real product images in Stripe and re-sync when available.
