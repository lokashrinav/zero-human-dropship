import httpx
import os

TERAC_API_KEY = os.getenv("TERAC_API_KEY", "")
TERAC_BASE = "https://api.terac.com/v1"


async def create_study(title: str, questions: list[dict], audience: str = "general_population") -> dict:
    """Create a Terac study. questions = [{"text": "...", "type": "rating_1_5"}, ...]"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TERAC_BASE}/studies",
            headers={"Authorization": f"Bearer {TERAC_API_KEY}"},
            json={
                "title": title,
                "audience": audience,
                "questions": questions,
            },
        )
        return resp.json()


async def get_study_results(study_id: str) -> dict:
    """Get results for a completed/in-progress study."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TERAC_BASE}/studies/{study_id}/results",
            headers={"Authorization": f"Bearer {TERAC_API_KEY}"},
        )
        return resp.json()
