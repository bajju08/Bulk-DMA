import os
import json
import time
import random
import urllib.parse
import requests
import pandas as pd
import gspread

from google.oauth2.service_account import Credentials


SPREADSHEET_ID = "1vnrsybq4tX4BFvDupY5y8oxFLh0LyuPF_dm-viSqxWM"


# =========================
# GOOGLE AUTH
# =========================

def auth_google():

    creds_json = os.environ.get("GOOGLE_CREDS_SECRET")

    if not creds_json:
        raise Exception("GOOGLE_CREDS_SECRET missing")

    creds_dict = json.loads(creds_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    client = gspread.authorize(creds)

    return client


# =========================
# NSE SESSION
# =========================

def create_session():

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive"
    }

    session.headers.update(headers)

    # IMPORTANT
    session.get(
        "https://www.nseindia.com",
        timeout=20
    )

    time.sleep(3)

    return session


# =========================
# FETCH NSE DATA
# =========================

def fetch_nse_data(deal_type="Bulk deals"):

    session = create_session()

    encoded_type = urllib.parse.quote(deal_type)

    urls = [

        f"https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?dealType={encoded_type}",

        f"https://www.nseindia.com/api/historicalOR/bulk-block-short-deals?dealType={encoded_type}&from=01-01-2025&to=31-12-2026"
    ]

    for url in urls:

        try:

            print(f"Trying URL: {url}")

            response = session.get(
                url,
                timeout=30,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Referer": "https://www.nseindia.com/report-detail/display-bulk-and-block-deals",
                    "User-Agent": "Mozilla/5.0",
                    "X-Requested-With": "XMLHttpRequest"
                }
            )

            print("Status Code:", response.status_code)

            if response.status_code != 200:
                continue

            data = response.json()

            if isinstance(data, dict):

                rows = data.get("data", [])

                print("Rows Found:", len(rows))

                if rows:
                    return rows

        except Exception as e:

            print("Fetch Error:", str(e))

    return []


# =========================
# BUILD DATAFRAME
# =========================

def build_dataframe(data):

    rows = []

    for item in data:

        qty = float(item.get("quantity", 0) or 0)
        price = float(item.get("price", 0) or 0)

        value_cr = round((qty * price) / 10000000, 2)

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

    df = pd.DataFrame(rows, columns=[
        "DATE",
        "SYMBOL",
        "SECURITY NAME",
        "CLIENT NAME",
        "TYPE",
        "QUANTITY",
        "PRICE",
        "VALUE_CR"
    ])

    return df


# =========================
# WRITE TO GOOGLE SHEETS
# =========================

def update_sheet(worksheet, dataframe):

    worksheet.clear()

    if dataframe.empty:

        worksheet.update(
            "A1",
            [["NO DATA RETURNED FROM NSE"]]
        )

        return

    values = [
        dataframe.columns.tolist()
    ] + dataframe.values.tolist()

    worksheet.update(
        "A1",
        values,
        value_input_option="USER_ENTERED"
    )


# =========================
# MAIN
# =========================

def main():

    print("STARTING NSE SYNC")

    client = auth_google()

    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    # ================= BULK =================

    print("FETCHING BULK DEALS")

    bulk_data = fetch_nse_data("Bulk deals")

    print("BULK RECORDS:", len(bulk_data))

    bulk_df = build_dataframe(bulk_data)

    bulk_sheet = spreadsheet.worksheet("📦 Bulk Deals")

    update_sheet(
        bulk_sheet,
        bulk_df
    )

    # ================= BLOCK =================

    print("FETCHING BLOCK DEALS")

    block_data = fetch_nse_data("Block deals")

    print("BLOCK RECORDS:", len(block_data))

    block_df = build_dataframe(block_data)

    block_sheet = spreadsheet.worksheet("🧱 Block Deals")

    update_sheet(
        block_sheet,
        block_df
    )

    # ================= DASHBOARD =================

    try:

        dashboard = spreadsheet.worksheet("🎯 Platform Dashboard")

        current_time = time.strftime(
            "%d-%m-%Y %H:%M:%S"
        )

        dashboard.update(
            "A2",
            [[f"✅ LAST SYNC SUCCESSFUL : {current_time}"]]
        )

    except Exception as e:

        print("Dashboard Update Error:", str(e))

    print("SYNC COMPLETED")


if __name__ == "__main__":
    main()
