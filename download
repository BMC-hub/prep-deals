"""Optional headless-browser fetcher for JS / anti-bot sites (js: true).

Install once:  pip install playwright && playwright install chromium
On GitHub Actions add a step:  - run: playwright install --with-deps chromium
"""
def get(url, wait_ms=3500):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(user_agent="Mozilla/5.0 (compatible; PrepDealsBot/1.0)")
        pg.goto(url, timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(wait_ms)
        html = pg.content()
        b.close()
        return html
