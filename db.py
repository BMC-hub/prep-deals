# Prep Deals — Build Plan

## Goal
Auto-scrub a fixed list of prepper/survival retailer pages daily, log prices,
and flag only *real* deals — verified against price history and cross-site
prices, ignoring fake "was $X" markups.

## Why this design
- Retailer "was/now" strikethroughs are the thing that gets faked. The only
  trustworthy signals are (a) your own logged price history and (b) the same
  product on other sites. This system uses both.
- Niche prepper sites mostly serve static HTML with little anti-bot, so simple
  HTTP scraping works. No third-party price history exists for them, so we build
  our own over time.

## Architecture
GitHub Actions (daily cron, free, always-on)
  -> scraper.py  reads config.yaml (your URLs + price selectors), fetches pages
  -> db.py       SQLite prices.db: one price row per product per run
  -> detect.py   flags a deal only if history gate AND cross-site gate pass
  -> dashboard.py writes index.html
  -> GitHub Pages hosts the dashboard, refreshes each run

## Deal-detection rules (the core value)
1. History gate: current price >= min_drop_pct below trailing median AND within
   atl_tolerance of the all-time low we've logged. Kills fake markups — inflate-
   then-discount keeps the median high, so the "sale" reads as noise.
2. Cross-site gate (product on 2+ listed sites): flagged only if cheapest live
   listing or within tolerance.
3. Cold-start: under ~10 data points a flag is UNVERIFIED (shown separately).

Cross-site matching: normalized brand + model/name, plus UPC/GTIN when present.

## What you provide
Product URLs (or category pages) + the price CSS selector per site. Template in
config.yaml. I can auto-detect selectors once you give the URLs.

## Cost
$0 — GitHub Actions + GitHub Pages free tiers. VPS only if you later want
sub-hourly checks.

## Honest risks
- A site adding Cloudflare needs a Playwright fallback (per-site, more fragile).
- Cross-site check only works for products carried by 2+ of your sites.
- First ~2 weeks build history; early flags are UNVERIFIED by design.
