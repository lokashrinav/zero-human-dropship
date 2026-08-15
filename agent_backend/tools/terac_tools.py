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


async def request_human_task(title: str, instructions: str, deliverable: str) -> dict:
    """Dispatch a human for a step agents can't complete (account signup, phone
    verification, CAPTCHA-gated flows). The agent-blocked step becomes a Terac
    opportunity; the human reports the deliverable back as a submission.

    instructions: exact numbered steps, all values the human needs inline.
    deliverable: what the submission must contain to count as done.
    """
    created = await create_opportunity(
        title=title,
        description=f"{instructions}\n\nDELIVERABLE (required for approval): {deliverable}",
        questions=[{"text": f"Paste the deliverable here: {deliverable}", "type": "text"}],
    )
    opp_id = (
        created.get("opportunityId")
        or created.get("id")
        or created.get("data", {}).get("id", "")
    )
    if opp_id:
        await launch_opportunity(opp_id)
    return {"opportunity_id": opp_id, "raw": created}


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
