"""Narrow Pioneer HTTP and evidence I/O bridge for the Jac service."""

from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


API_BASE = "https://api.pioneer.ai"
EVIDENCE_PATH = Path(__file__).resolve().parent / "data" / "recent_runs.jsonl"
_EVIDENCE_LOCK = threading.Lock()


class PioneerUnavailable(RuntimeError):
    """Raised when authenticated Pioneer inference cannot be completed."""


def _api_key() -> str:
    key = os.environ.get("PIONEER_API_KEY", "").strip()
    if not key:
        raise PioneerUnavailable("PIONEER_API_KEY is not configured")
    return key


def _error_message(body: bytes, status: int) -> str:
    fallback = f"Pioneer HTTP {status}"
    try:
        payload = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return fallback
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return f"{fallback}: {error['message'][:240]}"
        detail = payload.get("detail")
        if isinstance(detail, dict) and isinstance(detail.get("message"), str):
            return f"{fallback}: {detail['message'][:240]}"
        for field in ("detail", "message"):
            if isinstance(payload.get(field), str):
                return f"{fallback}: {payload[field][:240]}"
    return fallback


def _request(
    path: str, payload: dict[str, Any] | None = None, timeout: int = 120
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        method="GET" if payload is None else "POST",
        headers={
            "X-API-Key": _api_key(),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        message = _error_message(error.read(16_384), error.code)
        raise PioneerUnavailable(message) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise PioneerUnavailable(
            f"Pioneer request failed: {type(error).__name__}"
        ) from None
    except json.JSONDecodeError:
        raise PioneerUnavailable("Pioneer returned invalid JSON") from None
    if not isinstance(parsed, dict):
        raise PioneerUnavailable("Pioneer returned an unexpected response shape")
    return parsed


def fetch_model_catalog() -> str:
    return json.dumps(
        _request("/base-models?supports_inference=true", timeout=30)
    )


def call_decoder(
    model_id: str, system_prompt: str, user_prompt: str, max_tokens: int
) -> str:
    response = _request(
        "/v1/chat/completions",
        {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": False,
        },
    )
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise PioneerUnavailable(
            "Pioneer decoder response had no message content"
        ) from None
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = [
            part.get("text", "") for part in content if isinstance(part, dict)
        ]
        joined = "".join(part for part in parts if isinstance(part, str))
        if joined.strip():
            return joined
    raise PioneerUnavailable("Pioneer decoder returned empty content")


def call_gliner(model_id: str, text: str) -> str:
    response = _request(
        "/inference",
        {
            "model_id": model_id,
            "text": text,
            "schema": {
                "entities": [
                    "product feature",
                    "material",
                    "size or dimensions",
                    "quantity",
                    "compatible device",
                    "certification",
                    "brand",
                    "performance claim",
                    "shipping promise",
                    "customer proof",
                    "discount claim",
                ]
            },
            "threshold": 0.45,
        },
    )
    return json.dumps(response)


def append_evidence_json(run_json: str) -> None:
    payload = json.loads(run_json)
    if not isinstance(payload, dict):
        raise ValueError("run evidence must be an object")
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _EVIDENCE_LOCK, EVIDENCE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_recent_evidence_json(limit: int) -> str:
    if not EVIDENCE_PATH.exists():
        return "[]"
    with _EVIDENCE_LOCK, EVIDENCE_PATH.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    rows: list[dict[str, Any]] = []
    for line in reversed(lines[-max(1, min(limit, 100)) :]):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return json.dumps(rows)
