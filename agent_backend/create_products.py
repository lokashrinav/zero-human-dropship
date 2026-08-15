"""Create initial product catalog in Stripe with payment links."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

PRODUCTS = [
    {
        "name": "LED Strip Lights RGB 16 Colors",
        "description": "Color-changing LED strip lights with remote control. 16 colors, multiple modes. Perfect for bedroom, gaming setup, or dorm room. USB powered.",
        "price_cents": 599,
        "cost_cents": 350,
    },
    {
        "name": "Magnetic Phone Mount for Car",
        "description": "Ultra-strong magnetic car phone holder. Sticks to any dashboard or vent. Works with all phones. 360-degree rotation.",
        "price_cents": 499,
        "cost_cents": 250,
    },
    {
        "name": "Portable Mini Fan USB",
        "description": "Compact USB desk fan with 3 speeds. Whisper quiet. Perfect for office, dorm, or travel. USB-C powered.",
        "price_cents": 499,
        "cost_cents": 300,
    },
    {
        "name": "Wireless Earbuds with Charging Case",
        "description": "True wireless Bluetooth earbuds with noise isolation. 20-hour battery with charging case. Touch controls. Compatible with iPhone and Android.",
        "price_cents": 799,
        "cost_cents": 450,
    },
    {
        "name": "Phone Ring Light for Selfies",
        "description": "Clip-on ring light for your phone. 3 brightness levels. Rechargeable. Perfect for selfies, video calls, and TikTok.",
        "price_cents": 399,
        "cost_cents": 200,
    },
    {
        "name": "Cable Organizer Clips 10-Pack",
        "description": "Keep your desk clean. Self-adhesive cable management clips. Pack of 10. Works on wood, glass, and plastic.",
        "price_cents": 349,
        "cost_cents": 150,
    },
    {
        "name": "Foldable Phone Stand Adjustable",
        "description": "Aluminum alloy foldable phone and tablet stand. Adjustable angle. Anti-slip pads. Folds flat for travel.",
        "price_cents": 599,
        "cost_cents": 300,
    },
    {
        "name": "Screen Cleaner Spray Kit",
        "description": "Streak-free screen cleaner for phones, laptops, tablets. Includes microfiber cloth. Travel-sized.",
        "price_cents": 399,
        "cost_cents": 180,
    },
    {
        "name": "USB-C Fast Charging Cable 6ft",
        "description": "Braided nylon USB-C cable. Fast charging up to 60W. 6-foot length. Durable connectors. Works with Samsung, Pixel, iPad.",
        "price_cents": 499,
        "cost_cents": 200,
    },
    {
        "name": "Laptop Cooling Pad with Fan",
        "description": "Slim laptop cooling pad with quiet fan. Fits up to 15.6 inches. USB powered. Adjustable height.",
        "price_cents": 899,
        "cost_cents": 500,
    },
]


def main():
    if not stripe.api_key:
        print("ERROR: STRIPE_SECRET_KEY not set in .env")
        sys.exit(1)

    created = []
    for p in PRODUCTS:
        try:
            product = stripe.Product.create(
                name=p["name"],
                description=p["description"],
                metadata={"cost_cents": str(p["cost_cents"]), "source": "agent"},
                shippable=True,
            )
            price = stripe.Price.create(
                product=product.id,
                unit_amount=p["price_cents"],
                currency="usd",
            )
            payment_link = stripe.PaymentLink.create(
                line_items=[{"price": price.id, "quantity": 1}],
                shipping_address_collection={"allowed_countries": ["US"]},
                metadata={"price_id": price.id},
            )
            stripe.Product.modify(
                product.id,
                default_price=price.id,
                metadata={
                    "current_price_id": price.id,
                    "payment_link_id": payment_link.id,
                    "cost_cents": str(p["cost_cents"]),
                    "source": "agent",
                },
            )
            created.append({
                "name": p["name"],
                "price": p["price_cents"] / 100,
                "url": payment_link.url,
                "product_id": product.id,
            })
            print(f"OK: {p['name']} - ${p['price_cents']/100:.2f} - {payment_link.url}")
        except Exception as e:
            print(f"FAIL: {p['name']}: {e}")

    print(f"\n=== {len(created)} products created ===")
    for c in created:
        print(f"  {c['name']}: ${c['price']:.2f} -> {c['url']}")


if __name__ == "__main__":
    main()
