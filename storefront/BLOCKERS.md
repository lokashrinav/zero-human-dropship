# Blockers

- `SUPPORT_EMAIL` is not configured. The policy is intentionally honest and does not invent a contact address.
- `NEXT_PUBLIC_LINQ_PHONE` and `NEXT_PUBLIC_SALES_AGENT_URL` are not configured, so the shopping-agent CTA remains gracefully disabled.
- The 10 live Stripe products do not have product images. The storefront uses an explicit “Product image coming soon” state; no fixture imagery is presented.
- The live Stripe key was exposed in chat. Rotate it in Stripe and replace the Vercel value before treating the credential as secure.
