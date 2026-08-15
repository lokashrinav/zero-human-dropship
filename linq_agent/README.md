# Jac-first Linq autonomous sales agent

An independently deployable, inbound-only iMessage sales service. A signed Linq webhook is acknowledged quickly, then Jac validates the live catalog, classifies the customer request, chooses up to three eligible products, optionally obtains a fail-closed Band Business Gate approval, sends an idempotent recommendation, opens the trusted storefront product page, and records dashboard events. A direct trusted Stripe Payment Link is reserved for explicit purchase intent.

The Python surface is deliberately small: [`bridge.py`](./bridge.py) preserves the raw request body needed for Linq's Standard Webhooks signature and starts the ASGI server. Catalog rules, ranking, LLM validation, conversation state, Linq sends, idempotency, event recording, and checkout authorization are Jac.

## Run locally

Install Jac 0.34.7 using the current [Jac installer](https://www.jac-lang.org/install/) or use the official `jaseci/jaclang:0.34.7` image. Jac is a self-contained toolchain; `jaclang==0.34.7` is not a Python package to install from PyPI.

```sh
cd linq_agent
jac --version
jac install
cp .env.example .env
jac x uvicorn bridge:app --host 0.0.0.0 --port 10000
```

Populate environment variables through the shell or deployment secret manager. `.env` is ignored, and the service never logs secret values. Production requires `LINQ_API_KEY`, `LINQ_WEBHOOK_SECRET`, `PUBLIC_STORE_URL`, a checkout-ready catalog, and `PORT`; `ANTHROPIC_API_KEY` and `EVENT_SINK_URL` are optional. The Band gate is disabled by default; enable it only by setting both `BAND_GATE_ENABLED=true` and `BAND_GATE_URL`. `LINQ_PHONE_NUMBER_ID` is intentionally absent because the current Partner v3 reply API uses the inbound chat UUID and subscription filters use optional E.164 phone numbers.

`catalog.example.json` is intentionally non-transactional: its payment links are empty, not fake. Production accepts either `CATALOG_URL` (preferred when present, refreshed at most every 30 seconds) or `CATALOG_PATH`. With `PRODUCTION_MODE=true`, the example catalog is never used, every row must include a boolean `active` field, inactive rows are excluded, and every active row requires a real Stripe product ID and raw `https://buy.stripe.com/...` Payment Link. `product_url` may be supplied by the catalog; otherwise Jac derives it deterministically as `${PUBLIC_STORE_URL}/product/<slug>` using the storefront's verified slug algorithm. Explicit product URLs must be same-origin storefront HTTPS URLs. Images may be empty, but every supplied image must be an absolute HTTPS URL. The complete candidate catalog validates before an atomic swap; a malformed refresh leaves the last-known-good production catalog active.

## Validate

```sh
jac fmt --check sales_logic.jac catalog_store.jac band_gate.jac llm_sales.jac agent_runtime.jac sales_agent.jac workflow_tasks.jac
jac check -e sales_logic.jac catalog_store.jac band_gate.jac llm_sales.jac agent_runtime.jac sales_agent.jac workflow_tasks.jac
jac test sales_logic.jac
jac test catalog_store.jac
jac test band_gate.jac
.jac/venv/bin/python -m unittest -v test_bridge.py
```

The suites cover strict under-$10 behavior, categories, no match, malformed and unsafe catalogs, last-known-good reload, model hallucinated IDs/prices/URLs, missing credentials, signed webhook rejection, sequential and concurrent duplicates, per-conversation ordering, prompt injection, unsold products, opt-out/resume safety, transient/permanent Linq failures, Band APPROVE/BLOCK/fallback/fail-closed behavior, and event-sink failure.

Production catalog rows use this exact extension of the original contract:

```json
{
  "name": "Real product",
  "images": ["https://..."],
  "stripe_id": "prod_...",
  "product_url": "https://store.example/product/real-product",
  "payment_link": "https://buy.stripe.com/...",
  "cost": 4.5,
  "price": 9.0,
  "description": "Verified listing copy",
  "active": true
}
```

`product_url` is optional in the input only when `PUBLIC_STORE_URL` is configured and the deterministic storefront route can be derived. Every validated in-memory product has both `product_url` and `payment_link`. `cost` is optional internal metadata and defaults to zero/unknown when omitted; it is never exposed to the model, customer, Band gate, or public event API.

## Linq v3 integration

The receiver is pinned to `POST /webhooks/linq?version=2026-02-03`. It verifies `webhook-id`, `webhook-timestamp`, and every space-separated `v1` entry in `webhook-signature` against the untouched body, rejects stale or oversized requests, suppresses reconciled history/group/outbound events, and durably reserves `event_id` before returning HTTP 202. Per-conversation jobs retain arrival order. Transient Linq failures remain in the durable queue and retry in-process; permanent 4xx failures stop retrying.

Once a public HTTPS URL exists, create the subscription with the current Partner API:

```sh
curl --request POST 'https://api.linqapp.com/api/partner/v3/webhook-subscriptions' \
  --header "Authorization: Bearer $LINQ_API_KEY" \
  --header 'Content-Type: application/json' \
  --data '{
    "target_url": "https://YOUR-SERVICE.example/webhooks/linq?version=2026-02-03",
    "subscribed_events": ["message.received"]
  }'
```

Save the response's one-time `signing_secret` as `LINQ_WEBHOOK_SECRET`. Add `phone_numbers` only if an E.164 subscription filter is desired. There is no documented Partner v3 “test webhook” endpoint: test the real integration by sending an inbound message to the provisioned sandbox/number and inspect Linq delivery logs.

Normal sends use `POST /api/partner/v3/chats/{chat.id}/messages`. The recommendation text, product-page action, and checkout action have separate deterministic idempotency keys. Discovery sends the validated `product_url` as a sole rich `link` part. Explicit purchase intent such as “buy it,” “checkout,” or “I'll take it” sends the validated Stripe `payment_link` the same way. Although `GET /v3/experiences` advertises `link/open`, live iMessage testing showed that Experience rendering as a non-actionable title bubble, so it is not used for customer actions. The normal prose contains no raw URL. A direct `imessage_app` part is not fabricated: that requires a real Apple Messages extension team and bundle identity.

Relevant official references: [webhook verification](https://docs.linqapp.com/guides/webhooks/), [event schema](https://docs.linqapp.com/guides/webhooks/events/), [subscriptions](https://docs.linqapp.com/guides/webhooks/subscriptions/), [send message](https://docs.linqapp.com/api/resources/chats/subresources/messages/methods/send/), [Experiences](https://docs.linqapp.com/guides/messaging/experiences/), and [inbound-first best practices](https://docs.linqapp.com/getting-started/best-practices/).

## Band Business Gate contract

The adapter is Jac-owned in `band_gate.jac` and is inert unless `BAND_GATE_ENABLED=true`. When enabled, `BAND_GATE_URL` must be HTTPS (plain HTTP is accepted only for localhost development), and the agent posts to `${BAND_GATE_URL}/review` with a 2.5-second timeout and `Idempotency-Key: <review_id>`:

```json
{
  "schema_version": 1,
  "review_id": "linq-event-id:band:1",
  "action": "product_recommendation",
  "conversation_id": "hashed-conversation-id",
  "inbound_message_id": "linq-message-id",
  "intent": "product_search",
  "catalog_version": "sha256:...",
  "candidate": {
    "products": [{
      "product_id": "prod_...",
      "name": "Product",
      "price_cents": 900,
      "currency": "USD"
    }],
    "should_send_checkout": true
  }
}
```

Band returns HTTP 2xx with exactly one deterministic decision:

```json
{"decision": "APPROVE|BLOCK", "reason": "short reason"}
```

APPROVE permits the selected recommendation. BLOCK removes that primary product, selects the next deterministic eligible catalog product, and requests one more review. Missing configuration, timeout, non-2xx, malformed response, or a fallback that is not approved produces a neutral reply with no product, price, or checkout link. The same stable `review_id` is reused after Linq job recovery. Payment URLs, product cost, phone numbers, raw customer messages, secrets, prompts, and model output are never sent to Band.

Dashboard order for an approved gated discovery is `inbound_message` → `intent_detected` → `product_selected` → `band_review_requested` → `band_review_approved` → `product_recommended` → `product_page_sent`. Explicit purchase intent ends with `checkout_link_sent`. When Band is disabled, no `band_*` events are emitted.

## Safe live Linq authentication check

After injecting `LINQ_API_KEY`, verify Partner v3 access without printing the credential:

```sh
.jac/venv/bin/python -c 'import jaclang; from sales_agent import check_linq_authentication; print(check_linq_authentication())'
```

This calls the current authenticated `GET /api/partner/v3/phone_numbers` and `GET /api/partner/v3/experiences` endpoints. It prints only sanitized resource IDs, public phone numbers, reputation states, and capability booleans—never the credential.

## Render

`render.yaml` and `Dockerfile` deploy the webhook service with the official Jac runtime and a persistent `/var/data` disk. Render sets `PRODUCTION_MODE=true`, so it fails safely with zero products until either `CATALOG_URL` serves a valid production catalog or `/var/data/linq-agent/catalog.json` exists. `BAND_GATE_ENABLED=false` is the deployment default.

The optional Render Workflow is meaningful but not on the P0 delivery path. `workflows/main.py` registers `audit_catalog`; the SDK-compatible Python task calls `workflow_tasks.jac`, which performs the real full-catalog safety audit. Render Blueprints do not currently create Workflow services, so link this repository and register that task separately using the commands in `workflows/README.md`. A Workflow outage never affects webhook replies.

## Public API

- `GET /healthz` — liveness only.
- `GET /api/status` — safe service/catalog/configuration booleans and idempotent counters. It retains the original snake-case contract and also exposes `online`, `phoneNumber`, `conversations`, `recommendations`, `paymentLinksSent`, and `updatedAt` for the judge dashboard.
- `GET /api/events?cursor=0&limit=100` — cursor-paginated, append-only autonomy events. It contains hashed conversation IDs and no phone numbers, message bodies, secrets, cost, raw model output, or prompts.
- `POST /webhooks/linq?version=2026-02-03` — signed Linq webhook receiver.

The stable dashboard event contract is specified in [`HANDOFF.md`](./HANDOFF.md).
