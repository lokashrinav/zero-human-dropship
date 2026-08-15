import json
import os
import stripe
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

app = FastAPI(title="Zero Human Dropship — Agent Backend")


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


# ── Health check ───────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-backend"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
