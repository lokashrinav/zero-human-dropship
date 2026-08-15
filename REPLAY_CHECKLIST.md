# Replay QA Checklist — Autonomous Company Dashboard

## Test target

- Stable dashboard route: `/`
- Production target: use the dashboard URL recorded in `HANDOFF.md`.
- Local target: use the URL printed by the dashboard's development server.
- Run this checklist against the **dashboard**, not the storefront or the agent backend.

Automated smoke check from `dashboard/`:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

To exercise an already running or deployed build without starting a local server:

```bash
PLAYWRIGHT_BASE_URL=https://your-dashboard.example npm run test:e2e
```

## P0 — 60-second judge path

- [ ] Open `/` directly in a clean browser session; no login, seed step, or prior local storage is required.
- [ ] Confirm the first viewport clearly says `AUTONOMOUS COMPANY — LIVE`.
- [ ] Confirm all five metric labels are visible: `REAL REVENUE`, `ORDERS`, `PRODUCTS LIVE`, `CUSTOMER CONVERSATIONS`, and `AUTONOMOUS DECISIONS`.
- [ ] Confirm revenue never displays a fixture dollar amount as real revenue. Without a live feed it must say `Waiting for live Stripe feed` or another unambiguous pending state.
- [ ] Confirm fixture-backed sections display a visible `DEMO DATA` or `MOCK` label.
- [ ] Confirm the autonomous loop is understandable in order: `SOURCE → VALIDATE WITH HUMANS → LIST → SELL → FULFILL → LEARN ↺`.
- [ ] Confirm the active loop stage is visually distinguishable and is also conveyed by text or an accessible state, not color alone.
- [ ] Confirm the CEO decision feed separates `Reason`, `Action`, and `Outcome`; an outcome is omitted when the source did not provide one.
- [ ] Confirm the Terac section distinctly shows `BEFORE HUMAN FEEDBACK`, `TERAC FEEDBACK`, `AUTONOMOUS CHANGE`, and `AFTER`.
- [ ] Confirm the Linq flow reads `INBOUND → DECISION → OUTBOUND` and safely handles an absent phone number.
- [ ] Confirm every sponsor chip is either truthfully active/verified or visibly `PENDING`; unavailable sponsors must never appear verified.

## Integration and failure isolation

Run each case independently. A failure in one integration must degrade only that panel while the rest of the dashboard remains usable.

- [ ] Baseline fixture mode: run with no live endpoint environment variables. Dashboard renders fully; non-live data is labeled.
- [ ] Stripe unavailable: configure an unreachable revenue endpoint. Revenue panel shows pending/degraded, no dollar amount, and no unhandled exception.
- [ ] Linq unavailable: configure unreachable status/events endpoints. Linq panel shows fixture or offline/degraded state; other panels still update.
- [ ] Terac unavailable: configure an unreachable Terac endpoint. Before/after panel shows clearly labeled fixture/pending state.
- [ ] Decisions unavailable: configure an unreachable CEO decisions endpoint. Feed shows a bounded empty/degraded state instead of disappearing or crashing.
- [ ] Catalog unavailable or malformed: products metric/catalog panel shows unavailable/degraded and the page remains rendered.
- [ ] HTTP 500: intercept one endpoint and return status `500`; only its panel changes state.
- [ ] Slow response: delay one endpoint for at least 10 seconds; a loading state appears without blocking the page.
- [ ] Invalid JSON: return malformed JSON from one endpoint; the page remains rendered and reports a degraded state.
- [ ] Recovery: restore a failed endpoint. After the next polling interval the panel recovers without a full-page reload.
- [ ] Stale feed: stop responses after one successful poll. `LIVE`/freshness styling changes to stale/degraded rather than continuing to claim fresh data forever.

## Live event demo

- [ ] With Linq live, send one inbound message to the safe/public demo number.
- [ ] Within the configured polling interval, a new inbound event appears without refreshing the page.
- [ ] Subsequent agent decision, product selection/recommendation, and payment-link events appear in chronological order.
- [ ] Duplicate event IDs are not rendered twice across polling cycles.
- [ ] The active autonomous-loop stage follows the newest event when stage data is present.
- [ ] New activity is noticeable but motion does not prevent reading.
- [ ] Payment links are displayed safely; no Stripe secret/restricted key or private token is present in HTML, page source, console, or network request headers.

## Semantics and accessibility

- [ ] The document has one descriptive `h1` and a logical heading hierarchy.
- [ ] Status is expressed in visible text; important status changes use an appropriate live region where supported.
- [ ] All interactive controls are native `<button>` or `<a>` elements with accessible names.
- [ ] Any refresh/retry control is keyboard reachable and clearly labeled (for example, `Retry Linq feed`, not `Click here`).
- [ ] Focus indicators are visible against the dark background.
- [ ] Metrics use text labels rather than relying on icons or hover tooltips.
- [ ] Decorative animation respects `prefers-reduced-motion`.
- [ ] Text and status indicators remain legible at 200% browser zoom.

## Responsive projection and phone checks

Test at these viewports:

- [ ] `1440 × 900` — hero, metric row, loop, and current activity are projection-readable without horizontal scrolling.
- [ ] `1280 × 720` — primary demo story remains above or near the fold; no clipped panels.
- [ ] `390 × 844` — panels stack in narrative order, metrics remain readable, and no horizontal scrolling occurs.
- [ ] `320 × 568` — no text overlaps, controls remain tappable, and event content wraps safely.
- [ ] At every size, long product names, reasons, URLs, and phone/status text wrap without expanding the viewport.

## Browser health

- [ ] Hard-refresh `/`; there are no uncaught exceptions, hydration errors, missing-key warnings, or failed asset loads in the console.
- [ ] Network failures from intentionally unavailable integrations are handled and do not create an unbounded error loop.
- [ ] Polling stops or pauses when the page is no longer active/unmounted, and does not multiply after route changes or React development remounts.
- [ ] No browser request contains server-only credentials such as `STRIPE_SECRET_KEY`.
- [ ] Loading and error messages are concise and do not cause large layout shifts.
- [ ] Refresh the deployed URL directly; hosting returns the dashboard rather than a 404.

## Replay evidence to capture

- [ ] Screenshot: clean first viewport at `1440 × 900`.
- [ ] Screenshot: one integration degraded while the rest of the dashboard remains healthy.
- [ ] Screenshot or short recording: Linq inbound → decision → outbound sequence.
- [ ] Screenshot: mobile layout at `390 × 844`.
- [ ] Export/record the browser console showing zero unexpected errors during the main judge path.
- [ ] Record the UTC/local timestamp, build identifier, dashboard URL, and which integrations were live versus fixture-backed.

## Pass criteria

Replay QA passes when the P0 judge path is immediately understandable, revenue provenance is truthful, fixture data is unmistakably labeled, each integration fails independently, the live event flow can update without a refresh, all primary controls are semantic and keyboard usable, and the main path produces no unexpected browser-console errors.
