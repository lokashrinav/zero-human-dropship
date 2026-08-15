import httpx
import os

PIONEER_API_KEY = os.getenv("PIONEER_API_KEY", "")
PIONEER_BASE = os.getenv("PIONEER_BASE_URL", "https://api.pioneer.dev/v1")


async def generate_description(product_name: str, category: str = "") -> str:
    """Generate a compelling product description using Pioneer's open-weight model."""
    prompt = (
        f"Write a short, compelling e-commerce product description (2-3 sentences) for: {product_name}."
        f"{f' Category: {category}.' if category else ''}"
        " Focus on benefits, not features. Make it sound premium but accessible. "
        "Target impulse buyers. No markdown, no bullet points."
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{PIONEER_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {PIONEER_API_KEY}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
            },
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
