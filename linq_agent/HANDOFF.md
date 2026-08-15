# Person B — Linq Agent Handoff

Updated: 2026-08-15

## Current checkpoint

- Linq Partner API contract pinned to v3.
- Webhook payload pinned to `2026-02-03`.
- P0 webhook, deterministic recommendation, separate checkout, durable idempotency, last-known-good catalog reload, and event APIs are implemented.
- Optional Jac-owned Band Business Gate is implemented, disabled by default, and fail-closed when enabled.
- Jac compilation and the automated offline send path pass. The example catalog is deliberately non-transactional, so live checkout awaits Person A's real catalog.
- Render Docker/Blueprint and a real Render Workflow catalog-audit task are present. No Render public URL or Linq credential was injected into this process, so external deployment and a real iMessage were not claimed.

## Non-negotiable contracts

- Webhook: `POST /webhooks/linq?version=2026-02-03`
- Reply: `POST https://api.linqapp.com/api/partner/v3/chats/{chat_id}/messages`
- Recommendation and checkout are separate, idempotent sends.
- Checkout is a sole `link` part copied from the validated catalog, never model text.
- Linq Experience `link/open` is used only after `GET /v3/experiences` confirms account access.
- STOP/semantic opt-out is persisted with no outbound send; START/UNSTOP resumes.
- Transient sends remain durable and retry every 15 seconds; permanent 4xx failures are dead-lettered as diagnostics.
- No cold outbound messaging.
- Band never receives payment links, cost, phone numbers, raw messages, secrets, prompts, or model output.

## Catalog handoff from Person A

Set `CATALOG_URL` to a public HTTPS JSON endpoint or place the real file at the configured absolute `CATALOG_PATH`. `CATALOG_URL` takes precedence. Render runs with `PRODUCTION_MODE=true`, so a missing production source never falls back to the example catalog. Every row must include boolean `active`; inactive products are validated but excluded. A reload is atomic: a malformed replacement is rejected and the last known good catalog remains active. Every active production row requires a real Stripe product ID and raw Stripe Payment Link.

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
- `band_review_skipped`: `reason`, `product_ids`
- `product_recommended`: `product_ids`, `primary_product_id`, `send_status`, `trace_id`
- `checkout_link_sent`: `product_id`, `payment_link`, `channel`, `send_status`, `trace_id`
- `customer_response`: `prior_state`, `intent`
- Diagnostics: `catalog_reloaded`, `catalog_reload_failed`, `duplicate_delivery_ignored`, `reply_suppressed`, `reply_send_failed`
- Reserved for a future verified payment webhook only: `conversion` with `product_id`, `amount`, `currency`, `payment_event_id`. Customer text such as “I paid” never creates this event.

The event API never returns phone numbers, message text, cost, authorization headers, keys, prompts, or raw model output. `EVENT_SINK_URL`, when set, receives the same envelope from a durable outbox; failures remain queued and cannot block a Linq send.

Counters count only unique accepted inbound events and successfully accepted outbound recommendation/checkout sends. Provider retries do not increment business counters.

Local processing is at-least-once across a crash window. Each Linq send has a stable provider idempotency key (`event_id:recommendation` or `event_id:checkout`), so recovery may repeat an API request but cannot intentionally create a second Linq message. Events/counters are keyed by the inbound message and dashboard counters deduplicate crash replays.

## Manual dependencies still unknown

- The follow-up says a real credential is available, but `LINQ_API_KEY` is not populated in this execution environment. Inject it without committing it, then run the safe authentication command in `README.md`.
- Render browser deployment reached GitHub's interactive sign-in page. Complete that login, then reconnect this standalone repository to a deliberate remote; no source repository or visibility was guessed.
- Add the real catalog through Render files; optionally add `ANTHROPIC_API_KEY` (deterministic fallback works without it).
- Deploy the Blueprint, then create the pinned webhook subscription shown in `README.md` and save its one-time `signing_secret` as `LINQ_WEBHOOK_SECRET`.
- Send one real inbound sandbox/iMessage and confirm text, trusted Stripe link, Linq delivery status, `/api/status`, and `/api/events`.
- Leave `BAND_GATE_ENABLED=false` until the Band worker supplies its HTTPS URL. Then set the URL and enable the flag; the request/response contract is in `README.md`.
- Create the optional Render Workflow service from this repository and register `audit_catalog`; no workflow step is required for the P0 webhook.

## Verified locally

- Jac `0.34.7 (Darwin arm64)`.
- `jac fmt --check` and `jac check -e` on every Jac module.
- Jac MCP `validate_jac` on `band_gate.jac` and `agent_runtime.jac`: valid, zero errors/warnings.
- `jac test sales_logic.jac`: 20 passed.
- `jac test catalog_store.jac`: 31 passed because Jac also discovers the imported sales annex; all passed.
- `jac test band_gate.jac`: 4 passed.
- `.jac/venv/bin/python -m unittest -v test_bridge.py`: 27 passed.
- Python-to-Jac import, catalog workflow audit, signed webhook verification, exact under-$10 reply/link payload, concurrent idempotency, and event-sink outage behavior passed locally.
