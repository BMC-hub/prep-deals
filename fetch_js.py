"""SQLite price-history store (listing-page model)."""
import sqlite3, datetime, os
DB_PATH = os.environ.get("PREP_DB", os.path.join(os.path.dirname(__file__), "prices.db"))

def conn():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS prices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL, site TEXT, brand TEXT, name TEXT, url TEXT,
        price REAL NOT NULL, was_price REAL, currency TEXT DEFAULT 'USD',
        ts TEXT NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_pid ON prices(product_id)")
    return c

def record(product_id, site, brand, name, url, price, was_price=None, currency="USD"):
    c = conn()
    c.execute("""INSERT INTO prices(product_id,site,brand,name,url,price,was_price,currency,ts)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (product_id, site, brand, name, url, price, was_price, currency,
               datetime.datetime.utcnow().isoformat()))
    c.commit(); c.close()

def history(product_id):
    c = conn()
    rows = c.execute("SELECT price, ts FROM prices WHERE product_id=? ORDER BY ts",
                     (product_id,)).fetchall()
    c.close(); return [(r[0], r[1]) for r in rows]

def latest_by_product():
    c = conn()
    rows = c.execute("""SELECT p.product_id,p.brand,p.name,p.url,p.price,p.currency,p.ts,p.site,p.was_price
        FROM prices p JOIN (SELECT product_id, MAX(ts) mx FROM prices GROUP BY product_id) m
        ON p.product_id=m.product_id AND p.ts=m.mx""").fetchall()
    c.close(); return rows
