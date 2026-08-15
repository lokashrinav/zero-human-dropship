---
name: source-products
description: Source a batch of products from CJDropshipping into Stripe - the initial catalog build or a themed restock.
---

Source products into the catalog. Argument (optional): a theme or list of categories; default is the impulse-buy starter set.

1. Spawn the `sourcing` subagent with the brief. Default starter queries: "phone stand", "LED strip lights", "mini projector", "desk organizer", "wireless earbuds", "car phone mount", "galaxy projector", "magnetic charging cable".
2. Target 10-15 live products. If a query returns nothing usable, the subagent should substitute an adjacent query, not give up.
3. After it reports: verify with `python -m agents.cli observe` that products have payment links, then summarize the catalog (name, cost, price, margin per product).
4. Hand the new product list to the `growth` subagent for marketing if the CEO cycle called for it.
