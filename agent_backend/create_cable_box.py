"""One-shot: create the cable-management replacement product in Stripe (live)."""
from dotenv import load_dotenv
load_dotenv(".env")

import json
import stripe
from tools.stripe_tools import create_product

NAME = "Cable & Charger Organizer Box"
CJ_PID = "2608130254211611300"
CJ_VID = "2608130254211612302"          # Large size, 30.5 x 11.5 x 8 cm
CJ_ITEM_COST_CENTS = 72                  # $0.72
CJ_SHIP_CENTS = 636                      # $6.36 LuWei Ordinary US, 5-11 days
LANDED_CENTS = CJ_ITEM_COST_CENTS + CJ_SHIP_CENTS  # 708
PRICE_CENTS = 1299

DESCRIPTION = (
    "Transform your chaotic workspace into a sleek, organized haven with this crystal-clear "
    "plastic 5-compartment desk box, perfectly designed to separate your coiled USB cables, "
    "charger bricks, adapters, and dongles. The secure snap-lock lid keeps your tech essentials "
    "dust-free and tangle-free within a compact 30.5 x 11.5 x 8 cm profile that fits seamlessly "
    "on any desktop. Grab yours today to instantly elevate your daily setup and finally end the "
    "frustrating hunt for the right cord."
)

IMAGES = [
    "https://oss-cf.cjdropshipping.com/product/2026/08/13/02/eb4aa0f4-13ad-4fd5-8b6a-5c25a537296d_trans.jpeg",
    "https://oss-cf.cjdropshipping.com/product/2026/08/13/02/ca0bedef-a96b-4a54-93f5-9fda8ae04411_trans.jpeg",
    "https://oss-cf.cjdropshipping.com/product/2026/08/13/02/b4eb581e-3438-4eee-9a04-8934d455d737_trans.jpeg",
    "https://oss-cf.cjdropshipping.com/product/2026/08/13/02/272f345c-6052-49ea-98c2-3c5a499c5b8d_trans.jpeg",
]

# Guard: never create a second copy of this product.
existing = [p for p in stripe.Product.list(active=True, limit=100).auto_paging_iter()
            if p.name == NAME]
if existing:
    raise SystemExit(f"ALREADY EXISTS: {existing[0].id} — refusing to duplicate")

res = create_product(
    name=NAME,
    description=DESCRIPTION,
    images=IMAGES,
    price_cents=PRICE_CENTS,
    cost_cents=LANDED_CENTS,
    cj_product_id=CJ_PID,
)

# The fulfillment webhook maps orders via product metadata -> CJ pid + vid.
stripe.Product.modify(res["product_id"], metadata={
    "cj_product_id": CJ_PID,
    "cj_variant_id": CJ_VID,
    "cj_variant_name": "Large Size",
    "cj_item_cost_cents": str(CJ_ITEM_COST_CENTS),
    "cj_us_ship_cents": str(CJ_SHIP_CENTS),
    "cj_us_ship_channel": "LuWei Ordinary US",
    "landed_cost_cents": str(LANDED_CENTS),
    "us_shipping_verified": "true",
})

p = stripe.Product.retrieve(res["product_id"])
print(json.dumps({
    "product_id": p.id,
    "name": p.name,
    "livemode": p.livemode,
    "price_cents": PRICE_CENTS,
    "price_id": res["price_id"],
    "payment_link_url": res["payment_link_url"],
    "metadata": dict(p.metadata),
}, indent=2))
