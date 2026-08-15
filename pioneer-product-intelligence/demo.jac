"""Run the three-product live Pioneer pipeline from the command line."""

import from product_intelligence { Product, _rank_products_live }


with entry:__main__ {
    products = [
        Product(
            id="demo-light",
            name="Rechargeable Clip Reading Light",
            supplier_cost=4.25,
            raw_description="Compact clip light with three brightness levels and USB-C charging.",
            images=["https://example.invalid/light.jpg"],
        ),
        Product(
            id="demo-cable",
            name="Braided USB-C Cable",
            supplier_cost=2.1,
            raw_description="One-meter braided USB-C charging cable.",
            images=["https://example.invalid/cable.jpg"],
        ),
        Product(
            id="demo-tray",
            name="Silicone Cable Organizer Tray",
            supplier_cost=1.8,
            raw_description="Flexible silicone tray for organizing small charging cables.",
            images=["https://example.invalid/tray.jpg"],
        ),

    ];
    result = _rank_products_live(
        products, "impulse products likely to convert under $15"
    );
    print(result.to_json());
}
