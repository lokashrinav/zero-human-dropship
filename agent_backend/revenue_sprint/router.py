"""FastAPI integration for revenue recommendations and tracked redirects."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from tools.stripe_tools import list_products

from .core import get_tracker


router = APIRouter()


def _public_base_url(request: Request) -> str:
    return os.getenv("PUBLIC_BASE_URL", "").rstrip("/") or str(request.base_url).rstrip("/")


@router.get("/api/revenue/recommend")
async def recommend_offer(
    request: Request,
    channel: str = Query(default="direct", min_length=1, max_length=50),
):
    """Return the highest-value current offer with ready-to-share tracked copy."""
    products = await asyncio.to_thread(list_products)
    try:
        return await asyncio.to_thread(
            get_tracker().recommend,
            products,
            channel,
            _public_base_url(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/api/revenue/stats")
async def revenue_stats(channel: str | None = Query(default=None, max_length=50)):
    """Report clicks, attributed sales, revenue, and estimated gross profit."""
    return await asyncio.to_thread(get_tracker().stats, channel)


@router.get("/r/{code}", include_in_schema=False)
async def tracked_checkout(code: str):
    """Count a campaign click and send the buyer directly to Stripe Checkout."""
    try:
        checkout_url = await asyncio.to_thread(get_tracker().visit, code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Offer link is inactive or unknown") from exc
    return RedirectResponse(checkout_url, status_code=307)
