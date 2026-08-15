# Repository Agent Rules

## Jac is the source of truth

- Treat Jac as its own language. Jac syntax MUST be verified with the installed compiler; do not infer syntax from Python, TypeScript, old tutorials, or memory.
- Before novel Jac syntax, consult the current installed `jac guide` resources and the official Jac MCP exposed by `jac mcp`.
- Run `jac fmt --check` and `jac check` on every changed Jac file. Run the narrowest relevant `jac test` suite before claiming success.
- Never leave pseudocode, illustrative fragments, or uncompiled syntax pretending to be functional Jac.
- Keep business rules and autonomous-agent decisions in Jac. A Python or TypeScript file may exist only as a minimal third-party SDK, HTTP-runtime, or deployment bridge when Jac cannot satisfy that boundary directly.

## Shared workspace boundaries

- `storefront/` is owned by the storefront agent.
- `agent_backend/` is owned by the ecommerce/backend agent.
- `linq_agent/` is the independently buildable Linq autonomous sales service.
- Do not rewrite or clean another agent's changes. Coordinate through documented contracts instead.

## Secrets and commerce safety

- Never commit `.env`, API keys, webhook signing secrets, or raw authorization headers.
- Never invent products, prices, availability, policies, or checkout URLs.
- Checkout links must be copied by deterministic code from a fully validated catalog entry; model output must never supply or override a payment URL.
- Linq messaging is inbound-first. Do not add unsolicited bulk or cold-message behavior.
- When the Linq agent has `BAND_GATE_ENABLED=true`, product/payment recommendations require Band `APPROVE`; missing, invalid, or timed-out review results fail closed. Never send payment links, cost, phone numbers, raw messages, secrets, prompts, or model output to Band.
