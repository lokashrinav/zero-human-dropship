# Agent Operating Manual (Codex / Claude — any agent runtime)

This file is the entry point for ANY coding agent (Codex reads AGENTS.md; Claude Code also loads CLAUDE.md — same rules). The company is live: read this, then act.

## What this is
Autonomous dropshipping business (Zero Human Company Hackathon, Aug 15 2026). Real Stripe revenue, real products, agents run everything. Humans only relay credentials and watch.

## Boot (fresh machine)
1. `git clone https://github.com/lokashrinav/zero-human-dropship && cd zero-human-dropship`
2. `pip install -r agent_backend/requirements.txt`
3. Get `agent_backend/.env` from a teammate over a PRIVATE channel (iMessage/AirDrop — NEVER commit it; this repo is public with push-protection on). Minimum to operate: `STRIPE_SECRET_KEY`. Extras: `LINQ_API_KEY`, `SOLARI_API_KEY`, `PIONEER_API_KEY`, `TERAC_API_KEY`, `SUPERSERVE_API_KEY`.
4. Sanity check: `cd agent_backend && python -m agents.cli observe` → prints live catalog + sales.

## Current live state (as of ~3:00 PM PT)
- **Storefront** (KOVA): https://storefront-omega-three.vercel.app — 10 products, panel-calibrated prices synced. Product images attached in Stripe; appear after next `storefront/scripts/sync-stripe-catalog.ts` run.
- **Dashboard**: https://zero-human-control-room.vercel.app
- **Backend + public decision feed**: cloudflare tunnel `https://without-thinks-harvest-huge.trycloudflare.com` (`/api/products`, `/api/decisions`, `/api/stats`, POST `/api/log`). Ephemeral — if dead, whoever runs the backend machine restarts it and re-shares the URL.
- **FB Marketplace**: 10/10 listings live.
- **Terac**: study complete (n=10) → catalog reorder + 3 reprices, all cited on the decision feed. `request_human_task()` available for agent-blocked steps.
- **Fulfillment**: `fulfillment/pipeline.py` (Stripe→CJ daemon, CJ auth works). Run `match` once to build `product_map.json`. Unfulfillable orders → `manual_orders.log`.

## Lanes — who owns what (do not cross without coordinating)
| Lane | Owner | Scope |
|------|-------|-------|
| **CEO** (Stripe catalog mutations: reprice/drop/source) | Shrinav's machine, ONE session, loop already running | `agents/cli.py observe/act` through guardrails |
| **Growth/FB + fulfillment daemon** | revenue-sprint session (Shrinav's machine) | FB posts, `fulfillment/pipeline.py`, tracked links |
| **Storefront + dashboard + Linq deploy** | Teammate (Mac) | conversion optimization, catalog sync, `linq_agent/` deploy, Vercel envs |

**Hard rule: exactly ONE CEO session at a time.** Everyone else proposes catalog changes by logging to the decision feed (`python agent_backend/log_decision.py <Agent> "<proposal>"` locally, or `POST <tunnel>/api/log` with `{"agent": "...", "message": "..."}` from other machines). The CEO acts on proposals next cycle.

## Revenue levers ranked (teammate optimization targets)
1. **Linq inbound agent deploy** (`linq_agent/`) — storefront's "Text our AI shopping agent" section is a dead placeholder; number +1 415-305-0091 verified. Deploy on Render → $2,500 Linq + $900 Render tracks + a live sales channel.
2. **Storefront catalog re-sync** — picks up product images (attached in Stripe, biggest conversion fix) — then update FB listing prices for Cooling Pad ($10.99) and Earbuds ($9.49).
3. **Conversion polish**: trust signals near Buy buttons, Terac "panel-approved" badges (real data in `terac/aggregated_feedback.json`), mobile checkout friction.
4. **Bundles**: create multi-SKU Stripe products at higher AOV (propose to CEO or coordinate — creates catalog entries).
5. **Replay QA** on the storefront (checklist in `REPLAY_CHECKLIST.md`) — $1,500 track, fix what it finds.

## Guardrails (enforced in code — don't fight them)
Reprice/drop go through `agents/cli.py act`: min price 250c, ≥30% margin over cost, ≤35% price change per cycle, ≤3 actions per cycle, never drop the last/selling product. Old payment links stay ACTIVE on reprice (storefront serves a baked catalog — deactivating would dead-link live traffic). Full decision rules in `CLAUDE.md`.

## Context from the other operating sessions
- `HANDOFF.md` — teammate's dashboard/storefront handoff (verified production state, integration contracts)
- `OPERATIONS_HANDOFF.md` — revenue-sprint session's operational brain-dump (FB state, daemon, watchers) — if missing, ask that session to write it
- Decision feed (`/api/decisions`) — the full timestamped history of every agent decision
