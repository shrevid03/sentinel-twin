"""Channel3 product search: real products from many retailers for the shopping agent.

Live only when CHANNEL3_API_KEY is set. Results are mapped to the demo catalog's shape and cached
by SKU so checkout can resolve them. The key is never logged. Payment still runs in PayPal sandbox:
we do not buy from the retailer.
"""
import os
import re

import httpx

URL = "https://api.trychannel3.com/v1/search"
CACHE: dict[str, dict] = {}
status = {"enabled": False, "searches": 0, "errors": 0, "last_error": None}

GIFT_CARD = re.compile(r"gift\s*card|e-?gift|voucher", re.I)
CATEGORIES = [
    ("coffee", r"coffee|espresso|pour.?over|french press|cold brew|grinder|\bmug\b|latte|barista"),
    ("kitchen", r"kitchen|cook|\bpan\b|knife|spice|tea\b|teapot|kettle"),
    ("electronics", r"headphone|earbud|charger|keyboard|speaker|watch|usb|bluetooth|camera"),
    ("books", r"\bbook\b|hardcover|paperback|novel"),
    ("outdoor", r"backpack|tent|bottle|hiking|camp"),
    ("home", r"candle|decor|throw|blanket|lamp|vase"),
    ("apparel", r"shirt|shoe|sock|hoodie|jacket|dress|yoga"),
    ("plants", r"plant|seed|garden"),
    ("gaming", r"game|controller|console"),
]


# twin merchant node that stands in for an outside retailer when scoring risk (the twin only knows its own merchants)
TWIN_MERCHANT = {"coffee": "M-01", "electronics": "M-02", "books": "M-03", "outdoor": "M-04", "home": "M-05",
                 "apparel": "M-06", "gift_cards": "M-07", "plants": "M-08", "gaming": "M-09", "kitchen": "M-10"}


def enabled() -> bool:
    return bool(os.getenv("CHANNEL3_API_KEY"))


def _category(text: str) -> str:
    if GIFT_CARD.search(text):
        return "gift_cards"
    for cat, pat in CATEGORIES:
        if re.search(pat, text, re.I):
            return cat
    return "general"


def _offer(p):
    offers = [o for o in p.get("offers") or [] if (o.get("price") or {}).get("price") is not None]
    usd = [o for o in offers if (o["price"].get("currency") or "USD").upper() == "USD"]
    stock = [o for o in usd if (o.get("availability") or "InStock") == "InStock"] or usd
    return min(stock, key=lambda o: float(o["price"]["price"])) if stock else None


def to_item(p):
    o = _offer(p)
    if not o or not p.get("id"):
        return None
    imgs = p.get("images") or []
    img = next((i for i in imgs if i.get("is_main_image")), imgs[0] if imgs else {})
    title = (p.get("title") or "Product")[:120]
    desc = (p.get("description") or "")[:240]
    brands = p.get("brands") or []
    item = {"sku": f"C3-{p['id']}", "merchant": o.get("domain") or "retailer", "name": title,
            "price": round(float(o["price"]["price"]), 2), "category": _category(f"{title} {desc}"),
            "description": desc, "image": img.get("cleaned_url") or img.get("url"), "retailer_url": o.get("url"),
            "brand": brands[0].get("name") if brands else None, "source": "channel3"}
    item["twin_merchant"] = TWIN_MERCHANT.get(item["category"], "M-05")
    CACHE[item["sku"]] = item
    return item


def search(query, max_price=None, limit=8):
    """Live Channel3 search. Raises on any failure so the caller can fall back to the demo catalog."""
    key = os.getenv("CHANNEL3_API_KEY")
    if not key:
        raise RuntimeError("CHANNEL3_API_KEY not set")
    body = {"query": query or "gift", "limit": int(limit), "filters": {"availability": ["InStock"]}}
    if max_price is not None:
        body["filters"]["price"] = {"min_price": 0, "max_price": float(max_price)}
    last = None
    for _ in range(2):  # one retry
        try:
            r = httpx.post(URL, json=body, headers={"x-api-key": key}, timeout=6.0)
            r.raise_for_status()
            items = [i for i in (to_item(p) for p in r.json().get("products") or []) if i]
            if max_price is not None:
                items = [i for i in items if i["price"] <= float(max_price)]
            status["searches"] += 1
            return items[:limit]
        except Exception as e:  # noqa: BLE001
            last = e
    status["errors"] += 1
    status["last_error"] = type(last).__name__
    raise RuntimeError(f"Channel3 search failed ({type(last).__name__})")


def by_sku(sku):
    return CACHE.get(sku)
