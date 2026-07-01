"""Deal detection: flag real deals, reject fake markups.

A product is a DEAL only if BOTH gates pass:
  history gate  -- current price is min_drop_pct below the trailing median
                   AND within atl_tolerance_pct of the all-time low.
  cross-site gate (only if product tracked on 2+ sites via brand+name) --
                   current price is the cheapest live listing (within tolerance).

Fewer than min_points_for_verified data points -> status UNVERIFIED.
"""
import statistics, yaml
import db

def _median(vals):
    return statistics.median(vals) if vals else None

def evaluate(config_path="config.yaml"):
    with open(config_path) as f:
        s = yaml.safe_load(f).get("settings", {})
    min_drop = s.get("min_drop_pct", 15) / 100.0
    atl_tol  = s.get("atl_tolerance_pct", 5) / 100.0
    xs_tol   = s.get("cross_site_tolerance_pct", 3) / 100.0
    min_pts  = s.get("min_points_for_verified", 10)

    latest = db.latest_by_product()  # (pid,brand,name,url,price,cur,ts)

    # group latest listings by (brand,name) for cross-site comparison
    groups = {}
    for row in latest:
        key = ((row[1] or "").strip().lower(), (row[2] or "").strip().lower())
        groups.setdefault(key, []).append(row)

    results = []
    for row in latest:
        pid, brand, name, url, price = row[0], row[1], row[2], row[3], row[4]
        hist = [p for p, _ in db.history(pid)]
        med = _median(hist)
        atl = min(hist) if hist else None
        n = len(hist)

        history_gate = False
        if med and atl:
            below_median = price <= med * (1 - min_drop)
            near_low = price <= atl * (1 + atl_tol)
            history_gate = below_median and near_low

        # cross-site gate
        key = ((brand or "").strip().lower(), (name or "").strip().lower())
        peers = [g for g in groups[key] if g[0] != pid]
        cross_site_gate = True
        cheapest_peer = None
        if peers:
            cheapest_peer = min(p[4] for p in peers)
            cross_site_gate = price <= cheapest_peer * (1 + xs_tol)

        is_deal = history_gate and cross_site_gate
        status = "DEAL" if is_deal else "no"
        if is_deal and n < min_pts:
            status = "UNVERIFIED"

        pct_below_med = round((1 - price / med) * 100, 1) if med else None
        results.append({
            "product_id": pid, "brand": brand, "name": name, "url": url,
            "price": price, "median": round(med, 2) if med else None,
            "all_time_low": round(atl, 2) if atl else None,
            "pct_below_median": pct_below_med, "points": n,
            "cheapest_peer": cheapest_peer, "status": status,
            "history": [p for p, _ in db.history(pid)],
        })
    # deals first, then by biggest discount
    results.sort(key=lambda r: (r["status"] == "no",
                                -(r["pct_below_median"] or -999)))
    return results

if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2))
