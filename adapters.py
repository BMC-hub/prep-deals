"""Fetch each listing page, run its adapter, record all products to SQLite.

Basic mode uses plain HTTP (requests). Sites flagged `js: true` are skipped here
and require the Playwright fetcher (fetch_js.py) — run that separately/first.
"""
import sys, time, yaml, requests
import db, adapters

def load(path):
    with open(path) as f: return yaml.safe_load(f)

def fetch_html(url, headers, js=False):
    if js:
        try:
            import fetch_js
            return fetch_js.get(url)      # optional headless-browser fetcher
        except Exception as e:
            print(f"   (js fetch unavailable: {e})"); return None
    r = requests.get(url, headers=headers, timeout=25); r.raise_for_status()
    return r.text

def run(config_path="config.yaml"):
    cfg = load(config_path); s = cfg.get("settings", {})
    headers = {"User-Agent": s.get("user_agent", "PrepDealsBot/1.0")}
    delay = s.get("request_delay_sec", 2)
    total = 0
    for site in cfg.get("sites", []):
        if not site.get("enabled", True): continue
        name = site["id"]; adapter = adapters.REGISTRY.get(site.get("adapter", "generic"))
        try:
            html = fetch_html(site["url"], headers, site.get("js", False))
            if not html:
                print(f"SKIP {name}: no html (js site needs Playwright)"); continue
            items = adapter(html, site.get("base", site["url"]))
            n = 0
            for it in items:
                if not it.get("price"): continue
                pid = f"{name}:{it['product_id']}"
                db.record(pid, name, it.get("brand", ""), it.get("title", ""),
                          it.get("url"), it["price"], it.get("was_price"))
                n += 1
            print(f"OK {name}: {n} products"); total += n
        except Exception as e:
            print(f"ERR {name}: {e}")
        time.sleep(delay)
    print(f"done: {total} product prices logged")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "config.yaml")
