"""Agent decision/status log. Band API when configured; local JSONL fallback otherwise
(Band signup was broken at hackathon start). The local log is served at /api/decisions
so the demo dashboard gets the audit trail either way.
"""
import httpx
import json
import os
import time
from datetime import datetime
from pathlib import Path

BAND_API_KEY = os.getenv("BAND_API_KEY", "")
BAND_ROOM_ID = os.getenv("BAND_ROOM_ID", "")
BAND_BASE = "https://openapi.band.us"

LOCAL_LOG = Path(__file__).resolve().parent.parent / "decision_log.jsonl"


def _log_local(agent_name: str, message: str):
    entry = {
        "ts": time.time(),
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent_name,
        "message": message,
    }
    with LOCAL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_local_log(limit: int = 50) -> list[dict]:
    if not LOCAL_LOG.exists():
        return []
    lines = LOCAL_LOG.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines[-limit:]]


async def post_message(agent_name: str, message: str):
    """Post a decision/status update. Always logs locally; mirrors to the deployed
    backend when BACKEND_URL is set, and to Band if configured."""
    _log_local(agent_name, message)

    backend_url = os.getenv("BACKEND_URL", "").rstrip("/")
    if backend_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{backend_url}/api/log",
                    json={"agent": agent_name, "message": message},
                )
        except httpx.HTTPError:
            pass  # local log already has it

    if not BAND_API_KEY:
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {agent_name}: {message}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BAND_BASE}/v2.2/band/post/create",
                params={
                    "access_token": BAND_API_KEY,
                    "band_key": BAND_ROOM_ID,
                    "content": formatted,
                    "do_push": "false",
                },
            )
    except httpx.HTTPError:
        pass  # local log already has it


async def read_recent_posts(limit: int = 20) -> list[dict]:
    """Read recent agent activity. Local log is the source of truth."""
    local = read_local_log(limit)
    return [
        {"content": f"[{e['time']}] {e['agent']}: {e['message']}", "created_at": e["ts"], "author": e["agent"]}
        for e in local
    ]
