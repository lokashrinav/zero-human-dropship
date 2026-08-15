"""Offline tests for deterministic product-intelligence business rules."""

def _demo_products -> list[Product] {
    return [
        Product(
            id="cable-1",
            name="Braided USB-C Cable",
            supplier_cost=2.25,
            raw_description="One-meter braided USB-C charging cable.",
        ),
        Product(
            id="lamp-1",
            name="Clip Reading Light",
            supplier_cost=4.25,
            raw_description="Compact clip light with three brightness levels and USB charging.",
        ),
        Product(
            id="tray-1",
            name="Silicone Cable Tray",
            supplier_cost=1.8,
            raw_description="Flexible silicone tray for organizing small charging cables.",
        ),

    ];
}


test "parses and ranks three structured model proposals" {
    products = _demo_products();
    raw = """{
      "ranked_products": [
        {"id":"lamp-1","score":91,"suggested_title":"Clip Reading Light","suggested_description":"Compact clip light with three brightness levels and USB charging.","suggested_price":"$14.50","reason":"Compact source-described features suit the goal.","risk_flags":[]},
        {"id":"cable-1","score":82,"suggested_title":"Braided USB-C Cable","suggested_description":"One-meter braided USB-C charging cable.","suggested_price":9.99,"reason":"Simple low-cost charging accessory.","risk_flags":[]},
        {"id":"tray-1","score":75,"suggested_title":"Silicone Cable Tray","suggested_description":"Flexible silicone tray for organizing small charging cables.","suggested_price":7.99,"reason":"Low-cost organization accessory.","risk_flags":[]}
      ]
    }""";
    proposals = parse_decoder_output(raw);
    ranked = validate_proposals(
        products, "impulse products likely to convert under $15", proposals, {}, False,
    );
    assert len(ranked) == 3;
    assert ranked[0].id == "lamp-1";
    assert ranked[0].suggested_price == 11.99;
    assert "fastino_unavailable" in ranked[0].risk_flags;
    assert "model_copy_replaced_with_source" in ranked[0].risk_flags;
}


test "replaces fabricated copy with source text" {
    product = Product(
        id="lamp-1",
        name="Clip Reading Light",
        supplier_cost=4.25,
        raw_description="Compact clip light with three brightness levels.",
    );
    proposal = ModelProposal(
        id="lamp-1",
        score=88,
        suggested_title="Bestseller Clip Light",
        suggested_description="Customers love this free shipping bargain.",
        model_suggested_price=14.99,
        reason="Best seller with thousands sold.",
    );
    ranked = validate_proposals([product], "under $15", [proposal], {}, False);
    assert ranked[0].suggested_title == product.name;
    assert ranked[0].suggested_description == product.raw_description;
    assert "model_copy_replaced_with_source" in ranked[0].risk_flags;
}


test "fastino unsupported claim triggers deterministic fallback" {
    product = Product(
        id="cable-1",
        name="Braided USB-C Cable",
        supplier_cost=2.25,
        raw_description="One-meter braided USB-C charging cable.",
    );
    proposal = ModelProposal(
        id="cable-1",
        score=80,
        suggested_title="Waterproof Braided USB-C Cable",
        suggested_description="A waterproof one-meter charging cable.",
        model_suggested_price=9.99,
        reason="Useful cable.",
    );
    gliner = """{"result":{"entities":[{"text":"waterproof","label":"product feature","score":0.98}]}}""";
    ranked = validate_proposals(
        [product], "under $15", [proposal], {"cable-1": gliner}, True
    );
    assert ranked[0].suggested_title == product.name;
    assert any(flag.startswith("unsupported_claim:") for flag in ranked[0].risk_flags);
}


test "rejects duplicate product ids" {
    product = Product(
        id="dup", name="Item", supplier_cost=1.0, raw_description="A supplied item.",
    );
    try {
        validate_inputs([product, product], "under $15");
        assert False , "duplicate ids must fail";
    } except ValueError {
        assert True;
    }
}
