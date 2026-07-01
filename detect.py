"""Generate a static index.html dashboard from detection results."""
import html, re
from urllib.parse import quote_plus
from detect import evaluate

def _spark(vals, w=120, h=28):
    if len(vals) < 2: return ""
    lo, hi = min(vals), max(vals); rng = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = i/(len(vals)-1)*w; y = h-(v-lo)/rng*h
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline fill="none" stroke="#2b8a3e" stroke-width="1.5" points="{" ".join(pts)}"/></svg>')

def _is_amazon(r):
    n = (r.get("name") or "").lower(); u = (r.get("url") or "").lower()
    return "[amazon]" in n or "amazon." in u or "/dp/" in u

def _clean_title(name):
    t = re.sub(r'^\s*[A-Z][a-z]{2}\s+\d{1,2}\s*', '', name or '')
    t = re.sub(r'\[[^\]]*\]\s*', '', t)
    t = re.sub(r'\s*-\s*\$?[0-9].*$', '', t)
    return t.strip()

def _history_links(r):
    if not _is_amazon(r):
        return '<span style="color:#bbb">&mdash;</span>'
    title = _clean_title(r.get("name")); u = (r.get("url") or "")
    m = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', u)
    q = quote_plus(title); links = []
    if m:
        links.append(f'<a href="https://keepa.com/#!product/1-{m.group(1)}" target="_blank">Keepa</a>')
    else:
        links.append(f'<a href="https://keepa.com/#!search/1-{q}" target="_blank">Keepa</a>')
    links.append(f'<a href="https://camelcamelcamel.com/search?sq={q}" target="_blank">Camel</a>')
    return ' &middot; '.join(links)

def build(config_path="config.yaml", out="index.html"):
    rows = evaluate(config_path)
    deals = [r for r in rows if r["status"] in ("DEAL", "UNVERIFIED")]
    def badge(s):
        c = {"DEAL": "#2b8a3e", "UNVERIFIED": "#b08900", "no": "#888"}[s]
        return f'<span style="background:{c};color:#fff;padding:2px 7px;border-radius:4px;font-size:12px">{s}</span>'
    trs = []
    for r in rows:
        trs.append(f"""<tr>
          <td>{badge(r['status'])}</td>
          <td><a href="{html.escape(r['url'] or '#')}" target="_blank">{html.escape((r['name'] or '').strip())}</a></td>
          <td>${r['price']:.2f}</td>
          <td>{('$%.2f'%r['median']) if r['median'] else '-'}</td>
          <td>{('$%.2f'%r['all_time_low']) if r['all_time_low'] else '-'}</td>
          <td>{(str(r['pct_below_median'])+'%') if r['pct_below_median'] is not None else '-'}</td>
          <td>{r['points']}</td>
          <td>{_history_links(r)}</td>
          <td>{_spark(r['history'])}</td>
        </tr>""")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Prep Deals</title>
    <style>
      body{{font-family:system-ui,Arial,sans-serif;margin:24px;color:#222}}
      h1{{margin:0 0 4px}} .sub{{color:#666;margin-bottom:18px}}
      table{{border-collapse:collapse;width:100%;font-size:14px}}
      th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #eee}}
      th{{background:#fafafa}} a{{color:#1565c0;text-decoration:none}} a:hover{{text-decoration:underline}}
    </style></head><body>
    <h1>Prep Deals</h1>
    <div class="sub">{len(deals)} flagged &middot; {len(rows)} tracked. DEAL = verified vs our logged history.
    UNVERIFIED = too little history yet. <b>Amazon History</b> links open the real Keepa / CamelCamelCamel graph &mdash; glance before buying.</div>
    <table>
      <tr><th>Status</th><th>Product</th><th>Now</th><th>Median</th><th>All-time low</th>
      <th>Below median</th><th>Data pts</th><th>Amazon History</th><th>Trend</th></tr>
      {''.join(trs)}
    </table></body></html>"""
    with open(out, "w") as f: f.write(page)
    print(f"wrote {out} ({len(deals)} flagged of {len(rows)})")

if __name__ == "__main__":
    build()
