test "valid catalog parses exact cents" {
    snapshot = validate_catalog_text(
        """[{"name":"Fixture","images":[],"stripe_id":"prod_fixture","payment_link":"https://buy.stripe.com/test_fixture","cost":4.5,"price":9.5,"description":"Test fixture."}]"""
    );
    assert len(snapshot.products) == 1;
    assert snapshot.products[0].cost_cents == 450;
    assert snapshot.products[0].price_cents == 950;
    assert snapshot.checkout_ready_products == 1;
}


test "production catalog may omit internal cost" {
    snapshot = validate_catalog_text(
        """[{"name":"Fixture","images":[],"stripe_id":"prod_fixture","payment_link":"https://buy.stripe.com/test_fixture","price":9.5,"description":"Test fixture.","active":true}]""",
        require_active=True
    );
    assert len(snapshot.products) == 1;
    assert snapshot.products[0].cost_cents == 0;
    assert snapshot.products[0].price_cents == 950;
}


test "empty checkout link rejects normal catalog" {
    try {
        _ = validate_catalog_text(
            """[{"name":"Example","images":[],"stripe_id":"prod_example","payment_link":"","cost":1,"price":2,"description":"Safe example."}]"""
        );
        assert False , "empty production link must reject";
    } except ValueError {
        assert True;
    }
}


test "empty checkout link is allowed only in example mode" {
    snapshot = validate_catalog_text(
        """[{"name":"Example","images":[],"stripe_id":"prod_example","payment_link":"","cost":1,"price":2,"description":"Safe example."}]""",
        allow_non_transactional=True
    );
    assert snapshot.checkout_ready_products == 0;
    assert snapshot.products[0].payment_link == "";
}


test "malformed catalog missing field rejects" {
    try {
        _ = validate_catalog_text(
            """[{"name":"Broken","images":[],"stripe_id":"prod_broken","cost":1,"price":2,"description":"Missing link."}]"""
        );
        assert False , "should have rejected missing payment_link";
    } except ValueError {
        assert True;
    }
}


test "unsafe payment host rejects" {
    try {
        _ = validate_catalog_text(
            """[{"name":"Bad","images":[],"stripe_id":"prod_bad","payment_link":"https://evil.example/pay","cost":1,"price":2,"description":"Unsafe."}]"""
        );
        assert False , "should reject a non-Stripe payment host";
    } except ValueError {
        assert True;
    }
}


test "markdown payment link rejects" {
    try {
        _ = validate_catalog_text(
            """[{"name":"Bad","images":[],"stripe_id":"prod_bad","payment_link":"[https://buy.stripe.com/test](https://buy.stripe.com/test)","cost":1,"price":2,"description":"Unsafe."}]"""
        );
        assert False , "should reject Markdown";
    } except ValueError {
        assert True;
    }
}


test "duplicate product ids reject entire catalog" {
    try {
        _ = validate_catalog_text(
            """[{"name":"One","images":[],"stripe_id":"prod_same","payment_link":"","cost":1,"price":2,"description":"One."},{"name":"Two","images":[],"stripe_id":"prod_same","payment_link":"","cost":1,"price":3,"description":"Two."}]"""
        );
        assert False , "should reject duplicates";
    } except ValueError {
        assert True;
    }
}


test "boolean and over precise money reject" {
    for invalid_price in ["true", "9.999"] {
        try {
            _ = validate_catalog_text(
                f"[{{\"name\":\"Bad\",\"images\":[],\"stripe_id\":\"prod_bad\",\"payment_link\":\"\",\"cost\":1,\"price\":{invalid_price},\"description\":\"Bad price.\"}}]"
            );
            assert False , "should reject invalid money";
        } except ValueError {
            assert True;
        }
    }
}


test "cost greater than price rejects" {
    try {
        _ = validate_catalog_text(
            """[{"name":"Bad","images":[],"stripe_id":"prod_bad","payment_link":"","cost":10,"price":9,"description":"Bad margin."}]"""
        );
        assert False , "should reject negative margin";
    } except ValueError {
        assert True;
    }
}


test "production catalog requires explicit active status" {
    try {
        _ = validate_catalog_text(
            """[{"name":"Fixture","images":[],"stripe_id":"prod_fixture","payment_link":"https://buy.stripe.com/test_fixture","cost":4,"price":9,"description":"Fixture."}]""",
            require_active=True
        );
        assert False , "production entry without active must reject";
    } except ValueError {
        assert True;
    }
}


test "inactive production products are never exposed" {
    snapshot = validate_catalog_text(
        """[{"name":"Inactive","images":[],"stripe_id":"prod_inactive","payment_link":"https://buy.stripe.com/test_inactive","cost":4,"price":9,"description":"Inactive fixture.","active":false},{"name":"Active","images":["https://images.example.test/active.jpg"],"stripe_id":"prod_active","payment_link":"https://buy.stripe.com/test_active","cost":4,"price":8,"description":"Active fixture.","active":true}]""",
        require_active=True
    );
    assert len(snapshot.products) == 1;
    assert snapshot.products[0].stripe_id == "prod_active";
    assert snapshot.checkout_ready_products == 1;
}
