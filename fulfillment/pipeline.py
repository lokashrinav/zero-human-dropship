"""Stripe -> CJ Dropshipping fulfillment pipeline.

One file, four subcommands:
    python fulfillment/pipeline.py status
    python fulfillment/pipeline.py links on|off
    python fulfillment/pipeline.py match
    python fulfillment/pipeline.py daemon [--once] [--auto-pay]

Flow: buyer pays a Stripe payment link -> daemon sees the paid checkout
session -> looks up the CJ product in product_map.json -> creates a CJ order
shipped to the buyer's address. If anything is missing (CJ creds, mapping,
address) the order is written to manual_orders.log so it is never dropped.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import stripe
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
ENV = dotenv_values(ROOT.parent / "agent_backend" / ".env")
CJ_BASE = "https://developers.cjdropshipping.com/api2.0/v1"
MAP_FILE = ROOT / "product_map.json"
LEDGER_FILE = ROOT / "orders_ledger.json"
TOKEN_FILE = ROOT / "cj_token.json"
MANUAL_LOG = ROOT / "manual_orders.log"

stripe.api_key = ENV.get("STRIPE_SECRET_KEY", "")


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------- CJ API ----------

def cj_token():
    # A valid cached token works on its own; the API key is only needed to refresh.
    cached = load_json(TOKEN_FILE, {})
    if cached.get("token") and cached.get("expires", 0) > time.time() + 3600:
        return cached["token"]
    key = ENV.get("CJ_API_KEY")
    if not key:
        return None
    # CJ caches tokens server-side for 24h and rate-limits at 1 QPS -- cache locally.
    r = requests.post(f"{CJ_BASE}/authentication/getAccessToken",
                      json={"apiKey": key}, timeout=30)
    body = r.json()
    if not body.get("result"):
        raise RuntimeError(f"CJ auth failed: {body.get('message')}")
    token = body["data"]["accessToken"]
    save_json(TOKEN_FILE, {"token": token, "expires": time.time() + 14 * 86400})
    return token


def _throttle():
    # CJ rate limit: 1 QPS
    now = time.time()
    wait = _throttle.last + 1.1 - now
    if wait > 0:
        time.sleep(wait)
    _throttle.last = time.time()


_throttle.last = 0.0


def _cj_request(method, path, **kwargs):
    for attempt in range(4):
        _throttle()
        r = requests.request(method, f"{CJ_BASE}{path}",
                             headers={"CJ-Access-Token": cj_token()},
                             timeout=60, **kwargs)
        body = r.json()
        if body.get("result"):
            return body["data"]
        if "Too Many Requests" in str(body.get("message", "")):
            time.sleep(2.5 * (attempt + 1))
            continue
        raise RuntimeError(f"CJ {method} {path} failed: {body.get('message')}")
    raise RuntimeError(f"CJ {method} {path}: rate-limited after 4 attempts")


def cj_get(path, **params):
    return _cj_request("GET", path, params=params)


def cj_post(path, payload):
    return _cj_request("POST", path, json=payload)


# ---------- match: map Stripe products to real CJ products ----------

# CJ's keyword search is fuzzy garbage (returns rhinestone rings for "led
# strip light"), so we browse category listings instead and filter names
# locally. A result only counts if its name contains one of the accept
# phrases as a CONTIGUOUS phrase, so "Ring Light" can't match a jewelry ring.
CATALOG = {
    "LED Strip Lights RGB 16 Colors": {
        "cats": ["538CB48E-B7A0-46F7-B5A2-BB8183247B23",   # Night Lights
                 "EDB5F43E-EAC0-489A-8355-5188EAB72D08",   # String Lights
                 "DFFFDEDF-42F8-4D1F-B0A3-6B6744F7C1D3"],  # LED Spotlights
        "accept": ["led strip", "light strip", "strip light"]},
    "Magnetic Phone Mount for Car": {
        "cats": ["9170B3F9-5B9C-4C39-8CD6-7DC00E481D47"],  # Holders & Stands
        "accept": ["magnetic phone", "magnetic car", "car phone holder",
                   "car mount", "magsafe car"]},
    "Portable Mini Fan USB": {
        "cats": ["02EA33AA-4174-497D-86F4-D4FF9E525B81",   # Personal Care Appliances
                 "36686698-230D-46F9-A076-8CC61AE36CE3",   # Air Conditioning Appliances
                 "36F73513-6A5A-445D-87F9-BF3D6629E649"],  # Smart Home Appliances
        "accept": ["mini fan", "usb fan", "desk fan", "handheld fan",
                   "portable fan"]},
    "Wireless Earbuds with Charging Case": {
        "cats": ["DAECCC3B-13D8-4978-86A8-61D3DF186134"],  # Earphones & Headphones
        "accept": ["wireless earbuds", "bluetooth earbuds", "tws earbuds",
                   "wireless earphone", "bluetooth earphone", "tws earphone",
                   "wireless bluetooth headset"]},
    "Clip-On Selfie Light for Phone": {
        "cats": ["11D96803-A0A3-4175-B49B-2102EC285965",   # Photo Studio
                 "A2B55BEF-9B7D-44A0-8E80-A14FFFBBBD94",   # Camera & Photo Accessories
                 "9170B3F9-5B9C-4C39-8CD6-7DC00E481D47"],  # Holders & Stands
        "accept": ["ring light", "selfie light", "fill light"]},
    "Cable Organizer Clips 18-Pack": {
        "cats": ["87CF251F-8D11-4DE0-A154-9694D9858EB3",   # Home Office Storage
                 "40CC2ED1-8998-4515-9139-787CC25D42A7"],  # Digital Cables
        "accept": ["cable organizer", "cable clip", "cord organizer",
                   "cable management", "wire organizer", "cable holder"]},
    "Foldable Phone Stand Adjustable": {
        "cats": ["9170B3F9-5B9C-4C39-8CD6-7DC00E481D47"],  # Holders & Stands
        "accept": ["phone stand", "tablet stand", "desktop phone holder",
                   "foldable phone holder", "folding phone holder"]},
    "Screen Cleaner Spray Kit": {
        "cats": ["3633986F-83D2-4A6F-8F4D-79EE2CF77B8F",   # Cleaning Appliances
                 "51D68796-F1B5-4BDC-B9E0-32C3D9FF6994",   # Screen Protectors
                 "2502190343061609600"],                   # Computer Tablet Accessories
        "accept": ["screen cleaner", "screen cleaning", "cleaning kit",
                   "cleaner kit", "cleaning spray"]},
    "USB-C Fast Charging Cable 6ft": {
        "cats": ["00134C46-B7DF-4500-A3D9-ABB7B779EFD0",   # Phone Cables
                 "40CC2ED1-8998-4515-9139-787CC25D42A7"],  # Digital Cables
        "accept": ["type c cable", "usb c cable", "type c data cable",
                   "charging cable", "data cable"]},
    "Laptop Cooling Pad with Fan": {
        "cats": ["2502190343061609600",                    # Computer Tablet Accessories
                 "EDC3EDAF-1ED7-4776-8416-E9F8F0A5B4C6"],  # Tablet Accessories
        "accept": ["cooling pad", "laptop cooling", "laptop cooler",
                   "cooling stand", "laptop radiator"]},
}


def _norm(s):
    return " ".join("".join(c if c.isalnum() else " " for c in s.lower()).split())


def _name_matches(name, accept_phrases):
    padded = f" {_norm(name)} "
    return any(f" {_norm(p)} " in padded for p in accept_phrases)


def _lead_price(v):
    # sellPrice can be a range string like "2.97 -- 3.92"
    try:
        return float(str(v).split("--")[0].strip())
    except (ValueError, AttributeError):
        return 0.0


def cmd_match(_args):
    if not cj_token():
        sys.exit("CJ_API_KEY missing in agent_backend/.env -- "
                 "sign up at cjdropshipping.com first.")
    products = list(stripe.Product.list(active=True, limit=100).auto_paging_iter())
    mapping = load_json(MAP_FILE, {})
    for p in products:
        spec = CATALOG.get(p.name)
        if not spec:
            print(f"SKIP (not in CATALOG): {p.name}")
            continue
        passing = []
        for cat_id in spec["cats"]:
            found = (cj_get("/product/list", categoryId=cat_id,
                            pageNum=1, pageSize=100) or {}).get("list") or []
            passing += [c for c in found
                        if _name_matches(c.get("productNameEn", ""), spec["accept"])
                        and _lead_price(c.get("sellPrice")) > 0]
            if len(passing) >= 5:
                break
        if not passing:
            print(f"NO MATCH: {p.name}")
            continue
        cand = min(passing, key=lambda c: _lead_price(c.get("sellPrice")))
        variants = cj_get("/product/variant/query", pid=cand["pid"]) or []
        priced = [(float(v.get("variantSellPrice") or 0), v) for v in variants]
        priced = [pv for pv in priced if pv[0] > 0]
        if not priced:
            print(f"NO VARIANTS: {p.name}")
            continue
        cost, v = min(priced, key=lambda pv: pv[0])
        mapping[p.name] = {"pid": cand["pid"], "vid": v["vid"],
                           "cj_name": cand.get("productNameEn", ""),
                           "cj_cost": cost}
        print(f"{p.name}  ->  {mapping[p.name]['cj_name'][:60]}  (cost ${cost:.2f}, "
              f"{len(passing)} candidates)")
    save_json(MAP_FILE, mapping)
    print(f"\nWrote {MAP_FILE.name} with {len(mapping)} products mapped.")


# ---------- daemon: poll Stripe, place CJ orders ----------

def record_manual(session, summary, reason):
    det = getattr(session, "customer_details", None)
    line = (f"{datetime.now(timezone.utc).isoformat()} session={session.id} "
            f"amount=${(session.amount_total or 0) / 100:.2f} items=[{summary}] "
            f"email={getattr(det, 'email', '') or ''} REASON: {reason}\n")
    with open(MANUAL_LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print("MANUAL FULFILLMENT NEEDED:", line.strip())


def session_address(s):
    det = getattr(s, "shipping_details", None) or getattr(s, "customer_details", None)
    addr = getattr(det, "address", None) if det else None
    if not addr or not getattr(addr, "line1", None):
        return None
    cust = getattr(s, "customer_details", None)
    return {
        "name": getattr(det, "name", None) or "Customer",
        "phone": getattr(cust, "phone", None) or "0000000000",
        "line1": addr.line1,
        "line2": getattr(addr, "line2", None) or "",
        "city": addr.city or "",
        "state": getattr(addr, "state", None) or "",
        "zip": addr.postal_code or "",
        "country": addr.country or "US",
    }


def fulfill(session, ledger, auto_pay):
    items = stripe.checkout.Session.list_line_items(session.id, limit=10).data
    summary = ", ".join(f"{i.quantity}x {i.description}" for i in items)
    addr = session_address(session)
    if addr is None:
        record_manual(session, summary, "no shipping address collected")
        ledger[session.id] = {"status": "manual", "reason": "no address"}
        return
    mapping = load_json(MAP_FILE, {})
    cj_items = []
    for i in items:
        m = mapping.get(i.description)
        if not m:
            record_manual(session, summary, f"no CJ mapping for '{i.description}'")
            ledger[session.id] = {"status": "manual", "reason": "unmapped product"}
            return
        cj_items.append({"vid": m["vid"], "quantity": i.quantity})
    if not cj_token():
        record_manual(session, summary, "CJ credentials missing")
        ledger[session.id] = {"status": "manual", "reason": "no CJ creds"}
        return
    freight = cj_post("/logistic/freightCalculate", {
        "startCountryCode": "CN", "endCountryCode": addr["country"],
        "products": cj_items,
    })
    if not freight:
        raise RuntimeError("CJ returned no shipping options for this address")
    cheapest = min(freight, key=lambda f: float(f["logisticPrice"]))
    # CJ requires the country NAME in shippingCountry alongside the code.
    country_names = {"US": "United States", "CA": "Canada",
                     "GB": "United Kingdom", "AU": "Australia"}
    order = cj_post("/shopping/order/createOrderV2", {
        "orderNumber": f"stripe-{session.id[-24:]}",
        "shippingCountryCode": addr["country"],
        "shippingCountry": country_names.get(addr["country"], addr["country"]),
        "shippingProvince": addr["state"],
        "shippingCity": addr["city"],
        "shippingAddress": (addr["line1"] + (" " + addr["line2"] if addr["line2"] else "")),
        "shippingCustomerName": addr["name"],
        "shippingZip": addr["zip"],
        "shippingPhone": addr["phone"],
        "remark": "auto-fulfilled from Stripe",
        "logisticName": cheapest["logisticName"],
        "fromCountryCode": "CN",
        "products": cj_items,
    })
    order_id = order.get("orderId") if isinstance(order, dict) else order
    entry = {"status": "cj_created", "cj_order_id": order_id,
             "freight": cheapest["logisticName"],
             "freight_cost": cheapest["logisticPrice"], "items": summary,
             "ts": datetime.now(timezone.utc).isoformat()}
    if auto_pay:
        try:
            cj_post("/shopping/pay/payBalance", {"orderId": order_id})
            entry["status"] = "cj_paid"
        except Exception as e:  # usually: CJ wallet balance too low
            entry["pay_error"] = str(e)
    if entry["status"] != "cj_paid":
        # unpaid CJ orders do NOT ship -- make sure a human sees it
        record_manual(session, summary,
                      f"CJ order {order_id} created but UNPAID -- "
                      f"top up CJ wallet and pay it, or fulfill via Amazon")
    ledger[session.id] = entry
    print(f"[{datetime.now():%H:%M:%S}] CJ order {order_id} "
          f"({entry['status']}): {summary}")


def cmd_daemon(args):
    print("Fulfillment daemon: polling Stripe every 60s for paid checkouts. "
          "Ctrl+C to stop.")
    while True:
        ledger = load_json(LEDGER_FILE, {})
        try:
            for s in stripe.checkout.Session.list(limit=60).data:
                if s.payment_status != "paid":
                    continue
                entry = ledger.get(s.id)
                # --once (ops-cycle) retries parked orders that a refreshed
                # map/creds/code fix can unstick; "no address" needs a human.
                retryable = args.once and entry and (
                    entry.get("status") == "error"
                    or entry.get("reason") in ("unmapped product", "no CJ creds"))
                if entry and not retryable:
                    continue
                try:
                    fulfill(s, ledger, args.auto_pay)
                except Exception as e:
                    print(f"ERROR fulfilling {s.id}: {e}")
                    record_manual(s, "?", f"pipeline error: {e}")
                    ledger[s.id] = {"status": "error", "error": str(e)}
            save_json(LEDGER_FILE, ledger)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print("poll error:", e)
        if args.once:
            break
        time.sleep(60)


# ---------- links / status ----------

def cmd_links(args):
    turn_on = args.state == "on"
    links = list(stripe.PaymentLink.list(active=not turn_on,
                                         limit=100).auto_paging_iter())
    for l in links:
        stripe.PaymentLink.modify(l.id, active=turn_on)
        print(("activated   " if turn_on else "deactivated ") + l.url)
    print(f"{len(links)} links now {'ON' if turn_on else 'OFF'}")


def cmd_status(_args):
    n_active = len(stripe.PaymentLink.list(active=True, limit=100).data)
    mapping = load_json(MAP_FILE, {})
    ledger = load_json(LEDGER_FILE, {})
    has_cj = bool(ENV.get("CJ_API_KEY"))
    print(f"payment links active : {n_active}")
    print(f"CJ credentials       : {'set' if has_cj else 'MISSING (agent_backend/.env)'}")
    print(f"products mapped to CJ: {len(mapping)}")
    print(f"orders in ledger     : {len(ledger)}")
    for sid, e in ledger.items():
        print(f"  {sid[-8:]}: {e.get('status')} {e.get('items', '')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("links")
    p.add_argument("state", choices=["on", "off"])
    p.set_defaults(fn=cmd_links)
    sub.add_parser("match").set_defaults(fn=cmd_match)
    p = sub.add_parser("daemon")
    p.add_argument("--once", action="store_true", help="single poll then exit")
    p.add_argument("--auto-pay", action="store_true",
                   help="pay CJ orders from wallet balance automatically")
    p.set_defaults(fn=cmd_daemon)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
