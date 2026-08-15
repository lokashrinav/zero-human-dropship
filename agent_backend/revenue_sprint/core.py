"""Small, dependency-free revenue loop for Stripe Payment Links.

The tracker ranks products by expected gross profit, creates short campaign links,
records clicks, and attributes Checkout completions through Stripe's
``client_reference_id`` field. It deliberately stores no customer PII.
"""

from __future__ import annotations

import math
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from threading import Lock
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REFERENCE_PREFIX = "rev_"
DEFAULT_CHANNEL = "direct"
_SAFE_PARAMETER = re.compile(r"[^A-Za-z0-9_-]+")


def _safe_parameter(value: str, fallback: str = "unknown", limit: int = 100) -> str:
    cleaned = _SAFE_PARAMETER.sub("_", value.strip())[:limit].strip("_")
    return cleaned or fallback


def _now() -> int:
    return int(time.time())


class RevenueTracker:
    """SQLite-backed campaign attribution and profit-aware offer selection."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        prior_conversion_rate: float = 0.03,
        prior_clicks: int = 20,
        exploration_weight: float = 0.35,
    ) -> None:
        if not 0 < prior_conversion_rate < 1:
            raise ValueError("prior_conversion_rate must be between 0 and 1")
        if prior_clicks < 1:
            raise ValueError("prior_clicks must be positive")
        if exploration_weight < 0:
            raise ValueError("exploration_weight cannot be negative")

        self.db_path = str(db_path)
        self.prior_conversion_rate = prior_conversion_rate
        self.prior_clicks = prior_clicks
        self.exploration_weight = exploration_weight
        self._write_lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        path = Path(self.db_path)
        if self.db_path != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS campaigns (
                    code TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    payment_url TEXT NOT NULL,
                    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
                    cost_cents INTEGER NOT NULL CHECK (cost_cents >= 0),
                    created_at INTEGER NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS campaigns_product_channel
                    ON campaigns(product_id, channel, active);

                CREATE TABLE IF NOT EXISTS clicks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL REFERENCES campaigns(code),
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS clicks_code ON clicks(code);

                CREATE TABLE IF NOT EXISTS conversions (
                    stripe_session_id TEXT PRIMARY KEY,
                    code TEXT NOT NULL REFERENCES campaigns(code),
                    revenue_cents INTEGER NOT NULL CHECK (revenue_cents >= 0),
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS conversions_code ON conversions(code);
                """
            )

    @staticmethod
    def _validate_product(product: dict[str, Any]) -> dict[str, Any]:
        product_id = str(product.get("product_id", "")).strip()
        name = str(product.get("name", "")).strip()
        payment_url = str(product.get("payment_link_url", "")).strip()
        try:
            price_cents = int(product.get("price_cents", 0))
            cost_cents = int(product.get("cost_cents", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError("product price and cost must be integer cents") from exc

        parsed = urlsplit(payment_url)
        if not product_id or not name:
            raise ValueError("product_id and name are required")
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("payment_link_url must be an HTTPS URL")
        if price_cents <= 0 or cost_cents < 0 or cost_cents >= price_cents:
            raise ValueError("product must have a positive price above its cost")
        return {
            **product,
            "product_id": product_id,
            "name": name,
            "payment_link_url": payment_url,
            "price_cents": price_cents,
            "cost_cents": cost_cents,
        }

    def _performance_by_product(self, channel: str) -> dict[str, dict[str, int]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    c.product_id,
                    COUNT(DISTINCT cl.id) AS clicks,
                    COUNT(DISTINCT cv.stripe_session_id) AS conversions,
                    COALESCE(SUM(DISTINCT cv.revenue_cents), 0) AS revenue_cents
                FROM campaigns c
                LEFT JOIN clicks cl ON cl.code = c.code
                LEFT JOIN conversions cv ON cv.code = c.code
                WHERE c.channel = ?
                GROUP BY c.product_id
                """,
                (channel,),
            ).fetchall()
        return {
            row["product_id"]: {
                "clicks": int(row["clicks"]),
                "conversions": int(row["conversions"]),
                "revenue_cents": int(row["revenue_cents"]),
            }
            for row in rows
        }

    def rank_products(
        self, products: Iterable[dict[str, Any]], channel: str, limit: int = 3
    ) -> list[dict[str, Any]]:
        """Rank offers by estimated profit per click with bounded exploration."""
        safe_channel = _safe_parameter(channel, DEFAULT_CHANNEL, 50)
        performance = self._performance_by_product(safe_channel)
        ranked = []
        for raw_product in products:
            try:
                product = self._validate_product(raw_product)
            except ValueError:
                continue
            metrics = performance.get(
                product["product_id"],
                {"clicks": 0, "conversions": 0, "revenue_cents": 0},
            )
            clicks = metrics["clicks"]
            conversions = metrics["conversions"]
            posterior_rate = (
                conversions + self.prior_conversion_rate * self.prior_clicks
            ) / (clicks + self.prior_clicks)
            # The uncertainty bonus shrinks quickly. It explores products without
            # allowing an untested low-margin product to dominate indefinitely.
            uncertainty = math.sqrt(posterior_rate * (1 - posterior_rate) / (clicks + 1))
            expected_rate = min(
                1.0, posterior_rate + self.exploration_weight * uncertainty
            )
            margin_cents = product["price_cents"] - product["cost_cents"]
            ranked.append(
                {
                    **product,
                    "channel": safe_channel,
                    "clicks": clicks,
                    "conversions": conversions,
                    "observed_revenue_cents": metrics["revenue_cents"],
                    "estimated_conversion_rate": round(expected_rate, 6),
                    "estimated_profit_per_click_cents": round(
                        margin_cents * expected_rate, 2
                    ),
                }
            )

        ranked.sort(
            key=lambda product: (
                product["estimated_profit_per_click_cents"],
                product["price_cents"] - product["cost_cents"],
                product["product_id"],
            ),
            reverse=True,
        )
        return ranked[: max(1, min(limit, 20))]

    def get_or_create_campaign(
        self, product: dict[str, Any], channel: str, public_base_url: str
    ) -> dict[str, Any]:
        product = self._validate_product(product)
        safe_channel = _safe_parameter(channel, DEFAULT_CHANNEL, 50)
        base_url = public_base_url.rstrip("/")
        parsed_base = urlsplit(base_url)
        if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
            raise ValueError("public_base_url must be an HTTP(S) URL")

        with self._write_lock, self._connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM campaigns
                WHERE product_id = ? AND channel = ? AND payment_url = ? AND active = 1
                ORDER BY created_at DESC LIMIT 1
                """,
                (product["product_id"], safe_channel, product["payment_link_url"]),
            ).fetchone()
            if existing:
                campaign = dict(existing)
            else:
                code = secrets.token_hex(6)
                created_at = _now()
                connection.execute(
                    """
                    INSERT INTO campaigns (
                        code, product_id, product_name, channel, payment_url,
                        price_cents, cost_cents, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        code,
                        product["product_id"],
                        product["name"],
                        safe_channel,
                        product["payment_link_url"],
                        product["price_cents"],
                        product["cost_cents"],
                        created_at,
                    ),
                )
                campaign = {
                    "code": code,
                    "product_id": product["product_id"],
                    "product_name": product["name"],
                    "channel": safe_channel,
                    "payment_url": product["payment_link_url"],
                    "price_cents": product["price_cents"],
                    "cost_cents": product["cost_cents"],
                    "created_at": created_at,
                    "active": 1,
                }

        return {
            **campaign,
            "tracked_url": f"{base_url}/r/{campaign['code']}",
            "client_reference_id": f"{REFERENCE_PREFIX}{campaign['code']}",
        }

    def recommend(
        self,
        products: Iterable[dict[str, Any]],
        channel: str,
        public_base_url: str,
    ) -> dict[str, Any]:
        ranked = self.rank_products(products, channel, limit=1)
        if not ranked:
            raise ValueError("no profitable products with valid payment links are available")
        product = ranked[0]
        campaign = self.get_or_create_campaign(product, channel, public_base_url)
        tracked_url = campaign["tracked_url"]
        return {
            "product": product,
            "campaign": campaign,
            "share_copy": self.share_copy(product, tracked_url, channel),
        }

    @staticmethod
    def share_copy(product: dict[str, Any], tracked_url: str, channel: str) -> str:
        name = product["name"]
        price = product["price_cents"] / 100
        channel = _safe_parameter(channel, DEFAULT_CHANNEL, 50)
        if channel == "linq":
            return f"Quick find: {name} for ${price:.2f}. You can grab it here: {tracked_url}"
        if channel == "facebook_marketplace":
            return f"{name} — ${price:.2f}. Secure online checkout: {tracked_url}"
        if channel == "social":
            return f"Found this: {name} for ${price:.2f} → {tracked_url}"
        return f"{name} — ${price:.2f}: {tracked_url}"

    def visit(self, code: str) -> str:
        """Record a click and return the attributed Stripe Payment Link URL."""
        with self._write_lock, self._connect() as connection:
            campaign = connection.execute(
                "SELECT * FROM campaigns WHERE code = ? AND active = 1", (code,)
            ).fetchone()
            if campaign is None:
                raise KeyError(code)
            connection.execute(
                "INSERT INTO clicks (code, created_at) VALUES (?, ?)", (code, _now())
            )

        parsed = urlsplit(campaign["payment_url"])
        parameters = dict(parse_qsl(parsed.query, keep_blank_values=True))
        parameters.update(
            {
                "client_reference_id": f"{REFERENCE_PREFIX}{code}",
                "utm_source": _safe_parameter(campaign["channel"], DEFAULT_CHANNEL, 150),
                "utm_medium": "referral",
                "utm_campaign": "revenue_sprint",
                "utm_content": _safe_parameter(campaign["product_id"], "product", 150),
            }
        )
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(parameters), parsed.fragment)
        )

    def record_checkout_conversion(self, session: dict[str, Any]) -> bool:
        """Idempotently attribute a paid Checkout Session. Returns True if attributed."""
        reference = str(session.get("client_reference_id") or "")
        if not reference.startswith(REFERENCE_PREFIX):
            return False
        code = reference[len(REFERENCE_PREFIX) :]
        session_id = str(session.get("id") or "").strip()
        payment_status = str(session.get("payment_status") or "")
        try:
            revenue_cents = int(session.get("amount_total") or 0)
        except (TypeError, ValueError):
            return False
        if not session_id or payment_status != "paid" or revenue_cents < 0:
            return False

        with self._write_lock, self._connect() as connection:
            campaign = connection.execute(
                "SELECT code FROM campaigns WHERE code = ?", (code,)
            ).fetchone()
            if campaign is None:
                return False
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO conversions (
                    stripe_session_id, code, revenue_cents, created_at
                ) VALUES (?, ?, ?, ?)
                """,
                (session_id, code, revenue_cents, _now()),
            )
            return cursor.rowcount == 1

    def stats(self, channel: str | None = None) -> dict[str, Any]:
        parameters: tuple[Any, ...] = ()
        where = ""
        if channel:
            where = "WHERE c.channel = ?"
            parameters = (_safe_parameter(channel, DEFAULT_CHANNEL, 50),)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    c.code, c.product_id, c.product_name, c.channel,
                    c.price_cents, c.cost_cents, c.created_at, c.active,
                    (SELECT COUNT(*) FROM clicks cl WHERE cl.code = c.code) AS clicks,
                    (SELECT COUNT(*) FROM conversions cv WHERE cv.code = c.code) AS conversions,
                    (SELECT COALESCE(SUM(cv.revenue_cents), 0)
                        FROM conversions cv WHERE cv.code = c.code) AS revenue_cents
                FROM campaigns c
                {where}
                ORDER BY c.created_at DESC
                """,
                parameters,
            ).fetchall()

        campaigns = []
        for row in rows:
            item = dict(row)
            item["conversion_rate"] = round(
                item["conversions"] / item["clicks"], 4
            ) if item["clicks"] else 0.0
            item["estimated_gross_profit_cents"] = (
                item["revenue_cents"] - item["conversions"] * item["cost_cents"]
            )
            campaigns.append(item)

        return {
            "campaigns": campaigns,
            "totals": {
                "clicks": sum(item["clicks"] for item in campaigns),
                "conversions": sum(item["conversions"] for item in campaigns),
                "revenue_cents": sum(item["revenue_cents"] for item in campaigns),
                "estimated_gross_profit_cents": sum(
                    item["estimated_gross_profit_cents"] for item in campaigns
                ),
            },
        }


_tracker: RevenueTracker | None = None


def get_tracker() -> RevenueTracker:
    global _tracker
    if _tracker is None:
        default_path = Path(__file__).resolve().parent.parent / "revenue_sprint.sqlite3"
        _tracker = RevenueTracker(
            os.getenv("REVENUE_DB_PATH", str(default_path)),
            prior_conversion_rate=float(os.getenv("REVENUE_PRIOR_CONVERSION_RATE", "0.03")),
            prior_clicks=int(os.getenv("REVENUE_PRIOR_CLICKS", "20")),
            exploration_weight=float(os.getenv("REVENUE_EXPLORATION_WEIGHT", "0.35")),
        )
    return _tracker
