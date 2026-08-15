"""Pioneer (pioneer.ai) — OpenAI-compatible inference over open-weight models.
Auth: X-API-Key header. Docs: https://docs.pioneer.ai
"""
import httpx
import os

PIONEER_BASE = os.getenv("PIONEER_BASE_URL", "https://api.pioneer.ai/v1")
MODEL = os.getenv("PIONEER_MODEL", "zai-org/GLM-5.2-Fast")


def _headers() -> dict:
    return {"X-API-Key": os.getenv("PIONEER_API_KEY", "")}


async def generate_description(product_name: str, category: str = "") -> str:
    """Generate a compelling product description using Pioneer's open-weight model."""
    prompt = (
        f"Write a short, compelling e-commerce product description (2-3 sentences) for: {product_name}."
        f"{f' Category: {category}.' if category else ''}"
        " Focus on benefits, not features. Make it sound premium but accessible. "
        "Target impulse buyers. No markdown, no bullet points. Description only, no preamble."
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{PIONEER_BASE}/chat/completions",
            headers=_headers(),
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
