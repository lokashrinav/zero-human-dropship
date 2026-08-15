"""Boundary and runtime tests; Jac owns every sales decision under test."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import jaclang  # noqa: F401 - installs the .jac import hook
from fastapi.testclient import TestClient

import agent_runtime
import band_gate
from bridge import app, verify_linq_signature
from sales_agent import process_linq_event


CATALOG = [
    {
        "name": "Mini Phone Stand",
        "images": ["https://images.example.test/phone-stand.jpg"],
        "stripe_id": "prod_phone",
        "payment_link": "https://buy.stripe.com/test_fixture_phone",
        "cost": 3,
        "price": 9,
        "description": "A foldable phone accessory for a desk.",
    },
    {
        "name": "Ten Dollar Cable",
        "images": [],
        "stripe_id": "prod_cable",
        "payment_link": "https://buy.stripe.com/test_fixture_cable",
        "cost": 4,
        "price": 10,
        "description": "A durable charging cable.",
    },
]


def webhook_payload(
    event_id: str = "evt_fixture",
    message: str = "What's something cool under $10?",
) -> dict[str, object]:
    return {
        "api_version": "v3",
        "webhook_version": "2026-02-03",
        "event_type": "message.received",
        "event_id": event_id,
        "created_at": "2026-08-15T12:00:00Z",
        "trace_id": "trace_fixture",
        "partner_id": "partner_fixture",
        "data": {
            "id": f"msg_{event_id}",
            "direction": "inbound",
            "chat": {
                "id": "chat_fixture",
                "is_group": False,
                "health_status": {"status": "HEALTHY"},
            },
            "sender_handle": {"handle": "+15555550123", "is_me": False},
            "parts": [{"type": "text", "value": message}],
            "service": "iMessage",
            "sent_at": "2026-08-15T12:00:00Z",
        },
    }


def signed_headers(raw: bytes, secret: str, timestamp: int) -> dict[str, str]:
    webhook_id = "wh_fixture"
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{webhook_id}.{timestamp}.".encode() + raw
    signature = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    return {
        "webhook-id": webhook_id,
        "webhook-timestamp": str(timestamp),
        "webhook-signature": f"v1,{signature}",
        "content-type": "application/json",
    }


class LinqRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.catalog_path = self.root / "catalog.json"
        self.catalog_path.write_text(json.dumps(CATALOG), encoding="utf-8")
        self.environment = patch.dict(
            os.environ,
            {
                "DATA_DIR": str(self.root / "data"),
                "CATALOG_PATH": str(self.catalog_path),
                "LINQ_WEBHOOK_SECRET": "whsec_" + base64.b64encode(b"fixture-key").decode(),
            },
            clear=False,
        )
        self.environment.start()
        for key in (
            "LINQ_API_KEY",
            "ANTHROPIC_API_KEY",
            "EVENT_SINK_URL",
            "BAND_GATE_ENABLED",
            "BAND_GATE_URL",
            "CATALOG_URL",
            "PRODUCTION_MODE",
        ):
            os.environ.pop(key, None)
        agent_runtime.ACTIVE_CATALOG = None
        agent_runtime.ACTIVE_CATALOG_MTIME_NS = -1
        agent_runtime.ACTIVE_CATALOG_SOURCE = ""
        agent_runtime.CATALOG_ERROR = "not_loaded"
        agent_runtime.LAST_FAILED_CATALOG_SOURCE = ""
        agent_runtime.LAST_FAILED_CATALOG_MTIME_NS = -1
        agent_runtime.LAST_REMOTE_CATALOG_CHECK = -1.0
        agent_runtime.LINK_EXPERIENCE_AVAILABLE = False
        agent_runtime.PUBLIC_LINQ_PHONE = ""
        agent_runtime.LINQ_PHONE_REPUTATION = "UNKNOWN"
        agent_runtime.PROCESSING_EVENTS.clear()
        agent_runtime.PROCESSING_CONVERSATIONS.clear()
        agent_runtime.bootstrap()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def event_types(self) -> list[str]:
        result = agent_runtime.get_events(0, 250)
        return [str(event["type"]) for event in result["events"]]

    def test_standard_webhook_signature_and_staleness(self) -> None:
        raw = json.dumps(webhook_payload(), separators=(",", ":")).encode()
        secret = os.environ["LINQ_WEBHOOK_SECRET"]
        headers = signed_headers(raw, secret, 1_800_000_000)
        self.assertTrue(verify_linq_signature(raw, headers, secret, now=1_800_000_000))
        self.assertFalse(verify_linq_signature(raw + b" ", headers, secret, now=1_800_000_000))
        self.assertFalse(verify_linq_signature(raw, headers, secret, now=1_800_000_301))

    def test_bad_signature_has_no_webhook_side_effects(self) -> None:
        raw = json.dumps(webhook_payload()).encode()
        with TestClient(app) as client:
            response = client.post(
                "/webhooks/linq",
                content=raw,
                headers={
                    "webhook-id": "wh_bad",
                    "webhook-timestamp": str(int(time.time())),
                    "webhook-signature": "v1,invalid",
                    "content-type": "application/json",
                },
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(agent_runtime.pending_event_ids(), [])

    def test_oversize_webhook_rejects_before_queue(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/webhooks/linq",
                content=b"x" * 1_048_577,
                headers={"content-type": "application/json"},
            )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(agent_runtime.pending_event_ids(), [])

    def test_missing_api_credential_defers_without_network(self) -> None:
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload()))
        with patch.object(agent_runtime, "_linq_request") as request:
            result = agent_runtime.process_pending_event(str(queued["event_id"]))
        self.assertEqual(result["reason"], "missing_linq_credential")
        request.assert_not_called()
        self.assertEqual(len(agent_runtime.pending_event_ids()), 1)

    def test_duplicate_delivery_is_queued_once(self) -> None:
        raw = json.dumps(webhook_payload())
        first = agent_runtime.ingest_webhook(raw)
        second = agent_runtime.ingest_webhook(raw)
        self.assertTrue(first["queued"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(agent_runtime.get_status()["messages_handled"], 1)

    def test_own_inbound_shape_is_ignored(self) -> None:
        payload = webhook_payload("evt_own")
        payload["data"]["sender_handle"]["is_me"] = True
        result = agent_runtime.ingest_webhook(json.dumps(payload))
        self.assertFalse(result["queued"])
        self.assertEqual(result["reason"], "own_message_ignored")

    def test_status_counters_dedupe_crash_replay_events(self) -> None:
        for _ in range(2):
            agent_runtime._append_event(
                "product_recommended",
                conversation_id="conversation_fixture",
                inbound_message_id="message_fixture",
                data={"product_ids": ["prod_phone"]},
            )
        self.assertEqual(agent_runtime.get_status()["recommendations_sent"], 1)

    def test_opt_out_persists_without_any_outbound_send(self) -> None:
        payload = webhook_payload("evt_stop")
        payload["data"]["parts"] = [{"type": "text", "value": "Please stop texting me"}]
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        queued = agent_runtime.ingest_webhook(json.dumps(payload))
        with patch.object(agent_runtime, "_linq_request") as request:
            result = agent_runtime.process_pending_event(str(queued["event_id"]))
        self.assertTrue(result["processed"])
        self.assertFalse(result["replied"])
        self.assertEqual(result["reason"], "customer_opt_out")
        request.assert_not_called()

    def test_official_link_open_experience_shape_is_detected(self) -> None:
        response = {
            "data": [
                {
                    "experience": "link",
                    "actions": [{"name": "open", "params": {"url": {"required": True}}}],
                }
            ]
        }
        self.assertTrue(agent_runtime._contains_link_open(response))

    def test_live_account_discovery_uses_current_phone_and_experience_resources(
        self,
    ) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del method, payload, timeout_seconds
            if path == "/phone_numbers":
                return {
                    "phone_numbers": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "phone_number": "+12025550199",
                            "reputation": {"status": "HEALTHY"},
                        }
                    ]
                }
            if path == "/experiences":
                return {
                    "experiences": [
                        {
                            "experience": "link",
                            "actions": [{"name": "open"}],
                        }
                    ]
                }
            raise AssertionError(f"unexpected Linq path: {path}")

        with patch.object(agent_runtime, "_linq_request", side_effect=fake_linq):
            result = agent_runtime.check_linq_authentication()

        self.assertTrue(result["authenticated"])
        self.assertTrue(result["inbound_messaging_supported"])
        self.assertTrue(result["link_experience_available"])
        self.assertEqual(result["public_phone"], "+12025550199")
        self.assertEqual(agent_runtime.PUBLIC_LINQ_PHONE, "+12025550199")

        status = agent_runtime.get_status()
        self.assertTrue(status["online"])
        self.assertEqual(
            status["phoneNumber"],
            {
                "display": "+12025550199",
                "public": True,
                "reputation": "HEALTHY",
            },
        )
        self.assertEqual(status["recommendations"], status["recommendations_sent"])
        self.assertEqual(status["paymentLinksSent"], status["checkout_links_sent"])

    def test_multiple_linq_numbers_are_reported_without_guessing_public_line(self) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        responses = [
            {
                "phone_numbers": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "phone_number": "+12025550101",
                        "reputation": {"status": "HEALTHY"},
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "phone_number": "+12025550102",
                        "reputation": {"status": "HEALTHY"},
                    },
                ]
            },
            {"experiences": []},
        ]
        with patch.object(agent_runtime, "_linq_request", side_effect=responses):
            result = agent_runtime.check_linq_authentication()

        self.assertTrue(result["authenticated"])
        self.assertEqual(len(result["phone_numbers"]), 2)
        self.assertEqual(result["public_phone"], "")
        self.assertEqual(agent_runtime.PUBLIC_LINQ_PHONE, "")

    def test_under_ten_reply_and_checkout_are_catalog_grounded(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del timeout_seconds
            calls.append({"method": method, "path": path, "payload": payload or {}})
            return {"message": {"id": f"out_{len(calls)}"}}

        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload()))
        with patch.object(agent_runtime, "_linq_request", side_effect=fake_linq):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))
        self.assertTrue(result["processed"])
        self.assertEqual(result["product_ids"], ["prod_phone"])
        self.assertTrue(result["checkout_sent"])
        self.assertEqual(len(calls), 2)
        text_part = calls[0]["payload"]["message"]["parts"][0]
        checkout_part = calls[1]["payload"]["message"]["parts"][0]
        self.assertIn("$9.00", text_part["value"])
        self.assertEqual(checkout_part["type"], "link")
        self.assertEqual(
            checkout_part["value"], "https://buy.stripe.com/test_fixture_phone"
        )
        event_types = self.event_types()
        self.assertLess(event_types.index("product_selected"), event_types.index("band_review_skipped"))
        self.assertLess(event_types.index("band_review_skipped"), event_types.index("checkout_link_sent"))

    def test_band_approve_precedes_grounded_checkout(self) -> None:
        linq_calls: list[dict[str, object]] = []
        reviewed: list[band_gate.BandCandidate] = []

        def approve(candidate: band_gate.BandCandidate) -> band_gate.BandReview:
            reviewed.append(candidate)
            return band_gate.BandReview(
                decision="APPROVE",
                review_id=candidate.review_id,
                reason="fixture_approved",
            )

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del timeout_seconds
            linq_calls.append({"method": method, "path": path, "payload": payload or {}})
            return {"message": {"id": f"out_{len(linq_calls)}"}}

        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ["BAND_GATE_URL"] = "https://band.example.test"
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_band_approve")))
        with (
            patch.object(band_gate, "review_candidate", side_effect=approve),
            patch.object(agent_runtime, "_linq_request", side_effect=fake_linq),
        ):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))

        self.assertEqual(result["band_gate_status"], "approved")
        self.assertTrue(result["checkout_sent"])
        self.assertEqual(len(reviewed), 1)
        review_json = json.dumps(reviewed[0].products)
        self.assertNotIn("payment_link", review_json)
        self.assertNotIn("buy.stripe.com", review_json)
        self.assertNotIn("cost", review_json)
        checkout = linq_calls[1]["payload"]["message"]["parts"][0]
        self.assertEqual(checkout["value"], "https://buy.stripe.com/test_fixture_phone")
        event_types = self.event_types()
        ordered = [
            "inbound_message",
            "intent_detected",
            "product_selected",
            "band_review_requested",
            "band_review_approved",
            "checkout_link_sent",
        ]
        positions = [event_types.index(event_type) for event_type in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_band_adapter_posts_minimal_contract_to_review(self) -> None:
        received: list[dict[str, object]] = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("content-length", "0"))
                received.append(
                    {
                        "path": self.path,
                        "idempotency_key": self.headers.get("idempotency-key"),
                        "payload": json.loads(self.rfile.read(length)),
                    }
                )
                body = json.dumps(
                    {"decision": "APPROVE", "reason": "local_contract_test"}
                ).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ["BAND_GATE_URL"] = f"http://127.0.0.1:{server.server_port}"
        candidate = band_gate.BandCandidate(
            review_id="review-local",
            conversation_id="conversation-hash",
            inbound_message_id="message-id",
            intent="product_search",
            catalog_version="sha256:fixture",
            products=[
                {
                    "product_id": "prod_phone",
                    "name": "Mini Phone Stand",
                    "price_cents": 900,
                    "currency": "USD",
                }
            ],
            should_send_checkout=True,
        )
        try:
            review = band_gate.review_candidate(candidate)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(review.decision, "APPROVE")
        self.assertEqual(received[0]["path"], "/review")
        self.assertEqual(received[0]["idempotency_key"], "review-local")
        payload = received[0]["payload"]
        self.assertEqual(payload["review_id"], "review-local")
        serialized = json.dumps(payload)
        self.assertNotIn("payment_link", serialized)
        self.assertNotIn("buy.stripe.com", serialized)
        self.assertNotIn("cost", serialized)

    def test_band_adapter_timeout_returns_unavailable(self) -> None:
        class SlowHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("content-length", "0"))
                self.rfile.read(length)
                time.sleep(0.05)
                body = b'{"decision":"APPROVE"}'
                try:
                    self.send_response(200)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ["BAND_GATE_URL"] = f"http://127.0.0.1:{server.server_port}"
        candidate = band_gate.BandCandidate(
            review_id="review-timeout",
            conversation_id="conversation-hash",
            inbound_message_id="message-id",
            intent="product_search",
            catalog_version="sha256:fixture",
            products=[
                {
                    "product_id": "prod_phone",
                    "name": "Mini Phone Stand",
                    "price_cents": 900,
                    "currency": "USD",
                }
            ],
            should_send_checkout=True,
        )
        try:
            review = band_gate.review_candidate(candidate, timeout_seconds=0.01)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertEqual(review.decision, "UNAVAILABLE")
        self.assertEqual(review.reason, "band_request_failed_or_timed_out")

    def test_band_timeout_or_missing_url_fails_closed_without_product(self) -> None:
        linq_calls: list[dict[str, object]] = []

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del method, path, timeout_seconds
            linq_calls.append(payload or {})
            return {"message": {"id": "out_safe"}}

        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ.pop("BAND_GATE_URL", None)
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_band_closed")))
        with patch.object(agent_runtime, "_linq_request", side_effect=fake_linq):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))

        self.assertEqual(result["band_gate_status"], "fail_closed")
        self.assertFalse(result["checkout_sent"])
        self.assertEqual(result["product_ids"], [])
        self.assertEqual(len(linq_calls), 1)
        safe_text = linq_calls[0]["message"]["parts"][0]["value"]
        self.assertNotIn("Mini Phone Stand", safe_text)
        self.assertNotIn("buy.stripe.com", safe_text)
        self.assertIn("band_review_failed_closed", self.event_types())

    def test_band_also_gates_product_answer_without_checkout(self) -> None:
        linq_calls: list[dict[str, object]] = []

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del method, path, timeout_seconds
            linq_calls.append(payload or {})
            return {"message": {"id": "out_safe_answer"}}

        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ.pop("BAND_GATE_URL", None)
        queued = agent_runtime.ingest_webhook(
            json.dumps(
                webhook_payload(
                    "evt_band_product_answer", "How much is Mini Phone Stand?"
                )
            )
        )
        with patch.object(agent_runtime, "_linq_request", side_effect=fake_linq):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))

        self.assertEqual(result["band_gate_status"], "fail_closed")
        self.assertFalse(result["checkout_sent"])
        self.assertEqual(result["product_ids"], [])
        self.assertEqual(len(linq_calls), 1)
        safe_text = linq_calls[0]["message"]["parts"][0]["value"]
        self.assertNotIn("Mini Phone Stand", safe_text)
        self.assertIn("band_review_failed_closed", self.event_types())

    def test_status_is_degraded_when_enabled_band_url_is_missing(self) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ.pop("BAND_GATE_URL", None)
        status = agent_runtime.get_status()
        self.assertEqual(status["status"], "degraded")
        self.assertTrue(status["band_gate_enabled"])
        self.assertFalse(status["band_gate_configured"])

    def test_band_block_regenerates_and_reviews_fallback(self) -> None:
        linq_calls: list[dict[str, object]] = []
        reviews = [
            band_gate.BandReview(
                decision="BLOCK", review_id="evt_band_fallback:band:1", reason="blocked"
            ),
            band_gate.BandReview(
                decision="APPROVE",
                review_id="evt_band_fallback:band:2",
                reason="approved",
            ),
        ]

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del method, path, timeout_seconds
            linq_calls.append(payload or {})
            return {"message": {"id": f"out_{len(linq_calls)}"}}

        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        os.environ["BAND_GATE_ENABLED"] = "true"
        os.environ["BAND_GATE_URL"] = "https://band.example.test"
        queued = agent_runtime.ingest_webhook(
            json.dumps(webhook_payload("evt_band_fallback", "Show me something under $20"))
        )
        with (
            patch.object(band_gate, "review_candidate", side_effect=reviews),
            patch.object(agent_runtime, "_linq_request", side_effect=fake_linq),
        ):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))

        self.assertEqual(result["band_gate_status"], "approved_fallback")
        self.assertEqual(result["product_ids"], ["prod_phone"])
        self.assertTrue(result["checkout_sent"])
        checkout = linq_calls[1]["message"]["parts"][0]
        self.assertEqual(checkout["value"], "https://buy.stripe.com/test_fixture_phone")
        event_types = self.event_types()
        self.assertEqual(event_types.count("product_selected"), 2)
        self.assertEqual(event_types.count("band_review_requested"), 2)
        self.assertEqual(event_types.count("band_review_blocked"), 1)
        self.assertEqual(event_types.count("band_review_approved"), 1)

    def test_concurrent_processing_reservation_sends_once(self) -> None:
        calls: list[dict[str, object]] = []
        calls_lock = threading.Lock()

        def fake_linq(
            method: str,
            path: str,
            payload: dict[str, object] | None = None,
            timeout_seconds: float = 6.0,
        ) -> dict[str, object]:
            del method, path, timeout_seconds
            time.sleep(0.03)
            with calls_lock:
                calls.append(payload or {})
            return {"message": {"id": f"out_{len(calls)}"}}

        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_concurrent")))
        event_id = str(queued["event_id"])
        with patch.object(agent_runtime, "_linq_request", side_effect=fake_linq):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(agent_runtime.process_pending_event, [event_id, event_id]))
        self.assertEqual(len(calls), 2)
        self.assertEqual(sum(bool(item.get("processed")) for item in results), 1)

    def test_conversation_events_are_processed_in_arrival_order(self) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        first = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_first")))
        time.sleep(0.002)
        second = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_second")))
        with patch.object(
            agent_runtime,
            "_linq_request",
            return_value={"message": {"id": "out_fixture"}},
        ) as request:
            waiting = agent_runtime.process_pending_event(str(second["event_id"]))
            self.assertEqual(waiting["reason"], "earlier_conversation_event")
            request.assert_not_called()
            self.assertTrue(agent_runtime.process_pending_event(str(first["event_id"]))["processed"])
            self.assertTrue(agent_runtime.process_pending_event(str(second["event_id"]))["processed"])

    def test_failed_hot_reload_preserves_last_known_good(self) -> None:
        version = agent_runtime.ACTIVE_CATALOG.version
        self.catalog_path.write_text('{"not":"a catalog"}', encoding="utf-8")
        result = agent_runtime.refresh_catalog(force=True)
        self.assertEqual(result["error"], "catalog_validation_failed")
        self.assertEqual(agent_runtime.ACTIVE_CATALOG.version, version)

    def test_catalog_url_loads_a_valid_remote_catalog(self) -> None:
        catalog_json = json.dumps(CATALOG).encode()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(catalog_json)))
                self.end_headers()
                self.wfile.write(catalog_json)

            def log_message(self, format: str, *args: object) -> None:
                del format, args

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["CATALOG_URL"] = f"http://127.0.0.1:{server.server_port}/catalog.json"
        try:
            result = agent_runtime.refresh_catalog(force=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)

        self.assertTrue(result["reloaded"])
        self.assertEqual(result["source"], "catalog_url")
        self.assertEqual(len(agent_runtime.ACTIVE_CATALOG.products), 2)
        self.assertEqual(agent_runtime.ACTIVE_CATALOG_SOURCE, "catalog_url")

    def test_production_mode_never_falls_back_to_example_catalog(self) -> None:
        os.environ["PRODUCTION_MODE"] = "true"
        os.environ["CATALOG_PATH"] = str(self.root / "missing-production-catalog.json")
        agent_runtime.ACTIVE_CATALOG = None
        agent_runtime.ACTIVE_CATALOG_SOURCE = ""
        result = agent_runtime.refresh_catalog(force=True)

        self.assertEqual(result["error"], "catalog_validation_failed")
        self.assertEqual(result["catalog_products"], 0)
        self.assertIsNone(agent_runtime.ACTIVE_CATALOG)

    def test_event_sink_failure_cannot_block_sale(self) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        os.environ["EVENT_SINK_URL"] = "http://127.0.0.1:1/events"
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_sink")))
        with patch.object(
            agent_runtime,
            "_linq_request",
            return_value={"message": {"id": "out_fixture"}},
        ):
            result = process_linq_event(str(queued["event_id"]))
        self.assertTrue(result["processed"])
        self.assertTrue(result["checkout_sent"])
        self.assertGreater(len(list((self.root / "data" / "event_outbox").glob("*.json"))), 0)

    def test_rate_limit_stays_pending_for_recovery(self) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_429")))
        with patch.object(
            agent_runtime, "_linq_request", side_effect=RuntimeError("linq_http_429")
        ):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))
        self.assertFalse(result["processed"])
        self.assertEqual(agent_runtime.pending_event_ids(), ["evt_429"])

    def test_permanent_four_xx_is_dead_lettered(self) -> None:
        os.environ["LINQ_API_KEY"] = "fixture-not-a-secret"
        queued = agent_runtime.ingest_webhook(json.dumps(webhook_payload("evt_403")))
        with patch.object(
            agent_runtime, "_linq_request", side_effect=RuntimeError("linq_http_403")
        ):
            result = agent_runtime.process_pending_event(str(queued["event_id"]))
        self.assertTrue(result["processed"])
        self.assertEqual(agent_runtime.pending_event_ids(), [])


if __name__ == "__main__":
    unittest.main()
