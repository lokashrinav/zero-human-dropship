import httpx
import os
from datetime import datetime

BAND_API_KEY = os.getenv("BAND_API_KEY", "")
BAND_ROOM_ID = os.getenv("BAND_ROOM_ID", "")
BAND_BASE = "https://openapi.band.us"


async def post_message(agent_name: str, message: str):
    """Post a decision/status update to the Band room."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {agent_name}: {message}"
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{BAND_BASE}/v2.2/band/post/create",
            params={
                "access_token": BAND_API_KEY,
                "band_key": BAND_ROOM_ID,
                "content": formatted,
                "do_push": "false",
            },
        )


async def read_recent_posts(limit: int = 20) -> list[dict]:
    """Read recent posts from the Band room."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BAND_BASE}/v2/band/posts",
            params={
                "access_token": BAND_API_KEY,
                "band_key": BAND_ROOM_ID,
                "limit": limit,
            },
        )
        data = resp.json()
        posts = data.get("result_data", {}).get("items", [])
        return [
            {
                "content": p.get("content", ""),
                "created_at": p.get("created_at", 0),
                "author": p.get("author", {}).get("name", ""),
            }
            for p in posts
        ]
