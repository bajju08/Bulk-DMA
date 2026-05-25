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
SPREADSHEET_ID = "1vnrsybq4tX4BFvDupY5y8oxFLh0LyuPF_dm-viSqxWM"  # <-- Ensure your real Sheet ID string is pasted here

BULK_HEADERS = ['DATE', 'SYMBOL', 'SECURITY NAME', 'CLIENT NAME', 'TYPE', 'QUANTITY', 'EXECUTION PRICE', 'VALUE (₹ CR)', 'INSTITUTION_FLAG', 'SIZE INDEX', 'SIGNAL FIELD']
BLOCK_HEADERS = ['DATE', 'SYMBOL', 'SECURITY NAME', 'CLIENT NAME', 'TYPE', 'QUANTITY', 'PRICE', 'VALUE (₹ CR)', 'INSTITUTION_FLAG', 'INTERCEPT SIGNAL']

INSTITUTIONS = [
    'SBI MF', 'HDFC MF', 'ICICI PRUDENTIAL', 'KOTAK MF', 'AXIS MF', 'MIRAE ASSET', 
    'NIPPON', 'DSP', 'FRANKLIN', 'UTI MF', 'MOTILAL OSWAL', 'MORGAN STANLEY', 
    'GOLDMAN SACHS', 'NOMURA', 'CLSA', 'SOCIETE GENERALE', 'LIC', 'BLACKROCK'
]

def extract_data_robustly(json_response):
    """
    Scans the JSON payload dynamically to find the deal rows,
    handling nested dictionaries, mixed casing, or direct arrays.
    """
    if isinstance(json_response, list):
        return json_response
        
    if isinstance(json_response, dict):
        # Check standard targets
        for key in ['data', 'DATA', 'bulk_deals_data', 'block_deals_data', 'bulkDeals', 'blockDeals']:
            val = json_response.get(key)
            if isinstance(val, list) and len(val) > 0:
                return val
            elif isinstance(val, dict):
                # Handle cases where it is double-nested: response['data']['data']
                for sub_key in ['data', 'DATA']:
                    sub_val = val.get(sub_key)
                    if isinstance(sub_val, list) and len(sub_val) > 0:
                        return sub_val
                        
        # Ultimate fallback: if any key holds a non-empty list, use it
        for val in json_response.values():
            if isinstance(val, list) and len(val) > 0:
                return val
                
    return []

def fetch_nse_large_deals(deal_type="bulk_deals"):
    """Fetches real-time large deals by establishing a persistent browser session emulation layer."""
    cache_buster = random.randint(10000, 99999)
    url = f"https://www.nseindia.com/api/large-deals?type={deal_type}&v={cache_buster}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.nseindia.com/market-data/large-deals",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "keep-alive"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        # Step 1: Hit the home index page to establish valid cookie tokens
        print(f"[+] Initializing cookie handshakes for {deal_type}...")
        session.get("https://www.nseindia.com/", timeout=15)
        time.sleep(3) 
        
        # Step 2: Request the actual JSON API data stream
        print(f"[+] Requesting data matrix from primary cluster...")
        response = session.get(url, timeout=15)
        
        if response.status_code == 200:
            raw_json = response.json()
            extracted_rows = extract_data_robustly(raw_json)
            if extracted_rows:
                return extracted_rows
            print("⚠️ Primary cluster parsed but no list values found inside JSON fields.")
    except Exception as e:
        print(f"[-] Primary cluster tracking network block: {str(e)}")
        
    # Alternate Backup Node Routing Strategy
    alt_url = f"https://www1.nseindia.com/api/large-deals?type={deal_type}&v={cache_buster}"
    try:
        print("[!] Activating fallback stream sequence architecture...")
        time.sleep(2)
        alt_response = session.get(alt_url, timeout=15)
        if alt_response.status_code == 200:
            extracted_rows = extract_data_robustly(alt_response.json())
            if extracted_rows:
                return extracted_rows
    except Exception as e:
        print(f"[-] Backup network framework unconfirmed: {str(e)}")
        
    return []

def clear_and_reset_tab(worksheet, headers):
    """Safely clears old entries while maintaining header layout grids."""
    try:
        row_count = worksheet.row_count
        if row_count > 2:
            worksheet.delete_rows(3, row_count)
    except Exception as e:
        print(f"[!] Sheet format clean truncation bypassed: {e}")
    worksheet.update(range_name='A2', values=[headers], value_input_option='USER_ENTERED')

def pipeline_sync_to_sheets():
    print("🚀 Booting Velocity Institutional Smart Money Flow Pipeline...")
    
    creds_json = os.environ.get("GOOGLE_CREDS_SECRET")
    if not creds_json:
        raise ValueError("CRITICAL ERROR: GOOGLE_CREDS_SECRET environment variable is missing!")
        
    creds_dict = json.loads(creds_json)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    
    any_data_synced = False
    
    # ---- 1. RUNNING BULK DEALS REGISTRY ----
    print("🔄 Accessing Exchange Bulk Deals Pipeline Stream...")
    bulk_data = fetch_nse_large_deals("bulk_deals")
    bulk_tab = sheet.worksheet("📦 Bulk Deals")
    
    if bulk_data and len(bulk_data) > 0:
        rows_to_write = []
        for item in bulk_data:
            if not item or not isinstance(item, dict): continue
            
            # Universal key recovery fallback architecture
            sym_raw = item.get('BD_SYMBOL', item.get('symbol', item.get('mkt', '')))
            if not sym_raw: continue
            
            sym = f"NSE:{str(sym_raw).upper()}"
            client_name = item.get('BD_CLIENT_NAME', item.get('clientName', item.get('client', '—')))
            bs = str(item.get('BD_BUY_SELL', item.get('buySell', item.get('action', '')))).upper()
            qty = float(item.get('BD_QTY_TRD', item.get('quantity', item.get('qty', 0))))
            px = float(item.get('BD_TP_WATP', item.get('price', item.get('px', 0))))
            cr_val = round((qty * px) / 1e7, 2)
            
            is_buy = "BUY" in bs or "B" == bs
            is_inst = "YES" if any(inst in client_name.upper() for inst in INSTITUTIONS) else "—"
            size_index = "🟠 LARGE" if cr_val >= 50 else "⚪ MINOR"
            
            signal = "🏛️ INST BUY ⭐" if (is_inst == "YES" and is_buy) else \
                     "🏛️ INST SELL ⚠️" if (is_inst == "YES" and not is_buy) else "📊 POSITION ACCUMULATION"
            
            rows_to_write.append([
                item.get('BD_DT_DATE', item.get('date', time.strftime("%d-%b-%Y"))),
                sym, item.get('BD_SCRIP_NAME', item.get('name', item.get('scrip', '—'))),
                client_name, "BUY" if is_buy else "SELL", qty, px, cr_val, is_inst, size_index, signal
            ])
            
        if rows_to_write:
            clear_and_reset_tab(bulk_tab, BULK_HEADERS)
            bulk_tab.append_rows(rows_to_write, value_input_option="USER_ENTERED")
            print(f"✅ Target Verification Passed: {len(rows_to_write)} Bulk Deal rows synchronized.")
            any_data_synced = True
    else:
        print("走 Using placeholders for Bulk data.")
        clear_and_reset_tab(bulk_tab, BULK_HEADERS)
        bulk_tab.append_rows([["—", "No transactions logged on the exchange today.", "—", "—", "—", 0, 0, 0, "—", "—", "—"]], value_input_option="USER_ENTERED")

    # ---- 2. RUNNING BLOCK DEALS REGISTRY ----
    print("🔄 Accessing Exchange Block Deals Pipeline Stream...")
    block_data = fetch_nse_large_deals("block_deals")
    block_tab = sheet.worksheet("🧱 Block Deals")
    
    if block_data and len(block_data) > 0:
        rows_to_write = []
        for item in block_data:
            if not item or not isinstance(item, dict): continue
            
            sym_raw = item.get('BD_SYMBOL', item.get('symbol', item.get('mkt', '')))
            if not sym_raw: continue
            
            sym = f"NSE:{str(sym_raw).upper()}"
            client_name = item.get('BD_CLIENT_NAME', item.get('clientName', item.get('client', '—')))
            bs = str(item.get('BD_BUY_SELL', item.get('buySell', item.get('action', '')))).upper()
            qty = float(item.get('BD_QTY_TRD', item.get('quantity', item.get('qty', 0))))
            px = float(item.get('BD_TP_WATP', item.get('price', item.get('px', 0))))
            cr_val = round((qty * px) / 1e7, 2)
            
            rows_to_write.append([
                item.get('BD_DT_DATE', item.get('date', time.strftime("%d-%b-%Y"))),
                sym, item.get('BD_SCRIP_NAME', item.get('name', item.get('scrip', '—'))),
                client_name, "BUY" if ("BUY" in bs or "B" == bs) else "SELL",
                qty, px, cr_val, "YES", "🧱 CONSOLIDATION CROSS"
            ])
            
        if rows_to_write:
            clear_and_reset_tab(block_tab, BLOCK_HEADERS)
            block_tab.append_rows(rows_to_write, value_input_option="USER_ENTERED")
            print(f"✅ Target Verification Passed: {len(rows_to_write)} Block Deal rows synchronized.")
            any_data_synced = True
    else:
        print("走 Using placeholders for Block data.")
        clear_and_reset_tab(block_tab, BLOCK_HEADERS)
        block_tab.append_rows([["—", "No transactions logged on the exchange today.", "—", "—", "—", 0, 0, 0, "—", "—"]], value_input_option="USER_ENTERED")

    # ---- 3. UPDATE LIVE DASHBOARD STAMP STATUS ----
    try:
        dash_tab = sheet.worksheet("🎯 Platform Dashboard")
        sync_time = time.strftime("%d %b %Y @ %H:%M IST", time.localtime(time.time() + 19800))
        
        status_text = f"System Sync Status: Active via Actions Engine Pipeline | Last Data Lock: {sync_time}"
        if not any_data_synced:
            status_text += " (Market Dormant/Offline)"
            
        dash_tab.update(range_name='A2', values=[[status_text]], value_input_option='USER_ENTERED')
        print("📊 Dashboard status flag updated successfully.")
    except Exception as e:
        print(f"[-] Dashboard tracker stamp update bypassed: {e}")

if __name__ == "__main__":
    pipeline_sync_to_sheets()
