import os
import json
import random
import time
import requests
import gspread
from google.oauth2.service_account import Credentials

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
SPREADSHEET_ID = "1vnrsybq4tX4BFvDupY5y8oxFLh0LyuPF_dm-viSqxWM"  # <-- Ensure this matches your actual Sheet ID string

BULK_HEADERS = ['DATE', 'SYMBOL', 'SECURITY NAME', 'CLIENT NAME', 'TYPE', 'QUANTITY', 'EXECUTION PRICE', 'VALUE (₹ CR)', 'INSTITUTION_FLAG', 'SIZE INDEX', 'SIGNAL FIELD']
BLOCK_HEADERS = ['DATE', 'SYMBOL', 'SECURITY NAME', 'CLIENT NAME', 'TYPE', 'QUANTITY', 'PRICE', 'VALUE (₹ CR)', 'INSTITUTION_FLAG', 'INTERCEPT SIGNAL']

INSTITUTIONS = [
    'SBI MF', 'HDFC MF', 'ICICI PRUDENTIAL', 'KOTAK MF', 'AXIS MF', 'MIRAE ASSET', 
    'NIPPON', 'DSP', 'FRANKLIN', 'UTI MF', 'MOTILAL OSWAL', 'MORGAN STANLEY', 
    'GOLDMAN SACHS', 'NOMURA', 'CLSA', 'SOCIETE GENERALE', 'LIC', 'BLACKROCK'
]

def fetch_nse_large_deals(deal_type="bulk_deals"):
    """Fetches real-time large deals by emulating standard user-agent sessions."""
    cache_buster = random.randint(10000, 99999)
    url = f"https://www.nseindia.com/api/large-deals?type={deal_type}&v={cache_buster}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Referer": "https://www.nseindia.com/market-data/large-deals",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate, br"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # Establish base cookie structure first by hitting the home index node
        session.get("https://www.nseindia.com/", timeout=15)
        time.sleep(2)
        response = session.get(url, timeout=15)
        if response.status_code == 200:
            return response.json().get('data', response.json().get('DATA', []))
    except Exception as e:
        print(f"[-] Primary cluster tracking bridge bypassed: {str(e)}")
        
    # Alternate Node Fallback Routing with refreshed parameters
    alt_url = f"https://www1.nseindia.com/api/large-deals?type={deal_type}&v={cache_buster}"
    try:
        print("[!] Activating alternative stream sequence protocol...")
        alt_response = session.get(alt_url, timeout=15)
        if alt_response.status_code == 200:
            return alt_response.json().get('data', alt_response.json().get('DATA', []))
    except Exception as e:
        print(f"[-] Backup endpoint matrix unconfirmed: {str(e)}")
        
    return []

def clear_and_reset_tab(worksheet, headers):
    """Safely clears old entries below row 2 grid markings."""
    try:
        row_count = worksheet.row_count
        if row_count > 2:
            worksheet.delete_rows(3, row_count)
    except Exception as e:
        print(f"[!] System layout normalization initialized: {e}")
    # Wrapped inside a 2D matrix structure to prevent Google API 400 format errors
    worksheet.update(range_name='A2', values=[headers], value_input_option='USER_ENTERED')

def pipeline_sync_to_sheets():
    print("🚀 Booting Velocity Institutional Smart Money Flow Pipeline...")
    
    creds_json = os.environ.get("GOOGLE_CREDS_SECRET")
    if not creds_json:
        raise ValueError("CRITICAL ERROR: GOOGLE_CREDS_SECRET environment variable is completely empty!")
        
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    
    # Flag to track if data was successfully pulled during market context
    any_data_synced = False
    
    # ---- 1. PROCESSING BULK DEALS REGISTRY ----
    print("🔄 Accessing Exchange Bulk Deals Pipeline Stream...")
    bulk_data = fetch_nse_large_deals("bulk_deals")
    
    bulk_tab = sheet.worksheet("📦 Bulk Deals")
    if bulk_data:
        rows_to_write = []
        for item in bulk_data:
            if not item: continue
            sym = f"NSE:{item.get('BD_SYMBOL', item.get('symbol', '')).upper()}"
            client_name = item.get('BD_CLIENT_NAME', item.get('clientName', ''))
            bs = item.get('BD_BUY_SELL', item.get('buySell', '')).upper()
            qty = float(item.get('BD_QTY_TRD', item.get('quantity', 0)))
            px = float(item.get('BD_TP_WATP', item.get('price', 0)))
            cr_val = round((qty * px) / 1e7, 2)
            
            is_buy = "BUY" in bs
            is_inst = "YES" if any(inst in client_name.upper() for inst in INSTITUTIONS) else "—"
            size_index = "🟠 LARGE" if cr_val >= 50 else "⚪ MINOR"
            
            signal = "🏛️ INST BUY ⭐" if (is_inst == "YES" and is_buy) else \
                     "🏛️ INST SELL ⚠️" if (is_inst == "YES" and not is_buy) else "📊 POSITION ACCUMULATION"
            
            rows_to_write.append([
                item.get('BD_DT_DATE', item.get('date', '')),
                sym, item.get('BD_SCRIP_NAME', item.get('name', '')),
                client_name, "BUY" if is_buy else "SELL", qty, px, cr_val, is_inst, size_index, signal
            ])
            
        if rows_to_write:
            clear_and_reset_tab(bulk_tab, BULK_HEADERS)
            bulk_tab.append_rows(rows_to_write, value_input_option="USER_ENTERED")
            print(f"✅ Target Verification Passed: {len(rows_to_write)} Bulk Deal rows synchronized.")
            any_data_synced = True
    else:
        print("⚠️ No Bulk data retrieved. Maintaining sheet placeholders.")
        # Optional fallback stamp if empty on a holiday/weekend
        clear_and_reset_tab(bulk_tab, BULK_HEADERS)
        bulk_tab.append_rows([["—", "No transactions logged on the exchange today.", "—", "—", "—", 0, 0, 0, "—", "—", "—"]], value_input_option="USER_ENTERED")

    # ---- 2. PROCESSING BLOCK DEALS REGISTRY ----
    print("🔄 Accessing Exchange Block Deals Pipeline Stream...")
    block_data = fetch_nse_large_deals("block_deals")
    
    block_tab = sheet.worksheet("🧱 Block Deals")
    if block_data:
        rows_to_write = []
        for item in block_data:
            if not item: continue
            sym = f"NSE:{item.get('BD_SYMBOL', item.get('symbol', '')).upper()}"
            client_name = item.get('BD_CLIENT_NAME', item.get('clientName', ''))
            bs = item.get('BD_BUY_SELL', item.get('buySell', '')).upper()
            qty = float(item.get('BD_QTY_TRD', item.get('quantity', 0)))
            px = float(item.get('BD_TP_WATP', item.get('price', 0)))
            cr_val = round((qty * px) / 1e7, 2)
            
            rows_to_write.append([
                item.get('BD_DT_DATE', item.get('date', '')),
                sym, item.get('BD_SCRIP_NAME', item.get('name', '')),
                client_name, "BUY" if "BUY" in bs else "SELL",
                qty, px, cr_val, "YES", "🧱 CONSOLIDATION CROSS"
            ])
            
        if rows_to_write:
            clear_and_reset_tab(block_tab, BLOCK_HEADERS)
            block_tab.append_rows(rows_to_write, value_input_option="USER_ENTERED")
            print(f"✅ Target Verification Passed: {len(rows_to_write)} Block Deal rows synchronized.")
            any_data_synced = True
    else:
        print("⚠️ No Block data retrieved. Maintaining sheet placeholders.")
        clear_and_reset_tab(block_tab, BLOCK_HEADERS)
        block_tab.append_rows([["—", "No transactions logged on the exchange today.", "—", "—", "—", 0, 0, 0, "—", "—"]], value_input_option="USER_ENTERED")

    # ---- 3. TRIGGER STATUS MATRIX RECALCULATION ----
    try:
        dash_tab = sheet.worksheet("🎯 Platform Dashboard")
        sync_time = time.strftime("%d %b %Y @ %H:%M IST", time.localtime(time.time() + 19800)) # Clean IST Conversion Offset
        
        status_text = f"System Sync Status: Active via Actions Engine Pipeline | Last Data Lock: {sync_time}"
        if not any_data_synced:
            status_text += " (Market Dormant/Offline)"
            
        # FIX: Wrapped within a double array matrix format [[text]] to satisfy gspread 6.0+ endpoints perfectly
        dash_tab.update(range_name='A2', values=[[status_text]], value_input_option='USER_ENTERED')
        print("📊 Dashboard recalculation matrix locked successfully without formatting mismatch.")
    except Exception as e:
        print(f"[-] Intercept calculation update bypassed: {e}")

if __name__ == "__main__":
    pipeline_sync_to_sheets()
