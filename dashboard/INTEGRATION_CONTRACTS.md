# Dashboard integration contracts

The dashboard polls `GET /api/dashboard`. Every panel is normalized to a
`PanelState<T>` with `meta.mode` equal to `live`, `demo`, `pending`, or `error`.
Unavailable integrations return an empty panel with `pending` or `error`; they
do not invent business activity.

No revenue fixture exists. Revenue remains `null` with the message
`Waiting for live Stripe revenue` until at least one successful, net-positive
live-mode Stripe payment is verified.

All amounts ending in `Minor` are integer minor currency units (for example,
`1000` is USD $10.00). All timestamps are ISO 8601 strings.

## Person A: CEO decision log

Configure `CEO_DECISIONS_URL` and optionally `CEO_DECISIONS_TOKEN`. The endpoint
must return:

```json
{
  "updatedAt": "2026-08-15T19:43:00.000Z",
  "decisions": [
    {
      "id": "decision_01",
      "timestamp": "2026-08-15T19:43:00.000Z",
      "agent": "CEO AGENT",
      "kind": "repriced_product",
      "title": "REPRICED PRODUCT",
      "reason": "Verified human feedback requested clearer value framing.",
      "action": "Updated the product headline to match the verified feedback.",
      "stage": "learn"
    }
  ]
}
```

`kind` is one of `repriced_product`, `changed_copy`, `listed_product`,
`removed_product`, `changed_promotion`, or `other`. `stage` is one of `source`,
`validate`, `list`, `sell`, `fulfill`, or `learn`. `outcome` is optional and is
only rendered when this source supplies it. Do not send an estimated outcome.

## Person A: catalog

The production default is
`https://storefront-omega-three.vercel.app/api/catalog`. Configure
`CATALOG_URL` and optionally `CATALOG_TOKEN` to override it, or point
`CATALOG_JSON_PATH` at a server-readable JSON file. `CATALOG_URL` wins when both
are set. The preferred contract is:

```json
{
  "updatedAt": "2026-08-15T19:40:00.000Z",
  "products": [
    {
      "id": "prod_123",
      "name": "Pocket Desk Vacuum",
      "priceMinor": 1000,
      "currency": "USD",
      "source": "CJ",
      "active": true,
      "promoted": true,
      "url": "https://example.com/products/pocket-desk-vacuum",
      "imageUrl": "https://example.com/image.jpg"
    }
  ]
}
```

The adapter also accepts the existing Person A handoff array without a rewrite:

```json
[
  {
    "name": "Pocket Desk Vacuum",
    "images": ["https://example.com/image.jpg"],
    "stripe_id": "prod_123",
    "payment_link": "https://buy.stripe.com/example",
    "cost": 4.5,
    "price": 12.0
  }
]
```

It also accepts the agent backend's `product_id`, `price_cents`,
`payment_link_url`, and `cj_product_id` names. Legacy products default to USD,
active, and the first three are promoted. Legacy dollar `price` is converted to
minor units; `cost` is never displayed as price.

## Linq service

Set `LINQ_BASE_URL` to consume `<base>/api/status` and `<base>/api/events`, or
use `LINQ_STATUS_URL` and `LINQ_EVENTS_URL` as overrides. `LINQ_API_TOKEN` is an
optional server-side bearer token.

`GET /api/status`:

```json
{
  "status": "online",
  "online": true,
  "phoneNumber": {
    "display": "+1 415-305-0091",
    "public": true
  },
  "conversations": 1,
  "recommendations": 1,
  "paymentLinksSent": 1,
  "updatedAt": "2026-08-15T19:44:00.000Z"
}
```

The phone number is discarded unless `phoneNumber.public` is exactly `true`.

`GET /api/events?cursor=0&limit=100` accepts the Linq worker's native envelope:

```json
{
  "events": [
    {
      "event_id": "linq_evt_01",
      "occurred_at": "2026-08-15T19:44:00.000Z",
      "type": "inbound_message",
      "source": "linq_sales_agent",
      "conversation_id": "hashed-conversation-id",
      "data": { "message_length": 42 }
    }
  ],
  "next_cursor": 1,
  "has_more": false
}
```

The adapter maps native `intent_detected`, `product_selected`,
`product_recommended`, `checkout_link_sent`, `customer_response`, and
`conversion` events into the dashboard flow. It also accepts the normalized
event contract documented in `src/data/contracts.ts`.

## Terac before/after

Configure `TERAC_FEEDBACK_URL` and optionally `TERAC_FEEDBACK_TOKEN`:

```json
{
  "updatedAt": "2026-08-15T19:30:00.000Z",
  "studies": [
    {
      "id": "terac_01",
      "title": "Price and positioning test",
      "capturedAt": "2026-08-15T19:25:00.000Z",
      "before": {
        "summary": "Original business state",
        "items": [
          {
            "id": "prod_123",
            "name": "Pocket Desk Vacuum",
            "priceMinor": 1400,
            "currency": "USD",
            "copy": "Powerful cleaning anywhere.",
            "active": true
          }
        ]
      },
      "feedback": {
        "sampleSize": 1,
        "result": "Contract placeholder; replace with the real Terac result.",
        "rating": 5,
        "ratingScale": 5
      },
      "changes": [
        { "type": "copy", "description": "Contract placeholder change." }
      ],
      "after": {
        "summary": "Autonomously updated business state",
        "items": [
          {
            "id": "prod_123",
            "name": "Pocket Desk Vacuum",
            "priceMinor": 1400,
            "currency": "USD",
            "copy": "Clear desk crumbs in seconds.",
            "active": true
          }
        ]
      }
    }
  ]
}
```

Change `type` is `removed`, `replaced`, `price`, `copy`, or `other`.

## Stripe revenue

Preferred: configure `STRIPE_REVENUE_URL` and optionally
`STRIPE_REVENUE_TOKEN`. It must attest that the values came from live-mode
Stripe:

```json
{
  "source": "stripe",
  "livemode": true,
  "amountMinor": 1000,
  "currency": "USD",
  "orders": 1,
  "updatedAt": "2026-08-15T19:45:00.000Z"
}
```

Responses without `source: "stripe"` and `livemode: true` are rejected. The
endpoint must calculate actual captured revenue and account for refunds.

Alternatively, set server-only `STRIPE_SECRET_KEY`. Only keys beginning with
`sk_live_` or `rk_live_` are accepted. The adapter reads live charges on the
server, subtracts refunds, and never sends the key to browser JavaScript. A test
key leaves revenue pending instead of displaying a test dollar amount.

An authenticated live feed with no successful net-positive payment also stays
pending. Live products and Payment Links are reported separately as
`Stripe — REAL COMMERCE`; they are never presented as revenue.

## Pioneer verified evidence

`src/data/pioneer/index.ts` contains a credential-free static record copied
from `pioneer-product-intelligence/data/recent_runs.jsonl`. It attests only to
the verified historical run: GPT-OSS 120B inference PASS, Fastino GLiNER2
validation PASS, pipeline PASS, top ranking `demo-cable (95)`, verified at
`2026-08-15T19:20:56.289815Z`. It explicitly marks the service as not live and
contains no Pioneer credential.

## Sponsor proof probes

Terac and Linq chips are derived from their panel state. Stripe is
`REAL COMMERCE` when the verified catalog has active `buy.stripe.com` checkout
links, and upgrades to `REAL REVENUE` only when revenue is verified. Pioneer is
`VERIFIED` from the immutable evidence above. Band is intentionally `DISABLED`.
Render remains pending unless its configured proof URL returns:

```json
{ "ok": true, "updatedAt": "2026-08-15T19:45:00.000Z" }
```

Replay remains pending unless `REPLAY_VERIFICATION_URL` returns:

```json
{
  "verified": true,
  "verifiedAt": "2026-08-15T19:45:00.000Z"
}
```

Failed configured probes are `DEGRADED`; absent probes are `PENDING`.
