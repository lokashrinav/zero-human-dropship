"""Terac API — v2 beta. Resources are 'opportunities' (studies) and 'submissions' (results).
Rate limit: 100 req/min. NOTE: hackathon provides Terac via MCP — prefer the MCP tools
in Claude Code sessions; this module is for the deployed backend's automated loops.
"""
import httpx
import os

TERAC_API_KEY = os.getenv("TERAC_API_KEY", "")
TERAC_BASE = "https://terac.com/api/external/v2"


def _headers() -> dict:
    return {"Authorization": f"Bearer {TERAC_API_KEY}"}


async def create_opportunity(title: str, description: str, questions: list[dict]) -> dict:
    """Create a study (opportunity). questions = [{"text": "...", "type": "rating"}, ...]"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{TERAC_BASE}/createOpportunity",
            headers=_headers(),
            json={"title": title, "description": description, "questions": questions},
        )
        return resp.json()


async def launch_opportunity(opportunity_id: str) -> dict:
    """Launch a created opportunity to the panel."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{TERAC_BASE}/launchOpportunity",
            headers=_headers(),
            json={"opportunityId": opportunity_id},
        )
        return resp.json()


async def list_submissions(opportunity_id: str) -> list[dict]:
    """Get all submissions (results) for an opportunity."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{TERAC_BASE}/listSubmissions",
            headers=_headers(),
            params={"opportunityId": opportunity_id},
        )
        data = resp.json()
        return data.get("submissions", data if isinstance(data, list) else [])
