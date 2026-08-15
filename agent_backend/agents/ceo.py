"""Revenue CEO agent: observe sales, choose guarded actions, and execute them.

Run continuously with ``python -m agents.ceo``. Set ``CEO_EXECUTE_ACTIONS=true``
only after inspecting at least one dry-run cycle.
"""

import asyncio
import json
import math
import os
from typing import Any

from tools.band_tools import post_message, read_recent_posts
from tools.stripe_tools import (
    deactivate_product,
    get_sales_summary,
    list_products,
    update_price,
)
from tools.terac_tools import list_submissions


SYSTEM_PROMPT = """You are the revenue CEO of an autonomous dropshipping business.
Choose a few high-confidence actions based only on the evidence provided. Optimize for
gross profit and learning speed, not vanity metrics. Never infer traffic or conversion
data that is not present. Preserve products that are selling. When evidence is weak,
prefer one reversible experiment over sweeping catalog changes.

Available actions:
- {"action":"drop_product","product_id":"...","reason":"..."}
- {"action":"reprice","product_id":"...","new_price_cents":1299,"reason":"..."}
- {"action":"source_new","query":"specific product search","reason":"..."}
- {"action":"shift_focus","channel":"store|stripe_payment_links|linq|facebook_marketplace|social","reason":"..."}
- {"action":"no_action","reason":"..."}

Return only a JSON array. Use product IDs exactly as supplied. Prices are integer cents.
Do not drop a product merely because it has no sales unless actual traffic data proves it
had a fair test. Do not claim that an action happened; the execution layer handles it."""

_run_lock = asyncio.Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _model_client():
    import anthropic  # Lazy: only the headless API loop needs it, not the Claude Code CLI.

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=api_key)


def _call_model(context: str) -> str:
    response = _model_client().messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        max_tokens=1200,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    text_blocks = [
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ]
    if not text_blocks:
        raise RuntimeError("CEO model returned no text")
    return "\n".join(text_blocks)


def parse_decisions(raw_text: str) -> list[dict[str, Any]]:
    """Parse a model response without accepting prose around arbitrary JSON."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("CEO response was not a JSON array") from exc

    if isinstance(payload, dict) and isinstance(payload.get("actions"), list):
        payload = payload["actions"]
    if not isinstance(payload, list):
        raise ValueError("CEO response must be a JSON array")
    if not all(isinstance(item, dict) for item in payload):
        raise ValueError("Every CEO action must be a JSON object")
    return payload


def validate_decisions(
    decisions: list[dict[str, Any]], products: list[dict]
) -> tuple[list[dict], list[dict]]:
    """Apply deterministic catalog, price, and blast-radius guardrails."""
    catalog = {product["product_id"]: product for product in products}
    max_actions = max(1, _env_int("CEO_MAX_ACTIONS_PER_CYCLE", 3))
    min_price = max(1, _env_int("CEO_MIN_PRICE_CENTS", 500))
    max_price = max(min_price, _env_int("CEO_MAX_PRICE_CENTS", 50000))
    min_margin_percent = max(0, _env_int("CEO_MIN_MARGIN_PERCENT", 30))
    max_price_change_percent = max(1, _env_int("CEO_MAX_PRICE_CHANGE_PERCENT", 35))
    valid: list[dict] = []
    rejected: list[dict] = []
    touched_products: set[str] = set()

    for index, raw in enumerate(decisions):
        action = str(raw.get("action", "")).strip().lower()
        reason = str(raw.get("reason", "")).strip()[:500]
        rejection = {"action": action or "unknown", "status": "rejected", "reason": reason}

        if index >= max_actions:
            rejected.append({**rejection, "error": f"cycle limit is {max_actions} actions"})
            continue
        if not reason:
            rejected.append({**rejection, "error": "reason is required"})
            continue
        if action not in {"drop_product", "reprice", "source_new", "shift_focus", "no_action"}:
            rejected.append({**rejection, "error": "unknown action"})
            continue

        normalized = {"action": action, "reason": reason}
        if action in {"drop_product", "reprice"}:
            product_id = str(raw.get("product_id", "")).strip()
            if product_id not in catalog:
                rejected.append({**rejection, "product_id": product_id, "error": "unknown product"})
                continue
            if product_id in touched_products:
                rejected.append(
                    {**rejection, "product_id": product_id, "error": "product already changed this cycle"}
                )
                continue
            normalized["product_id"] = product_id

            if action == "drop_product" and len(catalog) <= 1:
                rejected.append({**normalized, "status": "rejected", "error": "cannot drop the last product"})
                continue

            if action == "reprice":
                raw_price = raw.get("new_price_cents")
                if isinstance(raw_price, bool):
                    new_price = -1
                else:
                    try:
                        new_price = int(raw_price)
                    except (TypeError, ValueError):
                        new_price = -1
                product = catalog[product_id]
                cost_cents = max(0, int(product.get("cost_cents", 0)))
                margin_floor = math.ceil(cost_cents * (1 + min_margin_percent / 100))
                effective_floor = max(min_price, margin_floor)
                if not effective_floor <= new_price <= max_price:
                    rejected.append(
                        {
                            **normalized,
                            "new_price_cents": new_price,
                            "status": "rejected",
                            "error": f"price must be between {effective_floor} and {max_price} cents",
                        }
                    )
                    continue
                current_price = int(product.get("price_cents", 0))
                if current_price > 0:
                    change_percent = abs(new_price - current_price) * 100 / current_price
                    if change_percent > max_price_change_percent:
                        rejected.append(
                            {
                                **normalized,
                                "new_price_cents": new_price,
                                "status": "rejected",
                                "error": (
                                    f"price change {change_percent:.1f}% exceeds "
                                    f"{max_price_change_percent}% cycle limit"
                                ),
                            }
                        )
                        continue
                normalized["new_price_cents"] = new_price
            touched_products.add(product_id)

        elif action == "source_new":
            query = " ".join(str(raw.get("query", "")).split())[:100]
            if len(query) < 3:
                rejected.append({**rejection, "error": "source query is too short"})
                continue
            normalized["query"] = query

        elif action == "shift_focus":
            channel = str(raw.get("channel", "")).strip().lower()
            allowed_channels = {
                "store",
                "stripe_payment_links",
                "linq",
                "facebook_marketplace",
                "social",
            }
            if channel not in allowed_channels:
                rejected.append({**rejection, "channel": channel, "error": "unsupported channel"})
                continue
            normalized["channel"] = channel

        valid.append(normalized)

    if not valid and not rejected:
        rejected.append(
            {"action": "no_action", "status": "rejected", "reason": "", "error": "empty action list"}
        )
    return valid, rejected


async def execute_decisions(
    decisions: list[dict[str, Any]], products: list[dict], execute_actions: bool
) -> list[dict]:
    """Validate and optionally execute one bounded set of CEO actions."""
    valid, results = validate_decisions(decisions, products)
    max_source_products = max(1, _env_int("CEO_MAX_PRODUCTS_PER_SOURCE_ACTION", 1))

    for decision in valid:
        result = {**decision, "status": "planned" if not execute_actions else "executed"}
        if not execute_actions or decision["action"] == "no_action":
            if decision["action"] == "no_action":
                result["status"] = "no_action"
            results.append(result)
            continue

        try:
            if decision["action"] == "drop_product":
                await asyncio.to_thread(deactivate_product, decision["product_id"])
            elif decision["action"] == "reprice":
                update = await asyncio.to_thread(
                    update_price,
                    decision["product_id"],
                    decision["new_price_cents"],
                )
                result["payment_link_url"] = update["payment_link_url"]
            elif decision["action"] == "source_new":
                # Import lazily so a read-only decision cycle does not initialize CJ.
                from agents.sourcing import source_products

                created = await source_products(
                    [decision["query"]], max_per_query=max_source_products
                )
                result["created_products"] = [
                    {
                        "product_id": item["product_id"],
                        "name": item["name"],
                        "payment_link_url": item["payment_link_url"],
                    }
                    for item in created
                ]
            elif decision["action"] == "shift_focus":
                # Channel execution belongs to the sales worker; Band is its command bus.
                await post_message(
                    "CEO",
                    f"Growth directive: focus {decision['channel']}. {decision['reason']}",
                )
                result["status"] = "dispatched"
        except Exception as exc:  # Keep later independent actions runnable.
            result["status"] = "failed"
            result["error"] = str(exc)[:500]
        results.append(result)
    return results


async def run_decision_loop(execute_actions: bool | None = None, trigger: str = "manual") -> dict:
    """Run one observable, model-decided, deterministically guarded revenue cycle."""
    if _run_lock.locked():
        raise RuntimeError("a CEO decision cycle is already running")
    async with _run_lock:
        if execute_actions is None:
            execute_actions = _env_bool("CEO_EXECUTE_ACTIONS", False)

        products, sales = await asyncio.gather(
            asyncio.to_thread(list_products),
            asyncio.to_thread(
                get_sales_summary,
                max(1, _env_int("CEO_SALES_WINDOW_HOURS", 24)),
            ),
        )
        band_posts = await read_recent_posts(limit=30)

        feedback: list[dict] = []
        opportunity_id = os.getenv("TERAC_OPPORTUNITY_ID", "").strip()
        if opportunity_id:
            try:
                feedback = await list_submissions(opportunity_id)
            except Exception as exc:
                await post_message("CEO", f"Terac read failed; continuing with sales data: {exc}")

        context = _build_context(products, sales, band_posts, feedback, trigger)
        model_output = await asyncio.to_thread(_call_model, context)
        decisions = parse_decisions(model_output)
        results = await execute_decisions(decisions, products, execute_actions)

        summary = {
            "trigger": trigger,
            "mode": "execute" if execute_actions else "dry_run",
            "sales": sales,
            "actions": results,
        }
        await post_message("CEO", f"Revenue cycle complete:\n{json.dumps(summary, separators=(',', ':'))}")
        return summary


def _build_context(
    products: list[dict],
    sales: dict,
    band_posts: list[dict],
    feedback: list[dict],
    trigger: str,
) -> str:
    sales_by_product = {
        metric["product_id"]: metric for metric in sales.get("by_product", [])
    }
    product_lines = []
    for product in products:
        metric = sales_by_product.get(product["product_id"], {})
        revenue = int(metric.get("revenue_cents", 0))
        units = int(metric.get("units", 0))
        estimated_profit = revenue - (units * int(product.get("cost_cents", 0)))
        product_lines.append(
            "  - "
            f"{product['product_id']} | {product['name']} | "
            f"price=${product['price_cents'] / 100:.2f} | "
            f"cost=${product.get('cost_cents', 0) / 100:.2f} | "
            f"units={units} | revenue=${revenue / 100:.2f} | "
            f"estimated_gross_profit=${estimated_profit / 100:.2f}"
        )

    recent_posts = [post.get("content", "")[:500] for post in band_posts[:10]]
    feedback_excerpt = feedback[:20]
    return f"""Trigger: {trigger}
Sales window: {sales.get('window_hours', 24)} hours
Paid orders: {sales.get('orders', 0)}
Gross revenue: ${sales.get('gross_revenue_cents', 0) / 100:.2f}

Catalog ({len(products)} products):
{chr(10).join(product_lines) if product_lines else '  No products are live.'}

Recent operator/channel activity (may be empty):
{json.dumps(recent_posts)}

Customer research submissions (may be empty):
{json.dumps(feedback_excerpt, default=str)[:6000]}

Important evidence limit: product views, clicks, and conversion rates are not available.
Do not describe an unsold product as having zero traffic. Return at most
{max(1, _env_int('CEO_MAX_ACTIONS_PER_CYCLE', 3))} actions."""


async def ceo_loop(interval_minutes: int | None = None) -> None:
    """Run revenue cycles continuously until the process is stopped."""
    interval = interval_minutes or max(1, _env_int("CEO_LOOP_INTERVAL_MINUTES", 15))
    while True:
        try:
            result = await run_decision_loop(trigger="scheduled")
            print(
                f"CEO cycle complete ({result['mode']}): "
                f"{len(result['actions'])} action result(s)"
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"CEO cycle error: {exc}")
            await post_message("CEO", f"Error in decision cycle: {exc}")
        await asyncio.sleep(interval * 60)


if __name__ == "__main__":
    asyncio.run(ceo_loop())
