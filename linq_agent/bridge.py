"""Minimal ASGI boundary for Linq raw-body verification and Jac invocation."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Mapping

import jaclang  # noqa: F401 - installs the .jac import hook
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from sales_agent import (
    dashboard_events,
    enqueue_linq_webhook,
    initialize_service,
    process_linq_event,
    recover_pending_events,
    service_status,
)

LOGGER = logging.getLogger("linq-sales-agent")
SIGNATURE_TOLERANCE_SECONDS = 300
RECOVERY_INTERVAL_SECONDS = 15
MAX_WEBHOOK_BODY_BYTES = 1_048_576


async def recover_pending_loop() -> None:
    """Retry durable transient failures without depending on webhook redelivery."""

    while True:
        await asyncio.sleep(RECOVERY_INTERVAL_SECONDS)
        if os.getenv("LINQ_API_KEY"):
            await asyncio.to_thread(recover_pending_events, 50)


async def read_limited_body(request: Request) -> bytes:
    """Read the raw signed body without allowing unbounded allocation."""

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_WEBHOOK_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Webhook payload too large")
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from error
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Webhook payload too large")
    return bytes(body)


def verify_linq_signature(
    raw_body: bytes,
    headers: Mapping[str, str],
    signing_secret: str,
    *,
    now: int | None = None,
) -> bool:
    """Verify Linq's Standard Webhooks signature against the untouched body."""

    webhook_id = headers.get("webhook-id", "")
    timestamp_text = headers.get("webhook-timestamp", "")
    signature_header = headers.get("webhook-signature", "")
    if not webhook_id or not timestamp_text or not signature_header:
        return False
    try:
        timestamp = int(timestamp_text)
    except ValueError:
        return False
    current_time = int(time.time()) if now is None else now
    if abs(current_time - timestamp) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    if not signing_secret.startswith("whsec_"):
        return False
    encoded_secret = signing_secret.removeprefix("whsec_")
    try:
        secret_bytes = base64.b64decode(encoded_secret, validate=True)
    except (binascii.Error, ValueError):
        return False
    signed_payload = (
        webhook_id.encode("utf-8")
        + b"."
        + timestamp_text.encode("ascii")
        + b"."
        + raw_body
    )
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()
    ).decode("ascii")
    for candidate in signature_header.split():
        version, separator, supplied = candidate.partition(",")
        if separator and version == "v1" and hmac.compare_digest(expected, supplied):
            return True
    return False


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup = await asyncio.to_thread(initialize_service)
    catalog = startup.get("catalog", {})
    LOGGER.info(
        "Linq sales agent started; catalog_products=%s checkout_card=%s",
        catalog.get("catalog_products", 0) if isinstance(catalog, dict) else 0,
        bool(startup.get("link_experience_available")),
    )
    initial_recovery_task = asyncio.create_task(
        asyncio.to_thread(recover_pending_events, 50)
    ) if os.getenv("LINQ_API_KEY") else None
    recovery_task = asyncio.create_task(recover_pending_loop())
    try:
        yield
    finally:
        recovery_task.cancel()
        with suppress(asyncio.CancelledError):
            await recovery_task
        if initial_recovery_task is not None and not initial_recovery_task.done():
            initial_recovery_task.cancel()
            with suppress(asyncio.CancelledError):
                await initial_recovery_task


app = FastAPI(
    title="Zero Human — Jac Linq Sales Agent",
    version="0.1.0",
    lifespan=lifespan,
)


@app.post("/webhooks/linq", status_code=202)
async def linq_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await read_limited_body(request)
    signing_secret = os.getenv("LINQ_WEBHOOK_SECRET", "")
    if not signing_secret:
        raise HTTPException(status_code=503, detail="Webhook verification is not configured")
    if not verify_linq_signature(raw_body, request.headers, signing_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        raw_text = raw_body.decode("utf-8")
        result = await asyncio.to_thread(enqueue_linq_webhook, raw_text)
    except (UnicodeDecodeError, ValueError) as error:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from error
    event_id = result.get("event_id")
    if result.get("queued") and isinstance(event_id, str):
        background_tasks.add_task(process_linq_event, event_id)
    return result


@app.get("/api/status")
async def api_status():
    return await asyncio.to_thread(service_status)


@app.get("/api/events")
async def api_events(
    cursor: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=250),
):
    return await asyncio.to_thread(dashboard_events, cursor, limit)


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return JSONResponse({"status": "ok"})
