import os
import time
from collections import defaultdict

import stripe


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def _require_api_key() -> None:
    """Fail with an actionable error instead of sending an empty credential."""
    if not os.getenv("STRIPE_SECRET_KEY"):
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")


def _meta_get(obj, key: str, default=""):
    """Safe key access for StripeObject, which is not a dict in newer stripe versions."""
    if obj is None:
        return default
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default



def _create_payment_link(price_id: str):
    return stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        shipping_address_collection={"allowed_countries": ["US"]},
        metadata={"price_id": price_id},
    )


def create_product(
    name: str,
    description: str,
    images: list[str],
    price_cents: int,
    cost_cents: int,
    cj_product_id: str = "",
) -> dict:
    """Create a Stripe product, its current price, and a shipping-enabled payment link."""
    _require_api_key()
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
    payment_link = _create_payment_link(price.id)

    # Keeping the active checkout objects on the product makes catalog reads cheap
    # and lets repricing atomically move customers to the new link.
    stripe.Product.modify(
        product.id,
        default_price=price.id,
        metadata={
            "current_price_id": price.id,
            "payment_link_id": payment_link.id,
        },
    )

    return {
        "product_id": product.id,
        "price_id": price.id,
        "payment_link_id": payment_link.id,
        "payment_link_url": payment_link.url,
        "name": name,
        "price_cents": price_cents,
        "cost_cents": cost_cents,
        "cj_product_id": cj_product_id,
        "images": images,
    }


def _payment_link_for_product(product, price_id: str) -> tuple[str, str]:
    """Return (link id, URL), supporting products created before metadata existed."""
    link_id = _meta_get(product.metadata, "payment_link_id", "")
    if link_id:
        try:
            link = stripe.PaymentLink.retrieve(link_id)
            if link.active:
                return link.id, link.url
        except stripe.error.StripeError:
            pass

    # Legacy fallback. New products never take this slower path.
    for link in stripe.PaymentLink.list(active=True, limit=100).auto_paging_iter():
        for item in stripe.PaymentLink.list_line_items(link.id, limit=100).data:
            item_price_id = getattr(item.price, "id", item.price)
            if item_price_id == price_id:
                return link.id, link.url
    return "", ""


def list_products() -> list[dict]:
    """List active products with their current price, cost, and checkout URL."""
    _require_api_key()
    products = stripe.Product.list(active=True, limit=100)
    result = []
    for product in products.data:
        price_id = _meta_get(product.metadata, "current_price_id", "")
        price = None
        if price_id:
            try:
                candidate = stripe.Price.retrieve(price_id)
                if candidate.active:
                    price = candidate
            except stripe.error.StripeError:
                pass

        if price is None:
            prices = stripe.Price.list(product=product.id, active=True, limit=1)
            if not prices.data:
                continue
            price = prices.data[0]

        link_id, link_url = _payment_link_for_product(product, price.id)
        result.append(
            {
                "product_id": product.id,
                "name": product.name,
                "description": product.description,
                "images": list(product.images),
                "price_cents": price.unit_amount,
                "price_id": price.id,
                "payment_link_id": link_id,
                "payment_link_url": link_url,
                "cost_cents": int(_meta_get(product.metadata, "cost_cents", 0)),
                "cj_product_id": _meta_get(product.metadata, "cj_product_id", ""),
            }
        )
    return result


def update_price(product_id: str, new_price_cents: int) -> dict:
    """Create a new price and checkout link, then retire the previous versions."""
    _require_api_key()
    product = stripe.Product.retrieve(product_id)
    old_link_id = _meta_get(product.metadata, "payment_link_id", "")
    old_prices = list(stripe.Price.list(product=product_id, active=True).auto_paging_iter())

    new_price = stripe.Price.create(
        product=product_id,
        unit_amount=new_price_cents,
        currency="usd",
    )
    new_link = _create_payment_link(new_price.id)

    # Move the product first: Stripe does not allow archiving a default price.
    stripe.Product.modify(
        product_id,
        default_price=new_price.id,
        metadata={
            "current_price_id": new_price.id,
            "payment_link_id": new_link.id,
        },
    )

    # The deployed storefront serves a build-time catalog.json with the OLD
    # payment link. Deactivating it would turn live storefront/FB traffic into
    # dead checkout links, so the old link stays active (at the old price)
    # until the storefront re-syncs. Old prices also stay active for that link.

    return {
        "product_id": product_id,
        "price_id": new_price.id,
        "price_cents": new_price_cents,
        "payment_link_id": new_link.id,
        "payment_link_url": new_link.url,
        "old_payment_link_id": old_link_id,
        "old_prices_kept_active": [p.id for p in old_prices if p.id != new_price.id],
        "note": "storefront re-sync needed: run storefront/scripts/sync-stripe-catalog.ts + redeploy, then old link can be retired",
    }


def deactivate_product(product_id: str) -> None:
    """Deactivate a product and its agent-managed payment link."""
    _require_api_key()
    product = stripe.Product.retrieve(product_id)
    link_id = _meta_get(product.metadata, "payment_link_id", "")
    if link_id:
        try:
            stripe.PaymentLink.modify(link_id, active=False)
        except stripe.error.StripeError:
            pass
    stripe.Product.modify(product_id, active=False)


def get_recent_charges(limit: int = 20) -> list[dict]:
    """Get recent successful charges for the audit log."""
    _require_api_key()
    charges = stripe.Charge.list(limit=limit)
    return [
        {
            "id": charge.id,
            "amount_cents": charge.amount,
            "created": charge.created,
            "description": charge.description,
            "paid": charge.paid,
            "product_description": _meta_get(charge.metadata, "product", ""),
        }
        for charge in charges.data
        if charge.paid
    ]


def get_sales_summary(since_hours: int = 24, limit: int = 100) -> dict:
    """Aggregate paid Stripe Checkout sessions into product-level revenue metrics."""
    _require_api_key()
    cutoff = int(time.time()) - (since_hours * 60 * 60)
    sessions = stripe.checkout.Session.list(limit=limit, created={"gte": cutoff})
    by_product: dict[str, dict] = defaultdict(
        lambda: {"units": 0, "revenue_cents": 0, "orders": 0, "name": ""}
    )
    gross_revenue_cents = 0
    paid_orders = 0
    units = 0

    for session in sessions.data:
        if session.payment_status != "paid":
            continue
        paid_orders += 1
        gross_revenue_cents += int(session.amount_total or 0)
        seen_in_order = set()
        line_items = stripe.checkout.Session.list_line_items(
            session.id,
            limit=100,
            expand=["data.price.product"],
        )
        for item in line_items.data:
            quantity = int(item.quantity or 0)
            units += quantity
            product = item.price.product
            product_id = getattr(product, "id", product)
            product_name = getattr(product, "name", "")
            metric = by_product[str(product_id)]
            metric["units"] += quantity
            metric["revenue_cents"] += int(item.amount_total or 0)
            metric["name"] = product_name or metric["name"]
            if product_id not in seen_in_order:
                metric["orders"] += 1
                seen_in_order.add(product_id)

    return {
        "window_hours": since_hours,
        "orders": paid_orders,
        "units": units,
        "gross_revenue_cents": gross_revenue_cents,
        "by_product": [
            {"product_id": product_id, **metrics}
            for product_id, metrics in sorted(by_product.items())
        ],
    }
