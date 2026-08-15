import httpx
import os

CJ_BASE = "https://developers.cjdropshipping.com/api2.0/v1"
_token = None


async def _get_token() -> str:
    global _token
    if _token:
        return _token
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{CJ_BASE}/authentication/getAccessToken", json={
            "email": os.getenv("CJ_EMAIL"),
            "apiKey": os.getenv("CJ_API_KEY"),
        })
        data = resp.json()
        if not data.get("data"):
            raise RuntimeError(f"CJ auth failed: {data}")
        _token = data["data"]["accessToken"]
        return _token


async def _headers() -> dict:
    token = await _get_token()
    return {"CJ-Access-Token": token}


async def search_products(query: str, page: int = 1, page_size: int = 20) -> list[dict]:
    """Search CJ for products. Returns simplified product list."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CJ_BASE}/product/list",
            headers=await _headers(),
            params={"productNameEn": query, "pageNum": page, "pageSize": page_size},
        )
        data = resp.json()
        if not data.get("data"):
            return []

        return [
            {
                "cj_product_id": p["pid"],
                "name": p.get("productNameEn", ""),
                "image": p.get("productImage", ""),
                "sell_price": p.get("sellPrice", 0),
                "category": p.get("categoryName", ""),
            }
            for p in data["data"].get("list", [])
        ]


async def get_product_details(product_id: str) -> dict:
    """Get full product details including all images and variants."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CJ_BASE}/product/query",
            headers=await _headers(),
            params={"pid": product_id},
        )
        data = resp.json()
        p = data.get("data", {})
        return {
            "cj_product_id": p.get("pid", ""),
            "name": p.get("productNameEn", ""),
            "description": p.get("description", ""),
            "images": [img.get("imageUrl", "") for img in p.get("productImageSet", [])],
            "sell_price": p.get("sellPrice", 0),
            "variants": [
                {
                    "vid": v.get("vid", ""),
                    "name": v.get("variantNameEn", ""),
                    "price": v.get("variantSellPrice", 0),
                }
                for v in p.get("variants", [])
            ],
        }


async def place_order(product_id: str, variant_id: str, shipping: dict) -> dict:
    """Place order with CJ. shipping = {name, phone, country, province, city, address, zip}"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{CJ_BASE}/shopping/order/createOrderV2",
            headers=await _headers(),
            json={
                "products": [{"pid": product_id, "vid": variant_id, "quantity": 1}],
                "shippingCountryCode": shipping.get("country", "US"),
                "shippingProvince": shipping["province"],
                "shippingCity": shipping["city"],
                "shippingAddress": shipping["address"],
                "shippingZip": shipping["zip"],
                "shippingCustomerName": shipping["name"],
                "shippingPhone": shipping.get("phone", ""),
            },
        )
        return resp.json()
