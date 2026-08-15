"""Sourcing agent: searches CJ for products, creates them in Stripe.
Run directly: python -m agents.sourcing "phone accessories"
"""
import asyncio
import sys
from tools.cj_tools import search_products, get_product_details
from tools.stripe_tools import create_product
from tools.band_tools import post_message


MARKUP = 2.5  # 2.5x markup on CJ cost
MIN_PRICE_CENTS = 500  # don't sell below $5
MAX_PRICE_CENTS = 1500  # impulse buy ceiling


def calculate_price(cost_usd: float) -> int:
    price = int(cost_usd * MARKUP * 100)
    return max(MIN_PRICE_CENTS, min(price, MAX_PRICE_CENTS))


async def source_products(queries: list[str], max_per_query: int = 5) -> list[dict]:
    """Search CJ for products across multiple queries, create in Stripe."""
    created = []

    for query in queries:
        print(f"Searching CJ for: {query}")
        results = await search_products(query, page_size=max_per_query)

        for product in results:
            try:
                details = await get_product_details(product["cj_product_id"])
                if not details.get("images"):
                    continue

                cost_usd = float(details.get("sell_price", 0))
                if cost_usd <= 0 or cost_usd > 8:
                    continue

                price_cents = calculate_price(cost_usd)
                cost_cents = int(cost_usd * 100)

                stripe_product = create_product(
                    name=details["name"][:100],
                    description=details.get("description", "")[:500],
                    images=details["images"][:5],
                    price_cents=price_cents,
                    cost_cents=cost_cents,
                    cj_product_id=details["cj_product_id"],
                )

                created.append(stripe_product)
                await post_message(
                    "SourcingAgent",
                    f"Created product: {stripe_product['name']} — "
                    f"cost ${cost_cents/100:.2f}, selling ${price_cents/100:.2f}, "
                    f"link: {stripe_product['payment_link_url']}"
                )
                print(f"  Created: {stripe_product['name']} at ${price_cents/100:.2f}")

            except Exception as e:
                print(f"  Skipped {product.get('name', '?')}: {e}")
                continue

    print(f"\nTotal created: {len(created)} products")
    return created


if __name__ == "__main__":
    queries = sys.argv[1:] or [
        "phone accessories",
        "LED lights",
        "desk gadgets",
        "earbuds",
        "phone stand",
    ]
    asyncio.run(source_products(queries))
