# Linq Agent Rules

- Jac is the source of truth for catalog validation, ranking, conversation state, checkout authorization, idempotency, and events.
- Jac syntax MUST be compiler-verified. Consult the installed `jac guide` and official `jac mcp` resources before novel syntax.
- Run `jac fmt --check`, `jac check`, and the relevant `jac test` command before claiming success.
- Never leave pseudocode or unchecked fragments pretending to be functional Jac.
- Python may only bridge raw HTTP/webhook or Render SDK boundaries. Do not move sales or agent decisions into Python.
- Never log secrets or send a payment URL that did not come byte-for-byte from a validated catalog entry.
- When `BAND_GATE_ENABLED=true`, every product/payment recommendation must receive an `APPROVE` decision before sending. BLOCK may use one deterministic catalog fallback; missing, invalid, or timed-out reviews fail closed.
- Never send payment links, product cost, phone numbers, raw messages, secrets, or model output to the Band gate.
- This is an inbound-first service. Do not add cold or bulk unsolicited messaging.
