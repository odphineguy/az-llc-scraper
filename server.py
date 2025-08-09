from flask import Flask, jsonify
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)

DB_FILE = "llcs.db"

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS llcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            filing_date TEXT,
            entity_url TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Scraper function ---
def scrape_recent_llcs(days_back=7):
    cutoff_date = datetime.today() - timedelta(days=days_back)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # Example search URL – you may need to tweak this for AZCC site
        page.goto("https://ecorp.azcc.gov/EntitySearch/Index")
        page.wait_for_timeout(5000)  # Wait for page to load

        # NOTE: You'll need to adjust selectors for AZCC site
        # For now, this is just a placeholder loop
        rows = page.query_selector_all("table tbody tr")
        for row in rows:
            cols = row.query_selector_all("td")
            if len(cols) >= 2:
                name = cols[0].inner_text().strip()
                filing_date_str = cols[1].inner_text().strip()
                try:
                    filing_date = datetime.strptime(filing_date_str, "%m/%d/%Y")
                except:
                    continue

                if filing_date >= cutoff_date:
                    link_el = cols[0].query_selector("a")
                    url = link_el.get_attribute("href") if link_el else None
                    results.append({
                        "name": name,
                        "filing_date": filing_date_str,
                        "entity_url": url
                    })

        browser.close()

    # Save to DB
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for r in results:
        c.execute("INSERT INTO llcs (name, filing_date, entity_url) VALUES (?, ?, ?)",
                  (r["name"], r["filing_date"], r["entity_url"]))
    conn.commit()
    conn.close()

    return results

# --- API endpoint ---
@app.route("/api/llcs/recent")
def get_recent_llcs():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name, filing_date, entity_url FROM llcs ORDER BY filing_date DESC")
    rows = c.fetchall()
    conn.close()

    llcs = [{"name": r[0], "filing_date": r[1], "entity_url": r[2]} for r in rows]
    return jsonify(llcs)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
