"""Per-site extractors. Each adapter takes raw HTML (+ base url) and returns a
list of items: {product_id, title, url, price, was_price(optional)}.

product_id = the product URL path (stable), used as the history key.
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

MONEY = r'\$([0-9][0-9,]*(?:\.[0-9]{2})?)'

def _f(s):
    try: return float(str(s).replace(",", ""))
    except Exception: return None

# ---- 1. preppingdeals.net : "Title - $now (was $was)" links ----
def preppingdeals(html, base):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for a in soup.select('a[href*="/deals/"]'):
        txt = a.get_text(" ", strip=True)
        m = re.search(r'(.+?)\s*-\s*' + MONEY + r'\s*\(was\s*' + MONEY + r'\)', txt)
        if not m: continue
        items.append({
            "product_id": a.get("href"),
            "title": m.group(1).strip(),
            "url": urljoin(base, a.get("href")),
            "price": _f(m.group(2)),
            "was_price": _f(m.group(3)),
        })
    return items

# ---- 2. WooCommerce (venturesurplus) : product cards w/ current price ----
def woocommerce(html, base):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select('li.product, ul.products li'):
        a = li.select_one('a[href*="/product"]') or li.find("a", href=True)
        if not a: continue
        title_el = li.select_one('.woocommerce-loop-product__title, h2, h3')
        # current price = last <ins> amount, else the (only) amount
        ins = li.select_one('ins .woocommerce-Price-amount, ins')
        amt = li.select_one('.price .woocommerce-Price-amount')
        price = None; was = None
        prices = [ _f(re.sub(r'[^0-9.]', '', e.get_text())) for e in
                   li.select('.woocommerce-Price-amount') ]
        prices = [p for p in prices if p]
        if prices:
            price = prices[-1]
            if len(prices) >= 2: was = prices[0]
        if price is None: continue
        items.append({
            "product_id": a.get("href"),
            "title": (title_el.get_text(strip=True) if title_el else a.get_text(strip=True))[:120],
            "url": urljoin(base, a.get("href")),
            "price": price, "was_price": was,
        })
    return items

# ---- 3. Generic: JSON-LD offers + microdata + common price classes ----
import json
def generic(html, base):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    # JSON-LD Product/ItemList
    for tag in soup.find_all("script", type="application/ld+json"):
        try: data = json.loads(tag.string or "")
        except Exception: continue
        for node in (data if isinstance(data, list) else [data]):
            if not isinstance(node, dict): continue
            if node.get("@type") == "Product":
                off = node.get("offers") or {}
                if isinstance(off, list): off = off[0] if off else {}
                p = _f(off.get("price"))
                if p:
                    items.append({"product_id": node.get("url") or node.get("name"),
                                  "title": node.get("name"), "url": node.get("url") or base,
                                  "price": p, "was_price": None})
    if items: return items
    # microdata fallback
    for el in soup.select('[itemtype*="Product"]'):
        name = el.select_one('[itemprop=name]')
        price = el.select_one('[itemprop=price]')
        link = el.select_one('a[href]')
        p = _f(price.get("content") or (price.get_text() if price else "")) if price else None
        if p and link:
            items.append({"product_id": link.get("href"), "title": name.get_text(strip=True) if name else "",
                          "url": urljoin(base, link.get("href")), "price": p, "was_price": None})
    return items

REGISTRY = {
    "preppingdeals": preppingdeals,
    "woocommerce": woocommerce,
    "generic": generic,
}
