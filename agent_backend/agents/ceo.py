"""CEO agent: reads Stripe + Terac + Band, makes decisions, dispatches actions.
Run directly: python -m agents.ceo
"""
import asyncio
import os
import anthropic
from tools.stripe_tools import list_products, get_recent_charges, update_price, deactivate_product
from tools.band_tools import post_message, read_recent_posts
from tools.terac_tools import list_submissions


client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the CEO agent of an autonomous dropshipping business.
You make strategic decisions based on sales data, customer feedback, and market signals.

Your available actions (respond with JSON):
- {"action": "drop_product", "product_id": "...", "reason": "..."}
- {"action": "reprice", "product_id": "...", "new_price_cents": N, "reason": "..."}
- {"action": "source_new", "query": "...", "reason": "..."}
- {"action": "shift_focus", "channel": "...", "reason": "..."}
- {"action": "no_action", "reason": "..."}

Respond with a JSON array of actions. Be decisive. Log your reasoning."""


async def run_decision_loop():
    """One iteration of the CEO decision loop."""
    products = list_products()
    charges = get_recent_charges(limit=50)
    band_posts = await read_recent_posts(limit=30)

    context = f"""Current products ({len(products)}):
{_format_products(products)}

Recent charges ({len(charges)}):
{_format_charges(charges)}

Recent Band activity:
{_format_posts(band_posts)}

Time pressure: we have limited hours. Products with zero traction should be dropped.
Products priced too high should be repriced. Gaps in catalog should trigger new sourcing."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    decisions_text = response.content[0].text
    await post_message("CEO", f"Decision cycle complete. Analysis:\n{decisions_text}")

    return decisions_text


def _format_products(products):
    if not products:
        return "No products yet."
    lines = []
    for p in products:
        lines.append(f"  - {p['name']} | ${p['price_cents']/100:.2f} | cost ${p['cost_cents']/100:.2f} | {p['product_id']}")
    return "\n".join(lines)


def _format_charges(charges):
    if not charges:
        return "No sales yet."
    lines = []
    for c in charges:
        lines.append(f"  - ${c['amount_cents']/100:.2f} | {c['description'] or 'no desc'}")
    return "\n".join(lines)


def _format_posts(posts):
    if not posts:
        return "No activity yet."
    return "\n".join(f"  - {p['content']}" for p in posts[:15])


async def ceo_loop(interval_minutes: int = 15):
    """Run CEO loop continuously."""
    while True:
        print(f"CEO decision cycle starting...")
        try:
            result = await run_decision_loop()
            print(f"CEO cycle complete: {result[:200]}...")
        except Exception as e:
            print(f"CEO cycle error: {e}")
            await post_message("CEO", f"Error in decision cycle: {e}")
        await asyncio.sleep(interval_minutes * 60)


if __name__ == "__main__":
    asyncio.run(ceo_loop())
