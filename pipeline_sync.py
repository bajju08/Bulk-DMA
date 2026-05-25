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

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page()

        page.goto(
            "https://www.nseindia.com/report-detail/display-bulk-and-block-deals",
            wait_until="networkidle",
            timeout=120000
        )

        time.sleep(5)

        if deal_type == "Bulk deals":

            api_url = (
                "https://www.nseindia.com/api/"
                "historicalOR/bulk-block-short-deals"
                "?dealType=Bulk%20deals"
            )

        else:

            api_url = (
                "https://www.nseindia.com/api/"
                "historicalOR/bulk-block-short-deals"
                "?dealType=Block%20deals"
            )

        response = page.goto(api_url)

        data = response.json()

        browser.close()

        return data.get("data", [])


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
