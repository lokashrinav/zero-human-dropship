# Replay QA Results

Evidence is limited to real Replay QA runs against the two production applications. Existing local browser and test-suite checks are listed only as regression evidence, not as a substitute for Replay.

## Storefront

- Production target: <https://storefront-omega-three.vercel.app/>
- Replay project: `proj-storefront-omega-three-vercel-app-msuth5fn`
- First report: <https://qa.replay.io/projects/proj-storefront-omega-three-vercel-app-msuth5fn/test-runs/ts-msuth5wx-cql5>
- First run ID: `ts-msuth5wx-cql5`
- First run started: 2026-08-15 13:16:50 PDT
- First exploration result before fixes: 15 journeys and 9 findings

### First-run triage

P0: none.

P1:

1. **[Search input lacked an accessible name (WCAG 3.3.2)](https://qa.replay.io/projects/proj-storefront-omega-three-vercel-app-msuth5fn/bugs/bug-msutm4ww-b42e).**
2. **[Hero content was clipped at the 1280 x 720 Replay viewport / resized-text condition (WCAG 1.4.4)](https://qa.replay.io/projects/proj-storefront-omega-three-vercel-app-msuth5fn/bugs/bug-msutodvk-0f5e).**
3. **[Product sort links all resolved to `/products` without the selected sort query, so sorting did not apply in Replay's browser](https://qa.replay.io/projects/proj-storefront-omega-three-vercel-app-msuth5fn/bugs/bug-msutxvld-cev5).**

P2 (not fixed, per scope):

1. Hero checkout badge visually overlapped the product label.
2. Search prefetch produced successful duplicate requests while typing; no failed request or broken search was shown.
3. Footer copyright contrast was reported at 3.15:1.
4. Footer shipping/returns disclaimer contrast was reported at 3.77:1.
5. Links to `/products` used differing accessible names.
6. Links to the same product used differing accessible names.

### P1 fixes

1. **Accessible search name**
   - Root cause: both desktop search variants relied on placeholder text alone.
   - Fix: added `aria-label="Search products"` to both search inputs in `storefront/components/search/search-input.tsx`.
   - Verification: production exposes the header input as a `Search products` combobox; the post-fix Replay exploration did not re-file the defect.
2. **Hero clipping**
   - Root cause: the large-screen hero's absolutely positioned content extended beyond an `overflow-hidden` section.
   - Fix: added 48 px of large-screen bottom padding (`lg:pb-12`) in `storefront/components/sections/hero.tsx`.
   - Verification: at 1280 x 720 production measured `clientHeight=720`, `scrollHeight=720`, `paddingBottom=48`; the post-fix Replay exploration did not re-file the defect.
3. **Sort links**
   - Root cause: `buildSortHref` depended on `URLSearchParams.size`, which was unavailable in Replay's browser runtime, so it fell back to the bare pathname.
   - Fix: serialize with `params.toString()` and test the serialized string in `storefront/app/products/products-sort-select.tsx`.
   - Verification: production exposes `/products?sort=price-asc`; Replay's focused post-fix sort/reordering journey completed without a new bug.

### Regression and deployment

- Biome: PASS, 156 files checked.
- TypeScript: PASS (`tsc --noEmit`).
- Tests: PASS, 43 passed / 0 failed across 11 files (74 expectations).
- Production build: PASS, Next.js 16.3 build completed with 28 static pages.
- Production deployment: `dpl_5pQuWgmj5zG1tH2gk9P6UzctgmDS` (`READY`).
- Vercel inspection: <https://vercel.com/vendraft/storefront/5pQuWgmj5zG1tH2gk9P6UzctgmDS>
- Required production alias preserved: <https://storefront-omega-three.vercel.app/>
- Catalog/checkout preservation smoke: 10 product-detail links and a real Stripe Payment Link were present; checkout was not submitted and no charge was made.

### Post-fix Replay pass

- Clean-project target: <https://storefront-omega-three.vercel.app/>
- Replay project: `proj-storefront-omega-three-vercel-app-msuw7auy`
- Final report: <https://qa.replay.io/projects/proj-storefront-omega-three-vercel-app-msuw7auy/test-runs/ts-msuwfk1b-qn6i>
- Final run ID: `ts-msuwfk1b-qn6i`
- Started: 2026-08-15 14:39:34 PDT
- Final Replay state: **Completed — 4 journeys, 2 findings, no P0/P1.**
- Passed: homepage hero at 1280 x 720 / CTA / cart; search filtering and clearing.
- Product-detail / Stripe initiation journey: no broken checkout finding and no payment submitted.
- Replay QA incomplete: sort/reordering journey. This was a Replay QA execution failure, not an app bug; the earlier post-fix Replay sort journey completed without re-filing the broken-query defect, and production exposes `/products?sort=price-asc`.
- P2 only: native GET search causes a redundant full-page navigation; the `/search` sort select navigates immediately on change without prior warning.
- Material verdict: **CLEAN — no P0/P1 remained.**

The original project accepted a post-fix exploration before its initial run envelope finalized and later suffered stuck Replay run instances. Its current aggregate totals therefore mix baseline and post-fix evidence; the preserved 15-journey / 9-finding snapshot above is the true pre-fix baseline. The separate clean project and report are the final post-fix evidence.

## Dashboard

- Production target: <https://zero-human-control-room.vercel.app/>
- Replay project: `proj-zero-human-control-room-vercel-app-msuwwep3`
- Report: <https://qa.replay.io/projects/proj-zero-human-control-room-vercel-app-msuwwep3/test-runs/ts-msuwwf79-zzu4>
- Run ID: `ts-msuwwf79-zzu4`
- Started: 2026-08-15 14:52:41 PDT
- Final Replay state: **Completed — 5 journeys, 7 findings, no P0/P1.**
- Passed: dashboard loads and renders live autonomous-commerce metrics; page sizing and scroll behavior.
- Main/mobile journeys filed only P2 contrast findings.
- Replay QA failure: generic search/filtering detail journey; the dashboard has no search workflow, so this was inapplicable rather than a broken dashboard interaction.
- P2 findings: low contrast on `CONTROL ROOM`, `UPDATED`, `REAL REVENUE`, and `LIVE` labels; medium contrast notes on two eyebrow labels; one false-positive clipping report.
- Clipping false-positive verification: at a 390 px production viewport the panel reported `clientHeight=739` and `scrollHeight=785` because rotated arrow graphics extend the scroll box, but visual inspection confirmed that all workflow text—including `CLOSE THE LOOP` and `EVERY SIGNAL BECOMES THE NEXT DECISION`—is visible.
- Dashboard fixes/deploy: none required; production code and project were not changed.
- Material verdict: **CLEAN — no P0/P1 found.**

## Safe sponsor handoff

The dashboard may display **`Replay — VERIFIED`**. Safe proof is Replay project `proj-zero-human-control-room-vercel-app-msuwwep3`, run `ts-msuwwf79-zzu4`, and the report URL above. This status means the actual Replay run completed with no material P0/P1; it does not claim that Replay filed zero P2 polish findings.
