"""Sourcing scratch tool: CJ keyword/category search + US freight verification.
Read-only against CJ. Does NOT touch fulfillment/ (reads cached token only).
"""
import json, sys, time
from pathlib import Path
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
ENV = dotenv_values(ROOT / ".env")
CJ_BASE = "https://developers.cjdropshipping.com/api2.0/v1"
TOKEN_FILE = ROOT.parent / "fulfillment" / "cj_token.json"

def cj_token():
    cached = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    if cached.get("token") and cached.get("expires", 0) > time.time() + 3600:
        return cached["token"]
    key = ENV.get("CJ_API_KEY")
    if not key:
        raise RuntimeError("no cached CJ token and CJ_API_KEY empty in .env")
    r = requests.post(f"{CJ_BASE}/authentication/getAccessToken", json={"apiKey": key}, timeout=30)
    b = r.json()
    if not b.get("result"):
        raise RuntimeError(f"CJ auth failed: {b.get('message')}")
    return b["data"]["accessToken"]

_last = [0.0]
def _throttle():
    w = _last[0] + 1.2 - time.time()
    if w > 0:
        time.sleep(w)
    _last[0] = time.time()

def cj(method, path, **kw):
    for attempt in range(4):
        _throttle()
        r = requests.request(method, f"{CJ_BASE}{path}",
                             headers={"CJ-Access-Token": cj_token()}, timeout=60, **kw)
        b = r.json()
        if b.get("result"):
            return b["data"]
        msg = str(b.get("message", ""))
        if "Too Many Requests" in msg:
            time.sleep(2.5 * (attempt + 1)); continue
        raise RuntimeError(f"CJ {method} {path} failed: {msg}")
    raise RuntimeError(f"CJ {method} {path}: rate-limited")

def lead_price(v):
    try:
        return float(str(v).split("--")[0].strip())
    except Exception:
        return 0.0

def search(kw, page_size=30):
    d = cj("GET", "/product/list", params={"productNameEn": kw, "pageNum": 1, "pageSize": page_size}) or {}
    return d.get("list") or []

def variants(pid):
    return cj("GET", "/product/variant/query", params={"pid": pid}) or []

def freight_us(vid, qty=1):
    """Returns list of US shipping options. EMPTY LIST = no US channel (permanent)."""
    return cj("POST", "/logistic/freightCalculate",
              json={"startCountryCode": "CN", "endCountryCode": "US",
                    "products": [{"vid": vid, "quantity": qty}]}) or []

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "search":
        for kw in sys.argv[2:]:
            rows = search(kw)
            print(f"\n=== {kw!r}: {len(rows)} results ===")
            for c in rows:
                p = lead_price(c.get("sellPrice"))
                print(f"  {c['pid']} | ${p:>6.2f} | {c.get('productNameEn','')[:78]}")
    elif mode == "freight":
        for pid in sys.argv[2:]:
            try:
                vs = variants(pid)
            except Exception as e:
                print(f"{pid}: VARIANT ERROR {e}"); continue
            priced = [(float(v.get("variantSellPrice") or 0), v) for v in vs]
            priced = [pv for pv in priced if pv[0] > 0]
            if not priced:
                print(f"{pid}: NO PRICED VARIANTS"); continue
            cost, v = min(priced, key=lambda pv: pv[0])
            try:
                opts = freight_us(v["vid"])
            except Exception as e:
                print(f"{pid}: FREIGHT ERROR {e}"); continue
            if not opts:
                print(f"{pid} vid={v['vid']} cost=${cost:.2f}: NO US CHANNEL (empty options)")
                continue
            cheap = min(opts, key=lambda f: float(f["logisticPrice"]))
            print(f"{pid} vid={v['vid']} cost=${cost:.2f} variants={len(priced)} "
                  f"-> SHIPS US: {cheap['logisticName']} ${float(cheap['logisticPrice']):.2f} "
                  f"({cheap.get('logisticAging','?')} days) | landed ${cost+float(cheap['logisticPrice']):.2f}")
    elif mode == "detail":
        pid = sys.argv[2]
        d = cj("GET", "/product/query", params={"pid": pid})
        print(json.dumps({k: d.get(k) for k in
              ("pid","productNameEn","productImage","sellPrice","categoryName",
               "productWeight","packingWeight","description")}, indent=2)[:3000])
        print("VARIANTS:")
        for v in variants(pid):
            print(" ", v.get("vid"), v.get("variantNameEn"), v.get("variantSellPrice"),
                  v.get("variantImage","")[:90])
