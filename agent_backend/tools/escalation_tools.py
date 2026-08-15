"""Non-blocking human escalation. The business NEVER stops: when an agent hits
a human-only wall (credential, payment approval, account action), it files an
escalation and moves on to other work. Humans drain the queue; agents retry
parked items each cycle.

CLI:  python -m tools.escalation_tools raise <Agent> "<what>" "<how_to_unblock>"
      python -m tools.escalation_tools list
      python -m tools.escalation_tools resolve <id>
"""
import json
import sys
import time
import uuid
from pathlib import Path

ESCALATIONS = Path(__file__).resolve().parent.parent / "escalations.jsonl"


def _load() -> list[dict]:
    if not ESCALATIONS.exists():
        return []
    return [json.loads(line) for line in ESCALATIONS.read_text(encoding="utf-8").strip().splitlines() if line]


def _save(items: list[dict]):
    ESCALATIONS.write_text("\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8")


async def escalate(agent: str, what: str, how_to_unblock: str) -> str:
    """File an escalation and KEEP GOING. Returns the escalation id."""
    from tools.band_tools import post_message

    eid = uuid.uuid4().hex[:8]
    items = _load()
    items.append({
        "id": eid, "ts": time.time(), "agent": agent,
        "what": what, "how_to_unblock": how_to_unblock, "status": "open",
    })
    _save(items)
    await post_message("ESCALATION", f"[{eid}] {agent} needs a human: {what} — TO UNBLOCK: {how_to_unblock}")
    return eid


def open_escalations() -> list[dict]:
    return [i for i in _load() if i["status"] == "open"]


def resolve(eid: str) -> bool:
    items = _load()
    for i in items:
        if i["id"] == eid and i["status"] == "open":
            i["status"] = "resolved"
            i["resolved_ts"] = time.time()
            _save(items)
            return True
    return False


if __name__ == "__main__":
    import asyncio

    from dotenv import load_dotenv

    load_dotenv()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "raise" and len(sys.argv) >= 5:
        eid = asyncio.run(escalate(sys.argv[2], sys.argv[3], sys.argv[4]))
        print(f"escalation filed: {eid} (business continues)")
    elif cmd == "list":
        for i in open_escalations():
            print(f"[{i['id']}] {i['agent']}: {i['what']} — UNBLOCK: {i['how_to_unblock']}")
        print(f"{len(open_escalations())} open")
    elif cmd == "resolve" and len(sys.argv) >= 3:
        print("resolved" if resolve(sys.argv[2]) else "not found / already resolved")
    else:
        print(__doc__)
        sys.exit(2)
