#!/usr/bin/env python3
"""Prep Deals - single-file version. Scrapes listing pages, logs prices to
SQLite, flags real deals vs logged history, writes index.html. No local imports."""
import os, re, sys, json, time, html, sqlite3, datetime, statistics
from urllib.parse import urljoin, quote_plus
import requests, yaml
from bs4 import BeautifulSoup

DB_PATH = os.environ.get("PREP_DB", "prices.db")
MONEY = r'\$([0-9][0-9,]*(?:\.[0-9]{2})?)'
def _f(s):
    try: return float(str(s).replace(",", ""))
    except Exception: return None

# ---------- DB ----------
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS prices(
        id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT NOT NULL, site TEXT,
        brand TEXT, name TEXT, url TEXT, price REAL NOT NULL, was_price REAL,
        currency TEXT DEFAULT 'USD', ts TEXT NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pid ON prices(product_id)")
    return c
def record(pid, site, brand, name, url, price, was=None):
    c = _conn()
    c.execute("INSERT INTO prices(product_id,site,brand,name,url,price,was_price,ts) VALUES(?,?,?,?,?,?,?,?)",
              (pid, site, brand, name, url, price, was, datetime.datetime.utcnow().isoformat()))
    c.commit(); c.close()
def history(pid):
    c = _conn(); rows = c.execute("SELECT price FROM prices WHERE product_id=? ORDER BY ts", (pid,)).fetchall()
    c.close(); return [r[0] for r in rows]
def latest_by_product():
    c = _conn()
    rows = c.execute("""SELECT p.product_id,p.brand,p.name,p.url,p.price,p.site FROM prices p
        JOIN (SELECT product_id,MAX(ts) mx FROM prices GROUP BY product_id) m
        ON p.product_id=m.product_id AND p.ts=m.mx""").fetchall()
    c.close(); return rows

# ---------- adapters ----------
def ad_preppingdeals(h, base):
    soup = BeautifulSoup(h, "html.parser"); out = []
    for a in soup.select('a[href*="/deals/"]'):
        m = re.search(r'(.+?)\s*-\s*'+MONEY+r'\s*\(was\s*'+MONEY+r'\)', a.get_text(" ", strip=True))
        if m: out.append({"product_id": a.get("href"), "title": m.group(1).strip(),
                          "url": urljoin(base, a.get("href")), "price": _f(m.group(2)), "was_price": _f(m.group(3))})
    return out
def ad_woocommerce(h, base):
    soup = BeautifulSoup(h, "html.parser"); out = []
    for li in soup.select('li.product, ul.products li'):
        a = li.select_one('a[href*="/product"]') or li.find("a", href=True)
        if not a: continue
        t = li.select_one('.woocommerce-loop-product__title, h2, h3')
        ps = [ _f(re.sub(r'[^0-9.]','',e.get_text())) for e in li.select('.woocommerce-Price-amount') ]
        ps = [p for p in ps if p]
        if not ps: continue
        out.append({"product_id": a.get("href"), "title": (t.get_text(strip=True) if t else a.get_text(strip=True))[:120],
                    "url": urljoin(base, a.get("href")), "price": ps[-1], "was_price": ps[0] if len(ps) >= 2 else None})
    return out
def _price_from(el):
    for sel in ['[data-price-amount]','.price--withoutTax','[data-product-price-without-tax]',
                '.special-price .price','.price-item--sale','ins .amount','.sale-price',
                '[itemprop=price]','.price','[class*=price]']:
        e = el.select_one(sel)
        if e:
            raw = e.get('content') or e.get('data-price-amount') or e.get('data-price') or e.get_text(" ")
            m = re.search(MONEY, raw) or re.search(r'([0-9][0-9,]*\.[0-9]{2})', str(raw))
            v = _f(m.group(1)) if m else None
            if v: return v
    m = re.search(MONEY, el.get_text(" "))
    return _f(m.group(1)) if m else None

def ad_generic(h, base):
    soup = BeautifulSoup(h, "html.parser"); out = []; seen = set()
    # 1) JSON-LD Product
    for tag in soup.find_all("script", type="application/ld+json"):
        try: data = json.loads(tag.string or "")
        except Exception: continue
        stack = data if isinstance(data, list) else [data]
        for node in stack:
            if isinstance(node, dict) and node.get("@type") == "Product":
                off = node.get("offers") or {}
                if isinstance(off, list): off = off[0] if off else {}
                pr = _f(off.get("price"))
                if pr: out.append({"product_id": node.get("url") or node.get("name"), "title": node.get("name"),
                                   "url": node.get("url") or base, "price": pr, "was_price": None})
    if len(out) >= 3: return out
    out = []
    # 2) product-card heuristic (BigCommerce, Magento, Shopify, custom grids)
    for sel in ["li.product","article.card","li.card",".product-item",".product-card",
                ".productCard",".product-tile",".grid-product",".item.product-item","[data-product-id]"]:
        cards = soup.select(sel)
        if len(cards) < 3: continue
        for c in cards:
            a = c.find("a", href=True)
            if not a: continue
            href = a.get("href")
            if not href or href in seen or href.startswith("#"): continue
            price = _price_from(c)
            if not price: continue
            te = c.select_one(".card-title,.product-item-link,.product-title,.card-title a,.name,h2 a,h3 a,h2,h3")
            title = (te.get_text(strip=True) if te else (a.get("title") or a.get_text(strip=True)))[:120]
            if not title: continue
            seen.add(href)
            out.append({"product_id": href, "title": title, "url": urljoin(base, href),
                        "price": price, "was_price": None})
        if len(out) >= 3: return out
    return out

ADAPTERS = {"preppingdeals": ad_preppingdeals, "woocommerce": ad_woocommerce, "generic": ad_generic}

# ---------- scrape ----------
def scrape(cfg):
    s = cfg.get("settings", {}); headers = {"User-Agent": s.get("user_agent", "PrepDealsBot/1.0")}
    delay = s.get("request_delay_sec", 3); total = 0
    for site in cfg.get("sites", []):
        if not site.get("enabled", True): continue
        if site.get("js"): print(f"SKIP {site['id']}: needs headless browser"); continue
        adapter = ADAPTERS.get(site.get("adapter", "generic"))
        try:
            r = requests.get(site["url"], headers=headers, timeout=25); r.raise_for_status()
            items = adapter(r.text, site.get("base", site["url"])); n = 0
            for it in items:
                if not it.get("price"): continue
                record(f"{site['id']}:{it['product_id']}", site["id"], "", it.get("title",""),
                       it.get("url"), it["price"], it.get("was_price")); n += 1
            print(f"OK {site['id']}: {n} products"); total += n
        except Exception as e:
            print(f"ERR {site['id']}: {e}")
        time.sleep(delay)
    print(f"logged {total} prices")

# ---------- detect ----------
def evaluate(cfg):
    s = cfg.get("settings", {})
    min_drop = s.get("min_drop_pct",15)/100.0; atl_tol = s.get("atl_tolerance_pct",5)/100.0
    min_pts = s.get("min_points_for_verified",10)
    res = []
    for pid, brand, name, url, price, site in latest_by_product():
        h = history(pid); med = statistics.median(h) if h else None; atl = min(h) if h else None; n = len(h)
        gate = bool(med and atl and price <= med*(1-min_drop) and price <= atl*(1+atl_tol))
        status = "DEAL" if gate else "no"
        if gate and n < min_pts: status = "UNVERIFIED"
        res.append({"name": name, "url": url, "price": price, "median": round(med,2) if med else None,
                    "all_time_low": round(atl,2) if atl else None,
                    "pct_below_median": round((1-price/med)*100,1) if med else None,
                    "points": n, "status": status, "history": h})
    res.sort(key=lambda r: (r["status"]=="no", -(r["pct_below_median"] or -999)))
    return res

# ---------- dashboard ----------
def _spark(v, w=120, hh=28):
    if len(v) < 2: return ""
    lo, hi = min(v), max(v); rng = (hi-lo) or 1
    pts = " ".join(f"{i/(len(v)-1)*w:.1f},{hh-(x-lo)/rng*hh:.1f}" for i, x in enumerate(v))
    return f'<svg width="{w}" height="{hh}"><polyline fill="none" stroke="#2b8a3e" stroke-width="1.5" points="{pts}"/></svg>'
def _is_amazon(r):
    n=(r.get("name") or "").lower(); u=(r.get("url") or "").lower()
    return "[amazon]" in n or "amazon." in u or "/dp/" in u
def _clean(name):
    t=re.sub(r'^\s*[A-Z][a-z]{2}\s+\d{1,2}\s*','',name or ''); t=re.sub(r'\[[^\]]*\]\s*','',t)
    return re.sub(r'\s*-\s*\$?[0-9].*$','',t).strip()
def _hist_links(r):
    if not _is_amazon(r): return '<span style="color:#bbb">&mdash;</span>'
    q=quote_plus(_clean(r.get("name"))); m=re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', r.get("url") or "")
    k=f'https://keepa.com/#!product/1-{m.group(1)}' if m else f'https://keepa.com/#!search/1-{q}'
    return f'<a href="{k}" target="_blank">Keepa</a> &middot; <a href="https://camelcamelcamel.com/search?sq={q}" target="_blank">Camel</a>'
def dashboard(cfg, out="index.html"):
    rows = evaluate(cfg); deals = [r for r in rows if r["status"] in ("DEAL","UNVERIFIED")]
    def badge(s):
        c={"DEAL":"#2b8a3e","UNVERIFIED":"#b08900","no":"#888"}[s]
        return f'<span style="background:{c};color:#fff;padding:2px 7px;border-radius:4px;font-size:12px">{s}</span>'
    trs="".join(f"""<tr><td>{badge(r['status'])}</td>
      <td><a href="{html.escape(r['url'] or '#')}" target="_blank">{html.escape((r['name'] or '').strip())}</a></td>
      <td>${r['price']:.2f}</td><td>{('$%.2f'%r['median']) if r['median'] else '-'}</td>
      <td>{('$%.2f'%r['all_time_low']) if r['all_time_low'] else '-'}</td>
      <td>{(str(r['pct_below_median'])+'%') if r['pct_below_median'] is not None else '-'}</td>
      <td>{r['points']}</td><td>{_hist_links(r)}</td><td>{_spark(r['history'])}</td></tr>""" for r in rows)
    page=f"""<!doctype html><html><head><meta charset="utf-8"><title>Prep Deals</title>
    <style>body{{font-family:system-ui,Arial,sans-serif;margin:24px;color:#222}}h1{{margin:0 0 4px}}
    .sub{{color:#666;margin-bottom:18px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
    th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eee}}th{{background:#fafafa}}
    a{{color:#1565c0;text-decoration:none}}a:hover{{text-decoration:underline}}</style></head><body>
    <h1>Prep Deals</h1><div class="sub">{len(deals)} flagged &middot; {len(rows)} tracked. DEAL = verified vs logged history.
    UNVERIFIED = too little history yet. Amazon History links open the real price graph.</div>
    <table><tr><th>Status</th><th>Product</th><th>Now</th><th>Median</th><th>All-time low</th>
    <th>Below median</th><th>Data pts</th><th>Amazon History</th><th>Trend</th></tr>{trs}</table></body></html>"""
    open(out,"w").write(page); print(f"wrote {out} ({len(deals)} flagged of {len(rows)})")


# ---------- embedded config (used if config.yaml is missing) ----------
DEFAULT_CONFIG = {
  "settings": {"min_drop_pct":15,"atl_tolerance_pct":5,"min_points_for_verified":10,
               "request_delay_sec":3,"user_agent":"Mozilla/5.0 (compatible; PrepDealsBot/1.0)"},
  "sites": [
    {"id":"preppingdeals","url":"https://www.preppingdeals.net/","adapter":"preppingdeals"},
    {"id":"venturesurplus","url":"https://www.venturesurplus.com/shop/?on_sale=1","base":"https://www.venturesurplus.com/","adapter":"woocommerce"},
    {"id":"sportsmansguide","url":"https://www.sportsmansguide.com/productlist?sn=13","adapter":"generic"},
    {"id":"primaryarms","url":"https://www.primaryarms.com/","adapter":"generic"},
    {"id":"budsgunshop","url":"https://www.budsgunshop.com/","adapter":"generic"},
    {"id":"armysurplusworld","url":"https://www.armysurplusworld.com/dailydeals","adapter":"generic"},
    {"id":"tacticalsurplususa","url":"https://tacticalsurplususa.com/","adapter":"generic"},
    {"id":"propper","url":"https://www.propper.com/sale.html","adapter":"generic"},
    {"id":"opticsplanet","url":"https://www.opticsplanet.com/clearance-sale.html","adapter":"generic","js":True,"enabled":False},
    {"id":"backcountry","url":"https://www.backcountry.com/rc/flash-sale","adapter":"generic","js":True,"enabled":False},
    {"id":"als","url":"https://www.als.com/sale","adapter":"generic","js":True,"enabled":False},
    {"id":"armynavysales","url":"https://www.armynavysales.com/new-and-on-sale.html","adapter":"generic","js":True,"enabled":False},
    {"id":"tacticalgear","url":"https://tacticalgear.com/","adapter":"generic","js":True,"enabled":False},
    {"id":"battlehawkarmory","url":"https://battlehawkarmory.com/product-tag/daily-deals","adapter":"generic","js":True,"enabled":False},
  ],
}

def load_config(path="config.yaml"):
    try:
        with open(path) as f:
            c = yaml.safe_load(f)
        if c and c.get("sites"): return c
    except Exception: pass
    print("using embedded default config")
    return DEFAULT_CONFIG

if __name__ == "__main__":
    cfg = load_config(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
    scrape(cfg); dashboard(cfg)
