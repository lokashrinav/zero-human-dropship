import sys
from cable_search import cj, lead_price
TERMS = ["cable", "cord", "wire", "charger", "desk", "winder", "clip", "socket", "power strip", "usb"]
for cat in sys.argv[1:]:
    rows = (cj("GET", "/product/list", params={"categoryId": cat, "pageNum": 1, "pageSize": 100}) or {}).get("list") or []
    hits = [c for c in rows if any(t in (c.get("productNameEn","") or "").lower() for t in TERMS)]
    print(f"\n=== cat {cat}: {len(rows)} rows, {len(hits)} cable-ish ===")
    for c in hits:
        print(f"  {c['pid']} | ${lead_price(c.get('sellPrice')):>6.2f} | {c.get('productNameEn','')[:80]}")
