"""Solari cloud browsers — parallel browser capacity that never touches the
operator's Chrome. Use for anonymous tasks: storefront verification, listing
checks, price audits. Logged-in tasks (FB, eBay) stay on local Chrome.

CLI:  python -m tools.solari_tools check <url>     # fetch page via cloud browser
Docs: https://docs.getsolari.com
"""
import asyncio
import json
import os
import sys

import httpx

SOLARI_API = "https://api.getsolari.com"


def _headers() -> dict:
    key = os.getenv("SOLARI_API_KEY", "")
    if not key:
        raise RuntimeError("SOLARI_API_KEY is not configured")
    return {"Authorization": f"Bearer {key}"}


async def create_session(stealth: bool = False) -> dict:
    """Create a cloud browser session. Returns sessionId + cdpEndpoint/wsEndpoint."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{SOLARI_API}/sessions", headers=_headers(), json={"stealth": stealth})
        resp.raise_for_status()
        return resp.json()


async def end_session(session_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        await client.delete(f"{SOLARI_API}/sessions/{session_id}", headers=_headers())


async def check_page(url: str) -> dict:
    """Load a page in a fresh cloud browser, return title + visible text head.
    The standard smoke check for 'does our storefront/listing actually render'."""
    from playwright.async_api import async_playwright

    session = await create_session()
    session_id = session.get("sessionId", session.get("id", ""))
    cdp = session.get("cdpEndpoint") or session.get("wsEndpoint")
    if not cdp:
        await end_session(session_id)
        raise RuntimeError(f"no CDP endpoint in session response: {list(session.keys())}")

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(cdp)
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            title = await page.title()
            text = (await page.inner_text("body"))[:1500]
            await browser.close()
        return {"url": url, "title": title, "text_head": text, "session_id": session_id}
    finally:
        try:
            await end_session(session_id)
        except httpx.HTTPError:
            pass


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    if len(sys.argv) >= 3 and sys.argv[1] == "check":
        out = asyncio.run(check_page(sys.argv[2]))
        print(json.dumps(out, indent=2)[:3000])
    else:
        print(__doc__)
        sys.exit(2)
