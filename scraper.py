# Site Feasibility Matrix

Tested each page by fetching it and inspecting how prices are delivered.
Three tiers: STATIC (parses with a simple HTTP request today), SERVER-RENDERED
(prices are in the raw HTML but the page needs per-site parsing rules), and
JS/ANTI-BOT (prices load via JavaScript or the site blocks bots — needs a
headless browser like Playwright).

| # | Site | Page | Platform | Tier | Notes |
|---|------|------|----------|------|-------|
| 1 | preppingdeals.net | / | Webflow | STATIC ✅ | Aggregator. Lists "Title - $now (was $was)", mostly Amazon. Easiest + richest. |
| 2 | sportsmansguide.com | productlist?sn=13 | custom | STATIC ✅ | ~140 prices in HTML, has "Regular" price for compare. |
| 3 | venturesurplus.com | shop?on_sale=1 | WooCommerce | STATIC ✅ | Cleanest data: "Original price was $X / Current price is $Y" + paging. Template site. |
| 4 | primaryarms.com | / | custom | STATIC ✅ | ~205 prices, "was $" present. |
| 5 | budsgunshop.com | / | custom | STATIC ✅ | ~96 prices in HTML. |
| 6 | armysurplusworld.com | dailydeals | BigCommerce | SERVER-RENDERED ⚠️ | Prices in raw HTML but stripped by our test converter; parses on a real run with a selector. |
| 7 | tacticalsurplususa.com | / | BigCommerce | SERVER-RENDERED ⚠️ | Same as above — BigCommerce, needs a selector. |
| 8 | propper.com | sale.html | Magento (Hyva) | SERVER-RENDERED ⚠️ | Product grid renders server-side; needs the sale-grid selector. |
| 9 | opticsplanet.com | deals.html | custom + Akamai | JS/ANTI-BOT ❌ | Anti-bot; and /deals is promos/rebates, not itemized prices. Use a clearance category instead. |
| 10 | backcountry.com | rc/flash-sale | Akamai | JS/ANTI-BOT ❌ | Returned empty to a bot. Needs headless browser. |
| 11 | als.com | /sale | — | JS/ANTI-BOT ❌ | Returned empty to a bot. |
| 12 | armynavysales.com | new-and-on-sale | — | JS/ANTI-BOT ❌ | Returned empty to a bot. |
| 13 | tacticalgear.com | / | JS SPA | JS/ANTI-BOT ❌ | Prices load via JavaScript; no prices in initial HTML. |
| 14 | battlehawkarmory.com | /product-tag/daily-deals | Coreware | JS/ANTI-BOT ❌ | Product tiles load via JS; homepage deal slots were empty in raw HTML. |

## What this means
- 5 sites (1-5) work with the basic scraper right now.
- 3 sites (6-8) work with one extra line of config (a CSS selector) once we see a
  real run's raw HTML.
- 6 sites (9-14) need a headless-browser add-on (Playwright). That runs fine on
  GitHub Actions too, just slower and more brittle. I'll add it as a second-stage
  fetcher for the sites flagged `js: true` in config.

## Note on the "was" prices
Sites 1-8 all show a strikethrough "was" price. We do NOT trust it — that's the
exact number that gets faked. The system logs the CURRENT price daily and builds
its own history; the "was" price is stored only for reference/display.
