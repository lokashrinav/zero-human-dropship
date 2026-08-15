test "approve response is normalized" {
    review = parse_review_response(
        {"decision": "approve", "reason": "Policy passed"}, "review-1"
    );
    assert review.decision == "APPROVE";
    assert review.review_id == "review-1";
    assert review.reason == "Policy passed";
}


test "block response is normalized" {
    review = parse_review_response(
        {"decision": " BLOCK ", "reason": "Margin rule"}, "review-2"
    );
    assert review.decision == "BLOCK";
    assert review.reason == "Margin rule";
}


test "unknown decision fails closed" {
    review = parse_review_response(
        {"decision": "maybe", "reason": "ambiguous"}, "review-3"
    );
    assert review.decision == "UNAVAILABLE";
    assert review.reason == "invalid_band_decision";
}


test "malformed https URL is not configured" {
    previous = os.getenv("BAND_GATE_URL");
    os.environ["BAND_GATE_URL"] = "https:///missing-host";
    try {
        assert not is_configured();
    } finally {
        if previous is None {
            del os.environ["BAND_GATE_URL"];
        } else {
            os.environ["BAND_GATE_URL"] = previous;
        }
    }
}
