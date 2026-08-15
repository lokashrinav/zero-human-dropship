# Person B — Linq Agent Handoff

Updated: 2026-08-15

## Current checkpoint

- Linq Partner API contract pinned to v3.
- Webhook payload pinned to `2026-02-03`.
- P0 webhook, deterministic recommendation, storefront product action, explicit-intent checkout, durable idempotency, last-known-good catalog reload, and event APIs are implemented.
- Optional Jac-owned Band Business Gate is implemented, disabled by default, and fail-closed when enabled.
- Jac compilation and automated discovery/purchase-intent paths pass against the 10-product production catalog.
- The live service is `https://zero-human-linq-agent.onrender.com`; Linq Partner v3 authentication, the signed webhook subscription, real inbound messaging, and trusted outbound checkout were verified before this UX patch.

## Non-negotiable contracts

- Webhook: `POST /webhooks/linq?version=2026-02-03`
- Reply: `POST https://api.linqapp.com/api/partner/v3/chats/{chat_id}/messages`
- Recommendation text, product-page action, and checkout are separate, idempotent sends.
- Discovery opens the deterministic same-origin storefront `product_url`; explicit purchase intent opens the trusted Stripe `payment_link`.
- Checkout is a sole `link` part copied from the validated catalog, never model text.
- Linq's standard `link` part is used for product and checkout actions. Live iMessage testing showed the advertised `link/open` Experience rendered as a non-actionable title bubble.
- STOP/semantic opt-out is persisted with no outbound send; START/UNSTOP resumes.
- Transient sends remain durable and retry every 15 seconds; permanent 4xx failures are dead-lettered as diagnostics.
- No cold outbound messaging.
- Band never receives payment links, cost, phone numbers, raw messages, secrets, prompts, or model output.

## Catalog handoff from Person A

Set `CATALOG_URL` to a public HTTPS JSON endpoint or place the real file at the configured absolute `CATALOG_PATH`. `CATALOG_URL` takes precedence. Render runs with `PRODUCTION_MODE=true`, so a missing production source never falls back to the example catalog. Every row must include boolean `active`; inactive products are validated but excluded. A reload is atomic: a malformed replacement is rejected and the last known good catalog remains active. Every active production row requires a real Stripe product ID and raw Stripe Payment Link. Each validated product also has a same-origin `product_url`, supplied by the catalog or deterministically derived from `PUBLIC_STORE_URL` and the verified storefront slug algorithm.

## Dashboard handoff

Base URL is the deployed Person B service.

`GET /api/status` returns:

```json
{
  "status": "online|degraded",
  "online": true,
  "phoneNumber": {"display": "+12025550199", "public": true, "reputation": "HEALTHY"},
  "conversations": 12,
  "recommendations": 8,
  "paymentLinksSent": 4,
  "updatedAt": "RFC3339 UTC",
  "catalog_products": 5,
  "checkout_ready_products": 5,
  "messages_handled": 12,
  "recommendations_sent": 8,
  "checkout_links_sent": 4,
  "pending_events": 0,
  "catalog_version": "sha256:...",
  "catalog_error": "",
  "linq_configured": true,
  "webhook_verification_configured": true,
  "llm_configured": false,
  "link_experience_available": true,
  "band_gate_enabled": false,
  "band_gate_configured": false,
  "started_at": "RFC3339 UTC"
}
```

`GET /api/events?cursor=0&limit=100` returns:

```json
{"events": [{"schema_version": 1, "event_id": "uuid", "type": "product_recommended", "occurred_at": "RFC3339 UTC", "source": "linq_sales_agent", "conversation_id": "24-char sha256 prefix", "inbound_message_id": "provider id", "catalog_version": "sha256:...", "data": {}}], "next_cursor": 1, "has_more": false}
```

Stable event types and `data`:

- `inbound_message`: `provider_event_id`, `message_length`, `service`, `health_status`
- `intent_detected`: `intent`, `method` (`deterministic` or `llm_validated`), `reason`
- `product_considered`: `product_id`, `name`, `price`, `eligible`, `rank`
- `product_selected`: `product_ids`, `primary_product_id`, `selection_method`, `attempt`
- `band_review_requested`: `review_id`, `product_ids`, `attempt`
- `band_review_approved`: `review_id`, `product_ids`, `attempt`, `reason`
- `band_review_blocked`: `review_id`, `product_ids`, `attempt`, `reason`
- `band_review_failed_closed`: `review_id`, `product_ids`, `attempt`, `reason`
- `product_recommended`: `product_ids`, `primary_product_id`, `product_url`, `send_status`, `trace_id`
- `product_page_sent`: `product_id`, `product_url`, `channel`, `send_status`, `trace_id`
- `checkout_link_sent`: `product_id`, `payment_link`, `channel`, `send_status`, `trace_id`
- `customer_response`: `prior_state`, `intent`
- Diagnostics: `catalog_reloaded`, `catalog_reload_failed`, `duplicate_delivery_ignored`, `reply_suppressed`, `reply_send_failed`
- Reserved for a future verified payment webhook only: `conversion` with `product_id`, `amount`, `currency`, `payment_event_id`. Customer text such as “I paid” never creates this event.

The event API never returns phone numbers, message text, cost, authorization headers, keys, prompts, or raw model output. `EVENT_SINK_URL`, when set, receives the same envelope from a durable outbox; failures remain queued and cannot block a Linq send.

Counters count only unique accepted inbound events and successfully accepted outbound recommendation/checkout sends. Provider retries do not increment business counters.

Local processing is at-least-once across a crash window. Each Linq send has a stable provider idempotency key (`event_id:recommendation`, `event_id:product-page`, or `event_id:checkout`), so recovery may repeat an API request but cannot intentionally create a second Linq message. Events/counters are keyed by the inbound message and dashboard counters deduplicate crash replays.

## Remaining live verification

- Redeploy this UX checkpoint to the existing Render service.
- Send one discovery iMessage and verify the trusted storefront `product_url` action plus `product_page_sent`.
- Reply “I'll take it” and verify the trusted Stripe `payment_link` plus `checkout_link_sent`.
- Keep `BAND_GATE_ENABLED=false`; disabled Band emits no `band_*` events.

## Verified locally

- Jac `0.34.7 (Darwin arm64)`.
- `jac fmt --check` and `jac check -e` on every Jac module.
- Jac MCP `validate_jac` on `band_gate.jac` and `agent_runtime.jac`: valid, zero errors/warnings.
- `jac test sales_logic.jac`: 21 passed.
- `jac test catalog_store.jac`: 34 passed because Jac also discovers the imported sales annex; all passed.
- `jac test band_gate.jac`: 4 passed.
- `.jac/venv/bin/python -m unittest -v test_bridge.py`: 29 passed.
- Python-to-Jac import, catalog workflow audit, signed webhook verification, concise under-$10 product-page action, explicit-intent checkout, concurrent idempotency, and event-sink outage behavior passed locally.
