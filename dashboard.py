# Prep Deals

Daily price tracker for prepper/tactical/survival gear. Scrapes a list of
sale/deal pages, logs every product's current price, and flags only *real* deals
— verified against the price history it builds and (where possible) cross-site,
so fake "was $X" markups don't fool it.

## Files
- `config.yaml` — your 14 sites, each with an adapter + tier. Toggle `enabled`.
- `adapters.py` — per-site extractors (preppingdeals, woocommerce, generic).
- `scraper.py` — fetches each page, runs its adapter, logs prices to `prices.db`.
- `db.py` — SQLite price history (also stores the site's untrusted "was" price).
- `detect.py` — deal logic: own-history gate + cross-site gate.
- `dashboard.py` — writes `index.html`.
- `keepa.py` — optional Amazon real-history check (needs KEEPA_KEY).
- `fetch_js.py` — optional Playwright fetcher for JS/anti-bot sites.
- `.github/workflows/daily.yml` — runs daily, free, on GitHub Actions.
- `SITES.md` — per-site feasibility (which sites work now vs need Playwright).

## Which sites work now
Enabled today (static/server-rendered): preppingdeals, venturesurplus,
sportsmansguide, primaryarms, budsgunshop, armysurplusworld, tacticalsurplususa,
propper. The other six (opticsplanet, backcountry, als, armynavysales,
tacticalgear, battlehawkarmory) are `enabled: false` + `js: true` — turn them on
after installing Playwright (see fetch_js.py). Details in SITES.md.

## Run locally
    pip install -r requirements.txt
    python scraper.py config.yaml     # fetch + log prices
    python dashboard.py               # build index.html
    open index.html

## Deploy (free, always-on)
1. Push this folder to a new GitHub repo.
2. Settings > Pages > Source: GitHub Actions.
3. Runs daily; dashboard updates automatically. Run manually from the Actions tab.

## How a deal is decided
Flagged only if current price is >= `min_drop_pct` below the trailing median AND
within `atl_tolerance_pct` of the lowest price we've logged (and, if the same
item is tracked on 2+ sites, it's the cheapest). Under `min_points_for_verified`
data points it shows as UNVERIFIED. The site's own "was" price is stored for
reference only and never used to decide a deal.

## Adding the Amazon check (recommended for preppingdeals)
Most preppingdeals items are Amazon. Set `KEEPA_KEY` (Keepa API, paid) to verify
each against real Amazon 90-day/all-time lows — the strongest fake-markup check.
