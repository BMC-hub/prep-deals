"""Optional: verify Amazon items against REAL price history via Keepa API.

Most preppingdeals.net items are Amazon links. Keepa tracks true Amazon price
history, so this is the strongest fake-markup check available. Requires a Keepa
API key (paid, ~EUR15/mo). Set env KEEPA_KEY to enable; otherwise it's skipped
and the system falls back to its own logged history.

Returns dict: {'amazon_low_90d': float, 'amazon_current': float} or None.
"""
import os, re, requests

def asin_from_url(url):
    m = re.search(r'/(?:dp|gp/product|d)/([A-Z0-9]{10})', url or "")
    return m.group(1) if m else None

def lookup(url):
    key = os.environ.get("KEEPA_KEY")
    asin = asin_from_url(url)
    if not key or not asin:
        return None
    try:
        r = requests.get("https://api.keepa.com/product",
                         params={"key": key, "domain": 1, "asin": asin, "stats": 90},
                         timeout=25)
        d = r.json().get("products", [{}])[0]
        stats = d.get("stats", {})
        # Keepa prices are in cents; index 0 = Amazon price
        cur = stats.get("current", [None])[0]
        low = (stats.get("min", [[None, None]])[0] or [None, None])[1]
        f = lambda c: round(c/100, 2) if isinstance(c, (int, float)) and c > 0 else None
        return {"amazon_current": f(cur), "amazon_low_90d": f(low)}
    except Exception:
        return None
