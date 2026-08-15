# Zero Human Hackathon — Autonomous Dropshipping Business

## Context
Hackathon: August 15, 2026, 10:45 AM – 6:45 PM (8 hours, selling window ~4 hrs). Two people, each running a Claude Code agent in parallel. Hackathon tracks revenue via Stripe restricted API key. Must use Terac MCP.

## Hard Truths That Shape This Plan

1. **Only Stripe revenue counts.** eBay/Mercari/Etsy/FB Marketplace process payments through their OWN systems. That revenue is invisible to hackathon organizers. The only channels that feed our Stripe: **our own store, Stripe Payment Links, and Linq iMessage.**

2. **A brand-new store has zero traffic.** No SEO, no reviews, no followers. We must DRIVE traffic to Stripe checkout — it won't come organically.

3. **Physical products from unknown stores are a hard sell in 4 hours.** Realistic target: $10-50 from impulse buys ($5-15 items) pushed through personal networks + marketplace traffic funneled to Stripe.

4. **The demo matters more than the dollar amount.** Judges want to see autonomous agents running a real business. $15 in genuine autonomous revenue + a visibly self-running agent system beats $0 with a perfect store.

## The Business Model

```
1. SOURCE    Agent calls CJDropshipping API → finds trending product at $4 (no browser needed)
2. CREATE    Agent creates Stripe Product (name, images, price $12) → auto-appears on store
3. LIST      Agent uses claude-in-chrome to post on FB Marketplace with link to our store
4. MARKET    Agent generates FLUX ad image + Kling video → pushes via Linq iMessage
5. SELL      Customer lands on our store OR gets Stripe Payment Link → pays via Stripe ✓
6. FULFILL   Agent calls CJDropshipping order API with customer's address
7. ITERATE   Terac feedback + Stripe data → agents swap products, reprice, shift channels
```

## Revenue Channels — Honest Assessment

| Channel | Payment through OUR Stripe? | Role | Priority |
|---------|:--:|------|:--:|
| **Our store (Your Next Store)** | ✅ Yes | Primary storefront. Stripe Checkout built-in. | **#1** |
| **Stripe Payment Links** | ✅ Yes | Universal checkout. Share on any platform. | **#1** |
| **Linq iMessage** | ✅ Yes (via payment link) | Conversational sales. Agent sends product + link. | **#2** |
| **FB Marketplace** | ❌ No (FB Pay) | **Traffic source only.** List products → link to our store/Stripe link in description. Organic local browsers click through. | **#3** |
| **eBay** | ❌ No (Managed Payments) | **Demo only.** Shows agents can list on major platforms. Revenue doesn't count for hackathon. | **#4** |
| **Mercari / Etsy** | ❌ No | Demo only. | **#5** |

**Revenue strategy: Your Next Store + Stripe Payment Links are THE revenue engine. Everything else is traffic or demo.**

## Prize Tracks — Targeting All ($11,400 possible)
| Track | Prize | How |
|-------|-------|-----|
| Best Overall Project | $2,500 | Multi-agent autonomous dropshipping business |
| Best Agent-Run Company | $2,500 | Real Stripe revenue, fully autonomous agents making business decisions |
| Best use of Linq | $1,500+$1,000 | iMessage as primary sales channel, interactive App cards |
| Best use of Replay | $1,000+$500 | Run QA on store → fix bugs → show clean report to judges |
| Best use of Superserve | $1,000+$500 | CEO loop + fulfillment agent run inside Superserve sandboxes |
| Best use of Band | $500 | CEO dispatches, agents report, full decision audit trail |
| Best use of Pioneer | $500 | Pioneer-hosted open-weight model generates product descriptions |
| Best use of Render | $500+$300+$100 | Linq webhook handler + store deployed via Render Workflows |

## How We Actually Get Sales

1. **FB Marketplace as traffic funnel** — List trending products. Include "Order online: [our store link]" or Stripe Payment Link in description. FB Marketplace has organic local browsers. When someone messages "Is this available?" → agent responds with Stripe Payment Link.

2. **Linq iMessage inbound** — Advertise iMessage number on store + FB listings ("Text us for deals"). When someone texts, Sales agent responds with product recs + Stripe Payment Link. No cold messaging allowed.

3. **Social sharing** — Stripe Payment Links shared in group chats, Discord servers, Reddit. FLUX-generated ad creatives make these shareable.

4. **Our store** — Your Next Store looks professional. Products auto-appear from Stripe. Send traffic here from everywhere else.

5. **Price for impulse** — $5-12 range. Trending items people want but don't need to think about. The payment link makes checkout 2 clicks.

## Exactly What We Build

### Component 1: Product Pipeline (Person A)
**Purpose**: Source products → create Stripe products → they auto-appear on store

- **CJDropshipping API** for sourcing (NO browser needed) — search products, get images/descriptions/prices
- Call Stripe API: create Product + Price (with markup) + Payment Link
- Products auto-appear on Your Next Store (zero manual step)
- Store product data in simple JSON for other agents to reference

**Code**: Python script. CJ API (`/product/list`, `/product/query`). Stripe SDK (`stripe.Product.create`, `stripe.Price.create`, `stripe.PaymentLink.create`).

### Component 2: Storefront (Person B)
**Purpose**: Professional-looking store that converts visitors to Stripe payments

- One store. Fork yournextstore.com → deploy on Vercel (one-click)
- Products pull from Stripe Dashboard automatically
- Customize: brand name, colors, logo (FLUX-generated)
- Mobile-first (it already is out of the box)
- Must verify Stripe Checkout collects shipping address (needed for CJ fulfillment)

**Code**: Almost zero — it's a fork + env vars. Customization is config-level.

### Component 3: Agent Backend (Person A)
**Purpose**: The brain. All agent loops run here.

FastAPI service deployed on Render. Claude API for reasoning. Tool functions for external services.

```
agent_backend/
├── main.py              # FastAPI app, routes, Stripe webhooks
├── agents/
│   ├── ceo.py           # Decision loop: read Stripe + Terac → decide → dispatch
│   ├── sourcing.py      # CJ API → create Stripe products
│   └── ops.py           # Order tracking, fulfillment forwarding
├── tools/
│   ├── stripe_tools.py  # Create/update/delete products, read charges, create payment links
│   ├── terac_tools.py   # Launch study, read results
│   ├── band_tools.py    # Post decisions, read room
│   ├── replicate_tools.py # FLUX image gen, Kling video gen
│   └── cj_tools.py      # CJDropshipping product search + order placement
└── render.yaml          # Deployment config
```

CEO loop runs every 15 min:
1. Read Stripe charges (what sold, what didn't)
2. Read Terac study results (if available)
3. Read Band room (agent status updates)
4. Claude API call with all context → output = decision + action
5. Execute: drop product, source new one, reprice, shift marketing focus
6. Post decision + reasoning to Band

### Component 4: Marketplace Listing Agent (Person B)
**Purpose**: Post products on FB Marketplace (traffic funnel) + eBay (demo)

- **claude-in-chrome** (one browser, shared) for FB Marketplace + eBay listing
- FB Marketplace: create listing with images + description + our store link
- eBay: create Buy It Now listing (for demo, revenue goes through eBay not our Stripe)
- Browser tasks run sequentially (one Chrome browser)
- Agent reads product catalog → posts each product → reports to Band

**Code**: Claude Code subagent using claude-in-chrome MCP tools (navigate, form_input, computer, file_upload). No separate browser SDK needed.

### Component 5: Sales & Marketing (Person B)
**Purpose**: Drive traffic to Stripe checkout. Close sales via iMessage.

- **Linq Sales Agent** (inbound only): webhook receives inbound iMessage → Claude processes → responds with product recommendation + Stripe Payment Link. No cold outbound messaging.
- **iMessage App cards**: interactive product showcase in iMessage (Linq feature)
- Drive inbound traffic to the number via store banner + FB Marketplace descriptions ("Text us: [number]")

**Code**: Person B builds this as a separate small FastAPI service on Render. Claude API for conversation. Linq SDK for send/receive. Reads `catalog.json` for product data + payment links.

### Component 6: Content Generation (Person A)
**Purpose**: Marketing creatives that make products shareable

- **FLUX 1.1 Pro** (via Replicate): lifestyle product images, ad creatives, store banners
- **Kling 2.0 / Minimax** (via Replicate): 5-second product showcase videos
- Generated content used in: store pages, FB Marketplace listings, social sharing

**Code**: Replicate SDK calls. Integrated into agent backend.

### Component 7: Coordination & Feedback (Both)
**Purpose**: Agent decision trail (for judges) + human feedback loop (for Terac)

- **Band**: room where all agents post. CEO decisions are the star — timestamped, with reasoning.
- **Terac**: 3 studies launched at intervals. Results feed back into agent decisions.

### Component 8: Demo Dashboard (Person B)
**Purpose**: Show judges the autonomous business in action

- Real-time Stripe revenue counter
- Agent decision timeline (pulled from Band)
- Terac before/after gallery (product v1 vs v2)
- Active listings across channels
- Could be: simple HTML page polling APIs, or Lovable-built (use the free credits here)

---

## Terac Integration (Required — The Before/After Story)

### Study 1: "Would You Buy This?" (launch ASAP — ~12:30 PM)
- Show 10 sourced products to General Population. "Rate 1-5. Would you buy?"
- **Before**: 10 agent-curated products, unvalidated
- **After**: Bottom 4 killed. Sourcing agent finds replacements matching top-rated attributes.
- **Feed into**: Sourcing agent + CEO decision log

### Study 2: "How Much Would You Pay?" (~2:00 PM)
- Show top 5 products at 3 price points each. "Which price would you buy at?"
- **Before**: Uniform 2.5x markup
- **After**: Per-product optimal pricing
- **Feed into**: CEO reprices all Stripe products + payment links

### Study 3: "Rate Our Store" (~3:30 PM)
- Send panelists to live store. "Would you buy? What's confusing?"
- **Before**: AI-written product descriptions
- **After**: Rewritten descriptions, reordered products
- **Feed into**: Growth agent updates store copy

**Launch Study 1 as EARLY as possible** — results take ~1 hour. Earlier launch = earlier iteration.

---

## Autonomous Decision Playbook

| Decision | Trigger | Agent | Example |
|----------|---------|-------|---------|
| Drop product | 0 views/clicks after 1hr | CEO | "Removing USB fan — zero traction" |
| Source replacement | Product dropped or Terac-rated <3/5 | Sourcing | "CJ API search: phone stands (replacing USB fan)" |
| Reprice | Terac price data or zero sales at current price | CEO | "Earbuds $20→$12 — Terac says max willingness is $13" |
| Shift channel focus | One channel has 3x engagement | CEO | "FB Marketplace driving 80% of store visits. Doubling listings there." |
| Generate ad creative | New product added | Growth | "FLUX lifestyle image for phone stand → FB Marketplace + store" |
| Generate video | High-margin product | Growth | "Kling 5s showcase → embed in iMessage" |
| A/B test copy | Sales stall on a product | Growth | "Testing 'TikTok Trending' vs 'Best Seller' headline" |
| Cross-list | Product selling on one channel | Growth | "Phone stand selling via store — listing on FB Marketplace too" |

Each decision logged in Band with: **timestamp + reasoning + outcome**. This is the audit trail judges will see.

---

## Two-Person Build Split

One machine, one Chrome browser, two Claude Code terminals. Split by what each person **builds**, not what business role they play. No file conflicts — each person owns separate code/repos.

### Person A: Backend codebase (`agent_backend/`)
Writes ALL the Python backend — agents, tools, API integrations. No browser needed. Pure coding.

**Builds (in order):**
1. FastAPI skeleton + `render.yaml` → deploy empty service on Render
2. `tools/stripe_tools.py` — create Product, Price, PaymentLink; read charges; update prices
3. `tools/cj_tools.py` — CJ API product search, image download, order placement
4. Product sourcing pipeline: CJ API → pick products → Stripe creation → output `catalog.json`
5. `tools/band_tools.py` — post message, read room
6. `tools/terac_tools.py` — create study, read results
7. `tools/replicate_tools.py` — FLUX image gen, Kling video gen
8. `agents/ceo.py` — decision loop (read Stripe + Terac + Band → Claude API → action)
9. `agents/sourcing.py` — receives directive → CJ search → new Stripe product
10. `agents/ops.py` — Stripe webhook `payment_intent.succeeded` → log → CJ order API
11. Superserve: wrap CEO + ops agent in sandboxed execution
12. Pioneer: open-weight model for product descriptions

**Signups (Phase 0):** Stripe, CJDropshipping, Replicate, Superserve + hackathon code, Pioneer

**Unblocks Person B at 12:00 PM** with `catalog.json` containing product names, images, Stripe IDs, payment link URLs.

### Person B: Storefront + channels + browser + dashboard
Everything customer-facing. Owns the Chrome browser. No file overlap with `agent_backend/`.

**Builds (in order):**
1. Fork yournextstore.com → customize brand/colors → deploy on Vercel
2. Linq webhook handler (separate small FastAPI service on Render) — inbound iMessage → Claude API → responds with product rec + payment link. Can build + test with dummy products before 12:00
3. ⏳ While waiting for A's products: set up Band room + register agent names, configure Linq webhook URL, set up Replay account
4. **12:00 PM — products land.** Plug real payment links into Linq handler. Verify products appear on store. Test Stripe Checkout end-to-end.
5. Browser (claude-in-chrome): FB Marketplace listings — each product with images + "Order here: [store URL]"
6. Advertise Linq iMessage number on store + FB listings ("Text us for deals")
7. iMessage App cards for interactive product showcase
8. Browser (claude-in-chrome): eBay Buy It Now listings (demo only)
9. Browser: Replay QA on store → fix what it finds → screenshot clean report
10. Demo dashboard: Lovable (free credits) or hand-coded HTML — revenue counter, decision timeline, Terac before/after

**Signups (Phase 0):** Vercel, Linq sandbox + phone number, Band + code HACKBANDAUG26, Render credits, Replay, Terac

**Launches Terac Study #3** at ~3:30 (store UX feedback). Person A launches Studies #1 and #2.

### Why this split works
| | Person A | Person B |
|---|---------|---------|
| **Writes code in** | `agent_backend/` (one repo) | Store fork (separate repo) + Linq webhook (separate service) + dashboard |
| **Deploys on** | Render (agent backend) | Vercel (store) + Render (Linq webhook) |
| **Uses browser?** | Never | All browser tasks |
| **Heaviest work** | Agent logic + 6 API integrations | Linq webhook + store deploy + FB/eBay listing |
| **Blocked on other?** | Never | Partially until 12:00 (needs products), but Linq handler + store customization fill the wait |
| **Can test alone?** | Yes — run sourcing pipeline, verify Stripe products appear | Yes — Linq handler testable with dummy data before 12:00 |

### Integration points
1. `catalog.json` — Person A writes at 12:00 PM, Person B reads. Format:
```json
[{"name": "...", "images": ["url1"], "stripe_id": "prod_xxx", "payment_link": "https://buy.stripe.com/xxx", "cost": 4.50, "price": 12.00}]
```
2. **Stripe** syncs automatically — A creates products, B's store reflects them. No code needed.
3. **Band** — both post status updates. A: CEO decisions. B: sales/listing updates. Both read.
4. **FLUX/Kling creatives** — A generates via Replicate, saves URLs. B uses in FB Marketplace updates + store.

---

## Timeline — Revenue-First

### Phase 0: Setup (10:45 – 11:15, 30 min)
**A**: Stripe `rk_` key → submit. Superserve signup + code ZEROHUMANHACK-SWSYP3XJ. CJDropshipping API registration. Replicate signup.
**B**: Fork Your Next Store → deploy on Vercel. Linq sandbox. Band + HACKBANDAUG26. Render credits. Terac signup.
**Both**: API keys into shared `.env`.

### Phase 1: Products Live + Store Live (11:15 – 1:15, 2 hrs)
**Goal: ≥10 products on our store + FB Marketplace. Stripe checkout working. First Terac study launched.**

**A** (sourcing + products):
- CJDropshipping API → search trending impulse-buy products ($3-8 supplier, sell $8-15)
- Target: phone accessories, desk gadgets, LED novelties, trending TikTok items
- Download images, write compelling descriptions (Claude)
- Create Stripe Products + Payment Links for each
- Products auto-appear on B's store
- Launch **Terac Study #1** at ~12:30 with first batch of products
- Start agent backend skeleton on Render

**B** (store + channels):
- Customize Your Next Store (brand, colors)
- Verify products appear on store from Stripe
- Browser-automate FB Marketplace listings: each product with "Order here: [store link]" 
- Set up Linq Sales agent: inbound webhook → Claude → product rec + payment link
- Test: visit store → select product → Stripe Checkout → payment succeeds

**12:00 Checkpoint**: A has ≥5 Stripe Products. B's store shows them. Test purchase works.

### Phase 2: Agent Autonomy + Marketing (1:15 – 3:15, 2 hrs)
**Goal: Agents running autonomously. Marketing pushing. Terac results flowing in.**

**A** (agent system):
- Band room: register all agents, start decision log
- CEO loop: every 15 min reads Stripe charges + Terac results → makes decision → dispatches
- Sourcing agent: receives CEO directive → CJ API search → creates new Stripe product
- Ops agent: Stripe webhook on payment → log order → CJ order API
- Process **Terac Study #1 results** → feed to CEO → agent drops/replaces products
- Launch **Terac Study #2** (pricing) at ~2:00
- Generate FLUX ad creatives + Kling product videos

**B** (marketing + sales):
- Growth agent: iMessage campaigns via Linq — product images + Stripe Payment Links
- Sales agent live: handles inbound Linq conversations
- eBay listings via browser (for demo breadth)
- iMessage App cards for interactive showcase
- Update FB Marketplace listings with FLUX-generated creatives
- Start demo dashboard

**2:00 Checkpoint**: Full autonomous loop works. CEO makes a visible decision in Band. At least one marketing campaign sent via Linq.

### Phase 3: Sell + Iterate (3:15 – 5:45, 2.5 hrs)
- Agents run without human intervention
- Marketing blitz: fresh FB Marketplace posts, social sharing, respond to all inbound Linq messages
- CEO iterates: Terac → reprice → swap products → shift channel focus
- Sourcing agent finds new products matching what's working
- Growth agent generates new creatives + videos for top sellers
- **Terac Study #3** (~3:30): store UX → agents adjust copy
- Track revenue in Stripe

### Phase 4: Polish + Submit (5:45 – 6:45, 1 hr)
- **A**: Clean Band decision logs — impressive audit trail
- **B**: Demo dashboard finalized (revenue, decisions, Terac before/after)
- **Both**: Demo script, rehearse pitch, submit by 6:45

---

## Demo Flow for Judges
1. "We built an autonomous dropshipping business. After setup, zero humans touched it."
2. Live agent demo: show Sourcing agent calling CJDropshipping API, finding a product, creating it in Stripe, and it appearing on the store — in real time
3. Linq demo: judge texts the iMessage number → Sales agent responds, recommends a product, sends Stripe Payment Link
4. Stripe dashboard: "$X in real revenue, Y transactions — all autonomous"
5. Band room: CEO decision trail — "Dropped 3 products after Terac rated them <3/5. Sourced replacements. Repriced earbuds from $15→$9 after pricing study."
6. Terac before/after: "50 real people rated our catalog. Here's v1 vs v2. Agents made every change."
7. FLUX/Kling: "Our Growth agent generated these ad creatives and videos to push via iMessage"
8. Multi-channel: "Products live on our store, FB Marketplace, eBay, and iMessage — all agent-listed"

## Risks + Mitigations
| Risk | Mitigation |
|------|-----------|
| Zero sales in 4 hrs | Revenue isn't the only metric — demo the SYSTEM working. But: price at near-cost ($5-8), push hard via Linq + personal network. Even $5 proves it works. |
| claude-in-chrome flaky on FB Marketplace | Fallback: manually list first 5 products on FB, automate rest. Sourcing uses CJ API (no browser). |
| CJDropshipping API registration slow | Fallback: browse AliExpress via claude-in-chrome for initial products, then switch to CJ API when approved. |
| Your Next Store doesn't work with our Stripe | Test in Phase 0. Fallback: simple HTML page with Stripe Payment Link buttons (ugly but functional). |
| Terac responses too slow | Launch Study #1 at 12:30 (earliest possible). General Population = fastest pool. Even if results come at 2:30, that's 4 hrs to iterate. |
| FB Marketplace listings get flagged | Don't link directly to Stripe. Link to our store (legitimate). Describe product normally. |

## Sponsor Integration Checklist
| Sponsor | Integration | When | Who |
|---------|------------|------|-----|
| **Stripe** (required) | Payments, products, payment links | Phase 0-1 | A |
| **Terac** (required) | 3 studies: product selection, pricing, store UX | Phase 1-3 | A launches, both consume |
| **Linq** ($2,500) | Inbound iMessage Sales agent + App cards (no cold outbound) | Phase 1-2 | B |
| **Band** ($500) | Agent coordination room, CEO decision log | Phase 2 | A |
| **Render** ($900) | Agent backend (A) + Linq webhook (B) deployed via Render Workflows | Phase 1-2 | Both |
| **Replay** ($1,500) | Sign up, run QA on store, fix bugs, show clean report | Phase 3 | B |
| **Superserve** ($1,500) | Run CEO decision loop + fulfillment agent in sandboxes | Phase 2 | A |
| **Pioneer** ($500) | Use Pioneer open-weight model for product description generation | Phase 1-2 | A |
| **Lovable** (no prize) | Use free credits for demo dashboard | Phase 3-4 | B |

**Browser automation**: claude-in-chrome (one browser, sequential tasks). Used for FB Marketplace + eBay listing only. Product sourcing via CJDropshipping API (no browser needed). Order fulfillment via CJ API.

**Sponsor correction (verified at event)**: Solari (getsolari.com, Pinetree Research — cloud browser/sandbox sessions, `slr_live_` keys) and Superserve (superserve.ai — Firecracker sandboxes) are SEPARATE sponsors. We have a working Solari key; Solari sessions can host agent browser tasks for that prize track.

## What to Cut If Behind
1. **MUST** (revenue): Stripe Products + Your Next Store + at least Linq OR FB Marketplace
2. **MUST** (rules): Terac feedback with visible before/after
3. **$2,500**: Linq iMessage sales + App cards
4. **$1,500**: Replay QA on store (easy — just run it and fix what it finds)
5. **$1,500**: Superserve sandboxes for agent tasks
6. **$900**: Render Workflows deployment
7. **$500**: Band agent decision log
8. **$500**: Pioneer for product copy
9. **HIGH**: FB Marketplace listings (traffic source)
10. **HIGH**: FLUX/Kling marketing content
11. **MED**: eBay listings (demo breadth)
12. **MED**: Demo dashboard (Lovable)
13. **LOW**: Additional marketplaces
