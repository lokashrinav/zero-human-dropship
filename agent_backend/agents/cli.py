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
import os
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


STORE_CATALOG_URL = "https://storefront-omega-three.vercel.app/api/catalog"


async def _catalog_fallback() -> list[dict]:
    """Read-only catalog from the live storefront when no Stripe key is set.
    Lets the CEO observe (not reprice) before credentials land."""
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(os.getenv("STORE_CATALOG_URL", STORE_CATALOG_URL))
        resp.raise_for_status()
        items = resp.json()
    return [
        {
            "product_id": p.get("stripe_id", p.get("id", "")),
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "images": p.get("images", []),
            "price_cents": int(round(float(p.get("price", 0)) * 100)),
            "price_id": "",
            "payment_link_url": p.get("payment_link", ""),
            "cost_cents": 0,  # unknown without Stripe metadata
            "cj_product_id": "",
            "read_only": True,
        }
        for p in items
        if p.get("active", True)
    ]


async def observe() -> dict:
    catalog_source = "stripe"
    try:
        products, sales = await asyncio.gather(
            asyncio.to_thread(list_products),
            asyncio.to_thread(get_sales_summary, max(1, _env_int("CEO_SALES_WINDOW_HOURS", 24))),
        )
    except RuntimeError:  # STRIPE_SECRET_KEY not configured
        products = await _catalog_fallback()
        sales = {"orders": 0, "gross_revenue_cents": 0, "units": 0, "by_product": [],
                 "note": "no Stripe key — revenue unavailable, catalog read-only from storefront"}
        catalog_source = "storefront_catalog(read_only)"
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
        "catalog_source": catalog_source,
        "context": _build_context(products, sales, band_posts, feedback, trigger="claude-code"),
        "products": products,
        "sales": sales,
        "recent_activity": band_posts,
        "terac_feedback": feedback,
    }


async def act(raw_actions: str, dry_run: bool) -> dict:
    decisions = parse_decisions(raw_actions)
    try:
        products = await asyncio.to_thread(list_products)
    except RuntimeError:
        # No Stripe key: catalog is read-only. Only log-style actions make sense;
        # guardrails will reject product mutations against this catalog anyway.
        products = await _catalog_fallback()
        dry_run = dry_run or any(
            d.get("action") in {"drop_product", "reprice"} for d in decisions
        )
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
