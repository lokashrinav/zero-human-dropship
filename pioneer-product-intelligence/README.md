# Pioneer Product Intelligence

Small Jac-first service that makes Pioneer a real sourcing dependency:

1. `openai/gpt-oss-120b` ranks raw supplier products and drafts restrained copy.
2. `fastino/gliner2-large-v1` extracts claims and entities from generated copy.
3. Jac checks IDs, scores, pricing, prohibited claims, and whether extracted claims exist in the supplier source.
4. Unsupported copy is replaced with the exact source name and description, with risk flags retained for review.

Both model IDs were selected from the authenticated live `GET /base-models?supports_inference=true` catalog. `gpt-oss-120b` is an open-weight Apache-2.0 model. The API key is read only from `PIONEER_API_KEY` by server-side Python standard-library HTTP code.

## Run

```bash
export PIONEER_API_KEY="..."
jac fmt --check main.sv.jac product_intelligence.jac product_intelligence.test.jac demo.jac
jac check main.sv.jac product_intelligence.jac product_intelligence.test.jac demo.jac
jac test product_intelligence.jac -v
jac run demo.jac
jac start main.sv.jac --no-client --port 8011
```

## Endpoints

- `POST /rank-products`
- `POST /generate-copy`
- `GET /status`
- `GET /model-info`
- `GET /recent-runs?limit=20`

Jac's standard response envelope places a function result at `data.result`.

Example request:

```json
{
  "products": [
    {
      "id": "cj-123",
      "name": "Rechargeable Clip Light",
      "supplier_cost": 4.25,
      "raw_description": "Clip light with three brightness levels and USB-C charging.",
      "images": ["https://supplier.example/image.jpg"]
    }
  ],
  "goal": "impulse products likely to convert under $15"
}
```

When decoder inference cannot run, the result is explicit and contains no fake ranking:

```json
{
  "status": "pioneer_unavailable",
  "ranked_products": [],
  "model": "openai/gpt-oss-120b"
}
```

Non-secret dashboard evidence is appended to `data/recent_runs.jsonl` and returned by `/recent-runs`.
