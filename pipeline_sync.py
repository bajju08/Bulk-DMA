import os
import json
import time
import pandas as pd
import gspread

from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1vnrsybq4tX4BFvDupY5y8oxFLh0LyuPF_dm-viSqxWM"


# =========================
# GOOGLE AUTH
# =========================

def auth_google():

    creds_json = os.environ.get("GOOGLE_CREDS_SECRET")

    creds_dict = json.loads(creds_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    return gspread.authorize(creds)


# =========================
# NSE FETCH
# =========================

def fetch_nse_data(deal_type="Bulk deals"):
    import urllib.parse
    from playwright.sync_api import sync_playwright

    encoded_type = urllib.parse.quote(deal_type)

    api_url = (
        "https://www.nseindia.com/api/historicalOR/bulk-block-short-deals"
        f"?dealType={encoded_type}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-http2",
            ],
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            ignore_https_errors=True,
            extra_http_headers={
                "accept": "application/json, text/plain, */*",
                "referer": "https://www.nseindia.com/",
                "x-requested-with": "XMLHttpRequest",
            },
        )

        request = context.request

        # Light warm-up request, but do not fail if NSE times out here
        try:
            request.get("https://www.nseindia.com", timeout=15000)
        except Exception as e:
            print("Warm-up skipped:", str(e))

        for attempt in range(5):
            try:
                print(f"Fetching {deal_type}, attempt {attempt + 1}")

                response = request.get(api_url, timeout=30000)

                print("Status Code:", response.status)

                if response.status != 200:
                    time.sleep(2)
                    continue

                data = response.json()
                rows = data.get("data", [])

                print("Rows Found:", len(rows))

                if rows:
                    browser.close()
                    return rows

            except Exception as e:
                print("Fetch error:", str(e))
                time.sleep(2)

        browser.close()
        return []
# =========================
# BUILD DATAFRAME
# =========================

def build_dataframe(data):

    rows = []

    for item in data:

        qty = float(item.get("quantity", 0) or 0)
        price = float(item.get("price", 0) or 0)

        value_cr = round(
            (qty * price) / 10000000,
            2
        )

        rows.append([
            item.get("date", ""),
            item.get("symbol", ""),
            item.get("name", ""),
            item.get("clientName", ""),
            item.get("buySell", ""),
            qty,
            price,
            value_cr
        ])

    return pd.DataFrame(
        rows,
        columns=[
            "DATE",
            "SYMBOL",
            "SECURITY NAME",
            "CLIENT NAME",
            "TYPE",
            "QUANTITY",
            "PRICE",
            "VALUE_CR"
        ]
    )


# =========================
# UPDATE SHEET
# =========================

def update_sheet(ws, df):

    ws.clear()

    if df.empty:

        ws.update(
            "A1",
            [["NO DATA RETURNED"]]
        )

        return

    values = [df.columns.tolist()] + df.values.tolist()

    ws.update(
        "A1",
        values
    )


# =========================
# MAIN
# =========================

def main():

    client = auth_google()

    spreadsheet = client.open_by_key(
        SPREADSHEET_ID
    )

    # BULK

    bulk_data = fetch_nse_data(
        "Bulk deals"
    )

    print("Bulk Records:", len(bulk_data))

    bulk_df = build_dataframe(
        bulk_data
    )

    bulk_ws = spreadsheet.worksheet(
        "📦 Bulk Deals"
    )

    update_sheet(
        bulk_ws,
        bulk_df
    )

    # BLOCK

    block_data = fetch_nse_data(
        "Block deals"
    )

    print("Block Records:", len(block_data))

    block_df = build_dataframe(
        block_data
    )

    block_ws = spreadsheet.worksheet(
        "🧱 Block Deals"
    )

    update_sheet(
        block_ws,
        block_df
    )

    print("SYNC COMPLETE")


if __name__ == "__main__":
    main()
