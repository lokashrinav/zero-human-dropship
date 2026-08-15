"""Ops agent: handles fulfillment when payments come in.
Triggered by Stripe webhook in main.py, not run directly.
"""
from tools.cj_tools import place_order
from tools.stripe_tools import list_products
from tools.band_tools import post_message


async def fulfill_order(session: dict):
    """Match a Stripe checkout session to CJ products and place supplier order."""
    shipping = session.get("shipping_details", {})
    if not shipping or not shipping.get("address"):
        await post_message("OpsAgent", "Order received but no shipping address — cannot fulfill")
        return

    addr = shipping["address"]
    cj_shipping = {
        "name": shipping.get("name", ""),
        "phone": "",
        "country": addr.get("country", "US"),
        "province": addr.get("state", ""),
        "city": addr.get("city", ""),
        "address": f"{addr.get('line1', '')} {addr.get('line2', '')}".strip(),
        "zip": addr.get("postal_code", ""),
    }

    products = list_products()
    cj_product_map = {p["product_id"]: p for p in products if p.get("cj_product_id")}

    line_items = session.get("line_items", {}).get("data", [])
    for item in line_items:
        product_id = item.get("price", {}).get("product", "")
        if product_id in cj_product_map:
            cj_id = cj_product_map[product_id]["cj_product_id"]
            try:
                result = await place_order(cj_id, "", cj_shipping)
                await post_message(
                    "OpsAgent",
                    f"CJ order placed for {cj_product_map[product_id]['name']}: {result}"
                )
            except Exception as e:
                await post_message("OpsAgent", f"CJ order failed for {product_id}: {e}")
