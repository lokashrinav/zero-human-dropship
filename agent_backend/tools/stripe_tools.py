import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_product(name: str, description: str, images: list[str], price_cents: int, cost_cents: int, cj_product_id: str = "") -> dict:
    """Create a Stripe product with price and payment link. Returns everything Person B needs."""
    product = stripe.Product.create(
        name=name,
        description=description,
        images=images[:8],
        metadata={
            "cj_product_id": cj_product_id,
            "cost_cents": str(cost_cents),
            "source": "agent",
        },
        shippable=True,
    )

    price = stripe.Price.create(
        product=product.id,
        unit_amount=price_cents,
        currency="usd",
    )

    payment_link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        shipping_address_collection={"allowed_countries": ["US"]},
    )

    return {
        "product_id": product.id,
        "price_id": price.id,
        "payment_link_id": payment_link.id,
        "payment_link_url": payment_link.url,
        "name": name,
        "price_cents": price_cents,
        "cost_cents": cost_cents,
        "images": images,
    }


def list_products() -> list[dict]:
    """List all active products with their prices and payment links.
    This is the integration point — Person B's code calls this same function
    (or hits Stripe API directly) to get product data."""
    products = stripe.Product.list(active=True, limit=100)
    result = []
    for p in products.data:
        prices = stripe.Price.list(product=p.id, active=True, limit=1)
        if not prices.data:
            continue
        price = prices.data[0]

        links = stripe.PaymentLink.list(limit=100)
        payment_link_url = ""
        for link in links.data:
            if link.active and any(li.price.id == price.id if hasattr(li.price, 'id') else li.price == price.id for li in stripe.PaymentLink.list_line_items(link.id).data):
                payment_link_url = link.url
                break

        result.append({
            "product_id": p.id,
            "name": p.name,
            "description": p.description,
            "images": p.images,
            "price_cents": price.unit_amount,
            "price_id": price.id,
            "payment_link_url": payment_link_url,
            "cost_cents": int(p.metadata.get("cost_cents", 0)),
            "cj_product_id": p.metadata.get("cj_product_id", ""),
        })
    return result


def update_price(product_id: str, new_price_cents: int) -> dict:
    """Archive old price, create new one. Returns new price ID."""
    old_prices = stripe.Price.list(product=product_id, active=True)
    for p in old_prices.data:
        stripe.Price.modify(p.id, active=False)

    new_price = stripe.Price.create(
        product=product_id,
        unit_amount=new_price_cents,
        currency="usd",
    )
    return {"price_id": new_price.id, "price_cents": new_price_cents}


def deactivate_product(product_id: str):
    """Soft-delete: deactivate product so it disappears from store."""
    stripe.Product.modify(product_id, active=False)


def get_recent_charges(limit: int = 20) -> list[dict]:
    """Get recent successful charges for CEO decision loop."""
    charges = stripe.Charge.list(limit=limit)
    return [
        {
            "id": c.id,
            "amount_cents": c.amount,
            "created": c.created,
            "description": c.description,
            "paid": c.paid,
            "product_description": c.metadata.get("product", ""),
        }
        for c in charges.data
        if c.paid
    ]
