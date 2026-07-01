# Prep Deals — watchlist of deal/sale pages to scrub daily.
# tier is informational; `adapter` picks the parser; `js: true` needs Playwright.
settings:
  min_drop_pct: 15
  atl_tolerance_pct: 5
  cross_site_tolerance_pct: 3
  min_points_for_verified: 10
  request_delay_sec: 3
  user_agent: "Mozilla/5.0 (compatible; PrepDealsBot/1.0; personal price tracker)"

sites:
  # ---- STATIC: work with the basic scraper today ----
  - id: preppingdeals
    url: "https://www.preppingdeals.net/"
    adapter: preppingdeals
    tier: static
    enabled: true

  - id: venturesurplus
    url: "https://www.venturesurplus.com/shop/?on_sale=1"
    base: "https://www.venturesurplus.com/"
    adapter: woocommerce
    tier: static
    enabled: true

  - id: sportsmansguide
    url: "https://www.sportsmansguide.com/productlist?sn=13"
    adapter: generic          # tune selector after first raw-HTML run
    tier: static
    enabled: true

  - id: primaryarms
    url: "https://www.primaryarms.com/"
    adapter: generic
    tier: static
    enabled: true

  - id: budsgunshop
    url: "https://www.budsgunshop.com/"
    adapter: generic
    tier: static
    enabled: true

  # ---- SERVER-RENDERED: parse from raw HTML, may need a selector tweak ----
  - id: armysurplusworld
    url: "https://www.armysurplusworld.com/dailydeals"
    adapter: generic
    tier: server
    enabled: true

  - id: tacticalsurplususa
    url: "https://tacticalsurplususa.com/"
    adapter: generic
    tier: server
    enabled: true

  - id: propper
    url: "https://www.propper.com/sale.html"
    adapter: generic
    tier: server
    enabled: true

  # ---- JS / ANTI-BOT: need the Playwright fetcher (js: true) ----
  - id: opticsplanet
    url: "https://www.opticsplanet.com/clearance-sale.html"
    adapter: generic
    tier: js
    js: true
    enabled: false

  - id: backcountry
    url: "https://www.backcountry.com/rc/flash-sale"
    adapter: generic
    tier: js
    js: true
    enabled: false

  - id: als
    url: "https://www.als.com/sale"
    adapter: generic
    tier: js
    js: true
    enabled: false

  - id: armynavysales
    url: "https://www.armynavysales.com/new-and-on-sale.html"
    adapter: generic
    tier: js
    js: true
    enabled: false

  - id: tacticalgear
    url: "https://tacticalgear.com/"
    adapter: generic
    tier: js
    js: true
    enabled: false

  - id: battlehawkarmory
    url: "https://battlehawkarmory.com/product-tag/daily-deals"
    adapter: generic
    tier: js
    js: true
    enabled: false
