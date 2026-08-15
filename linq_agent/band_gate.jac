import os;
import from httpx { Client, Response }
import from urllib.parse { urlparse }


obj BandReview {
    has decision: str,
        review_id: str,
        reason: str;
}


obj BandCandidate {
    has review_id: str,
        conversation_id: str,
        inbound_message_id: str,
        intent: str,
        catalog_version: str,
        products: list[dict[str, object]],
        should_send_checkout: bool;
}


def is_enabled -> bool {
    configured = os.getenv("BAND_GATE_ENABLED") or "";
    return configured.strip().casefold() == "true";
}


def is_configured -> bool {
    return _review_url() is not None;
}


def _review_url -> str | None {
    raw_url = os.getenv("BAND_GATE_URL") or "";
    base_url = raw_url.strip().rstrip("/");
    if not base_url {
        return None;
    }
    parsed = urlparse(base_url);
    hostname = parsed.hostname or "";
    if not hostname {
        return None;
    }
    local_http = parsed.scheme == "http"
    and hostname in {"127.0.0.1", "localhost", "::1"};
    if parsed.scheme != "https" and not local_http {
        return None;
    }
    if parsed.username is not None
    or parsed.password is not None
    or parsed.query
    or parsed.fragment {
        return None;
    }
    return f"{base_url}/review";
}


def parse_review_response(payload: dict[str, object], review_id: str) -> BandReview {
    raw_decision = payload.get("decision");
    raw_reason = payload.get("reason");
    decision = raw_decision.strip().upper()
        if isinstance(raw_decision, str)
        else "UNAVAILABLE";
    reason = raw_reason.strip()[:160]
        if isinstance(raw_reason, str) and raw_reason.strip()
        else "no_reason_supplied";
    if decision not in {"APPROVE", "BLOCK"} {
        return BandReview(
            decision="UNAVAILABLE", review_id=review_id, reason="invalid_band_decision"
        );
    }
    return BandReview(decision=decision, review_id=review_id, reason=reason);
}


def review_candidate(
    candidate: BandCandidate, timeout_seconds: float = 2.5
) -> BandReview {
    if not is_enabled() {
        return BandReview(
            decision="DISABLED",
            review_id=candidate.review_id,
            reason="band_gate_disabled"
        );
    }
    endpoint = _review_url();
    if endpoint is None {
        return BandReview(
            decision="UNAVAILABLE",
            review_id=candidate.review_id,
            reason="band_gate_url_missing_or_invalid"
        );
    }
    request_payload: dict[str, object] = {
        "schema_version": 1,
        "review_id": candidate.review_id,
        "action": "product_recommendation",
        "conversation_id": candidate.conversation_id,
        "inbound_message_id": candidate.inbound_message_id,
        "intent": candidate.intent,
        "catalog_version": candidate.catalog_version,
        "candidate": {
            "products": candidate.products,
            "should_send_checkout": candidate.should_send_checkout
        }
    };
    client: Client = Client(timeout=timeout_seconds);
    try {
        response: Response = client.post(
            endpoint,
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": candidate.review_id
            },
            json=request_payload
        );
        if response.status_code < 200 or response.status_code >= 300 {
            return BandReview(
                decision="UNAVAILABLE",
                review_id=candidate.review_id,
                reason=f"band_http_{response.status_code}"
            );
        }
        parsed = response.json();
    } except Exception {
        return BandReview(
            decision="UNAVAILABLE",
            review_id=candidate.review_id,
            reason="band_request_failed_or_timed_out"
        );
    } finally {
        client.close();
    }
    if not isinstance(parsed, dict) {
        return BandReview(
            decision="UNAVAILABLE",
            review_id=candidate.review_id,
            reason="invalid_band_response"
        );
    }
    return parse_review_response(parsed as dict[str, object], candidate.review_id);
}
