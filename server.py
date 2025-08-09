import os
import sqlite3
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from playwright.sync_api import sync_playwright

app = Flask(__name__)
CORS(app)

DB_FILE = "llcs.db"

# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS llcs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            filing_date TEXT,
            link TEXT,
            UNIQUE(name, filing_date)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- SCRAPER ----------
def scrape_llcs(days=7, max_pages=5):
    """Scrape new LLCs from azcc.gov"""
    results = []
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://ecorp.azcc.gov/EntitySearch/Index")
        page.wait_for_load_state("domcontentloaded")

        # Example: click or set search filters
        # You may need to adjust selectors if site changes
        # This is placeholder — real azcc.gov scraping needs selector testing

        for page_num in range(1, max_pages + 1):
            # TODO: Replace with actual scraping logic for LLC name/date/link
            fake_data = [
                {
                    "name": f"Test LLC {page_num}-{i}",
                    "filing_date": str(today - datetime.timedelta(days=i)),
                    "link": "https://ecorp.azcc.gov/EntitySearch/BusinessInfo?entityId=123"
                }
                for i in range(3)
            ]
            for row in fake_data:
                filing_dt = datetime.date.fromisoformat(row["filing_date"])
                if filing_dt >= cutoff:
                    results.append(row)

        browser.close()

    return results

# ---------- DATABASE SAVE ----------
def save_llcs_to_db(llcs):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for llc in llcs:
        try:
            c.execute(
                "INSERT OR IGNORE INTO llcs (name, filing_date, link) VALUES (?, ?, ?)",
                (llc["name"], llc["filing_date"], llc["link"])
            )
        except Exception as e:
            print(f"DB insert error: {e}")
    conn.commit()
    conn.close()

# ---------- API ROUTES ----------
@app.route("/api/llcs/recent", methods=["GET"])
def get_recent_llcs():
    days = int(request.args.get("days", 7))
    page_num = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    cutoff_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    c.execute("SELECT name, filing_date, link FROM llcs WHERE filing_date >= ? ORDER BY filing_date DESC", (cutoff_date,))
    rows = c.fetchall()
    conn.close()

    # Pagination
    start = (page_num - 1) * per_page
    end = start + per_page
    paginated = rows[start:end]

    data = [{"name": r[0], "filing_date": r[1], "link": r[2]} for r in paginated]
    return jsonify(data)

@app.route("/api/llcs/scrape", methods=["POST"])
def scrape_and_save():
    llcs = scrape_llcs()
    save_llcs_to_db(llcs)
    return jsonify({"status": "success", "scraped": len(llcs)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
