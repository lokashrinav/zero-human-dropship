"""Quick live smoke test of the sponsor APIs we have keys for.
Run: python test_apis.py
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_pioneer():
    from tools.pioneer_tools import generate_description
    try:
        desc = await generate_description("LED galaxy star projector night light", "home decor")
        print(f"PIONEER  OK: {desc[:120]}")
        return True
    except Exception as e:
        print(f"PIONEER  FAIL: {e}")
        return False


async def test_linq():
    key = os.getenv("LINQ_API_KEY", "")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.linqapp.com/api/partner/v3/webhook-subscriptions",
                headers={"Authorization": f"Bearer {key}"},
            )
            if resp.status_code in (200, 404):
                print(f"LINQ     OK: auth accepted (status {resp.status_code}): {resp.text[:150]}")
                return True
            print(f"LINQ     FAIL: status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"LINQ     FAIL: {e}")
        return False


async def test_solari():
    key = os.getenv("SOLARI_API_KEY", "")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.getsolari.com/health",
                headers={"Authorization": f"Bearer {key}"},
            )
            print(f"SOLARI   health: {resp.status_code}: {resp.text[:100]}")
            # health may be unauthenticated; try creating+deleting a session to verify the key
            resp2 = await client.post(
                "https://api.getsolari.com/sessions",
                headers={"Authorization": f"Bearer {key}"},
                json={},
            )
            if resp2.status_code in (200, 201):
                session = resp2.json()
                sid = session.get("sessionId", session.get("id", ""))
                print(f"SOLARI   OK: session created: {sid}")
                if sid:
                    await client.delete(
                        f"https://api.getsolari.com/sessions/{sid}",
                        headers={"Authorization": f"Bearer {key}"},
                    )
                    print(f"SOLARI   session cleaned up")
                return True
            print(f"SOLARI   FAIL: session create {resp2.status_code}: {resp2.text[:200]}")
            return False
    except Exception as e:
        print(f"SOLARI   FAIL: {e}")
        return False


async def test_decision_log():
    from tools.band_tools import post_message, read_local_log
    await post_message("TestAgent", "smoke test entry")
    entries = read_local_log(5)
    ok = any(e["agent"] == "TestAgent" for e in entries)
    print(f"DECISION LOG {'OK' if ok else 'FAIL'}: {len(entries)} entries")
    return ok


async def main():
    results = await asyncio.gather(
        test_pioneer(),
        test_linq(),
        test_solari(),
        test_decision_log(),
    )
    print(f"\n{sum(results)}/{len(results)} passed")


if __name__ == "__main__":
    asyncio.run(main())
