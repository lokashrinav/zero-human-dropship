import json
import os
import stripe
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from revenue_sprint.router import router as revenue_router

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

app = FastAPI(title="Zero Human Dropship — Agent Backend")
app.include_router(revenue_router)


# ── Integration endpoint for Person B ──────────────────────────
# Person B's Linq handler (any language) calls GET /api/products
# to get all active products with payment links.

@app.get("/api/products")
async def get_products():
    """Returns all active products. This is how Person B's code gets product data.
    Works from any language — it's just a GET request."""
    from tools.stripe_tools import list_products
    return list_products()


# ── Stripe webhook ─────────────────────────────────────────────

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe events — payment success triggers fulfillment."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        from revenue_sprint import get_tracker

        # Attribution is local and idempotent. Sessions not created from a
        # revenue-sprint link are ignored.
        get_tracker().record_checkout_conversion(dict(session))
        await handle_payment(session)

    return {"status": "ok"}


async def handle_payment(session: dict):
    """On successful payment: log to Band, trigger CJ fulfillment."""
    from tools.band_tools import post_message
    from agents.ops import fulfill_order

    amount = session.get("amount_total", 0) / 100
    customer_email = session.get("customer_details", {}).get("email", "")

    await post_message("OpsAgent", f"Payment received: ${amount:.2f} from {customer_email}")

    session_full = stripe.checkout.Session.retrieve(session["id"], expand=["line_items.data.price.product"])
    await fulfill_order({
        "shipping_details": session.get("shipping_details", {}),
        "line_items": {"data": [
            {"price": {"product": li.price.product.id}}
            for li in session_full.line_items.data
        ]},
    })


# ── Decision log for dashboard ─────────────────────────────────

@app.get("/api/decisions")
async def get_decisions(limit: int = 50):
    """Agent decision audit trail — the demo dashboard polls this."""
    from tools.band_tools import read_local_log
    return read_local_log(limit)


@app.get("/api/dashboard/decisions")
async def dashboard_decisions(limit: int = 60):
    """Decision feed in the judge dashboard's contract (INTEGRATION_CONTRACTS.md)."""
    from datetime import datetime, timezone

    from tools.band_tools import read_local_log

    def _iso(ts: float) -> str:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _classify(agent: str, msg: str) -> tuple[str, str, str]:
        m = msg.lower()
        if "reprice" in m or "repriced" in m:
            return "repriced_product", "REPRICED PRODUCT", "learn"
        if "renamed" in m or "description" in m or "copy" in m:
            return "changed_copy", "UPDATED PRODUCT COPY", "list"
        if "listing" in m or "listed" in m or "marketplace" in m:
            return "listed_product", "UPDATED LISTINGS", "list"
        if "drop" in m and "product" in m:
            return "removed_product", "REMOVED PRODUCT", "learn"
        if "order" in m or "fulfill" in m or "shipping" in m:
            return "other", "FULFILLMENT", "fulfill"
        if "sale" in m or "revenue" in m or "payment" in m:
            return "other", "SALES", "sell"
        if "sourc" in m or "created product" in m or "cj " in m:
            return "other", "SOURCING", "source"
        if "terac" in m or "panel" in m or "study" in m:
            return "other", "CUSTOMER RESEARCH", "validate"
        return "other", "OPERATIONS", "learn"

    entries = read_local_log(limit * 2)
    decisions = []
    for e in entries:
        agent, msg = e.get("agent", ""), e.get("message", "")
        if agent == "Supervisor" and ("cycle" in msg.lower() and "tunnel" not in msg.lower()):
            continue  # heartbeat noise
        kind, title, stage = _classify(agent, msg)
        decisions.append({
            "id": f"feed_{e['ts']}",
            "timestamp": _iso(e["ts"]),
            "agent": f"{agent.replace('Agent', '').upper()} AGENT" if agent != "ESCALATION" else "ESCALATION",
            "kind": kind,
            "title": title,
            "reason": msg[:600],
            "action": msg[:200],
            "stage": stage,
        })
    decisions = decisions[-limit:][::-1]
    updated = decisions[0]["timestamp"] if decisions else _iso(0)
    return {"updatedAt": updated, "decisions": decisions}


@app.get("/api/dashboard/revenue")
async def dashboard_revenue():
    """Live-mode attested revenue in the dashboard's contract: captured minus refunds."""
    from datetime import datetime, timezone

    charges = stripe.Charge.list(limit=100)
    amount = 0
    orders = 0
    livemode = False
    for c in charges.data:
        if not c.paid:
            continue
        livemode = livemode or bool(c.livemode)
        amount += c.amount - (c.amount_refunded or 0)
        orders += 1
    return {
        "source": "stripe",
        "livemode": livemode,
        "amountMinor": amount,
        "currency": "USD",
        "orders": orders,
        "updatedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }


@app.get("/api/escalations")
async def get_escalations():
    """Open human-needed items. The business keeps running; humans drain this."""
    from tools.escalation_tools import open_escalations
    return open_escalations()


@app.post("/api/log")
async def post_log(entry: dict):
    """Remote log write — lets Person B's Linq handler (or any service on
    another machine) append to the same audit trail the dashboard shows."""
    from tools.band_tools import post_message
    agent = str(entry.get("agent", "Unknown"))[:40]
    message = str(entry.get("message", ""))[:2000]
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    await post_message(agent, message)
    return {"status": "logged"}


@app.get("/api/stats")
async def get_stats():
    """Revenue headline numbers for the dashboard. Zeros gracefully pre-keys."""
    from tools.stripe_tools import get_recent_charges, get_sales_summary
    try:
        summary = get_sales_summary(since_hours=24)
        charges = get_recent_charges(limit=100)
        return {
            "gross_revenue_cents": summary.get("gross_revenue_cents", 0),
            "orders": summary.get("orders", 0),
            "units": summary.get("units", 0),
            "by_product": summary.get("by_product", []),
            "charges": [{"created": c["created"], "amount_cents": c["amount_cents"]} for c in charges],
        }
    except Exception as exc:
        return {"gross_revenue_cents": 0, "orders": 0, "units": 0, "by_product": [], "charges": [], "error": str(exc)[:200]}


# ── Dashboard (the presentation layer — judges watch this) ─────

@app.get("/")
async def dashboard():
    from fastapi.responses import FileResponse
    from pathlib import Path
    return FileResponse(Path(__file__).parent / "static" / "dashboard.html")


# ── Health check ───────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
