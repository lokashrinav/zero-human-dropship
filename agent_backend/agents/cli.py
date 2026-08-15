"""CEO cockpit for a Claude Code session — no ANTHROPIC_API_KEY needed.

The Claude Code session IS the decision model. It runs:

  python -m agents.cli observe
      → prints the evidence bundle (catalog, sales, activity, Terac feedback)

  python -m agents.cli act '[{"action":"reprice","product_id":"prod_x","new_price_cents":999,"reason":"..."}]'
  python -m agents.cli act - < actions.json
      → validates through the same deterministic guardrails as the headless
        loop (price caps, margin floors, blast radius) and executes.
        Pass --dry-run to validate without executing.

agents/ceo.py (anthropic API loop) remains as the headless fallback.
"""

import asyncio
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from agents.ceo import (  # noqa: E402
    _build_context,
    _env_int,
    execute_decisions,
    parse_decisions,
)
from tools.band_tools import post_message, read_recent_posts  # noqa: E402
from tools.stripe_tools import get_sales_summary, list_products  # noqa: E402


async def observe() -> dict:
    import os

    products, sales = await asyncio.gather(
        asyncio.to_thread(list_products),
        asyncio.to_thread(get_sales_summary, max(1, _env_int("CEO_SALES_WINDOW_HOURS", 24))),
    )
    band_posts = await read_recent_posts(limit=30)

    feedback: list[dict] = []
    opportunity_id = os.getenv("TERAC_OPPORTUNITY_ID", "").strip()
    if opportunity_id:
        try:
            from tools.terac_tools import list_submissions

            feedback = await list_submissions(opportunity_id)
        except Exception as exc:
            feedback = [{"error": f"Terac read failed: {exc}"}]

    return {
        "context": _build_context(products, sales, band_posts, feedback, trigger="claude-code"),
        "products": products,
        "sales": sales,
        "recent_activity": band_posts,
        "terac_feedback": feedback,
    }


async def act(raw_actions: str, dry_run: bool) -> dict:
    decisions = parse_decisions(raw_actions)
    products = await asyncio.to_thread(list_products)
    results = await execute_decisions(decisions, products, execute_actions=not dry_run)
    summary = {"mode": "dry_run" if dry_run else "execute", "actions": results}
    await post_message("CEO", f"Claude Code cycle:\n{json.dumps(summary, separators=(',', ':'))}")
    return summary


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in {"observe", "act"}:
        print(__doc__)
        sys.exit(2)

    if args[0] == "observe":
        print(json.dumps(asyncio.run(observe()), indent=2, default=str))
        return

    dry_run = "--dry-run" in args
    positional = [a for a in args[1:] if a != "--dry-run"]
    if not positional:
        print("act requires a JSON array argument, or '-' to read stdin", file=sys.stderr)
        sys.exit(2)
    raw = sys.stdin.read() if positional[0] == "-" else positional[0]
    print(json.dumps(asyncio.run(act(raw, dry_run)), indent=2, default=str))


if __name__ == "__main__":
    main()
