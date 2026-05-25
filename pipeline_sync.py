import os
import json
import random
import time
import gspread
from google.oauth2.service_account import Credentials
from curl_cffi import requests

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURATION ENGINE
# ══════════════════════════════════════════════════════════════════════════
SPREADSHEET_ID = "1vnrsybq4tX4BFvDupY5y8oxFLh0LyuPF_dm-viSqxWM"  # <-- Make sure your real Sheet ID string is pasted here

BULK_HEADERS = ['DATE', 'SYMBOL', 'SECURITY NAME', 'CLIENT NAME', 'TYPE', 'QUANTITY', 'EXECUTION PRICE', 'VALUE (₹ CR)', 'INSTITUTION_FLAG', 'SIZE INDEX', 'SIGNAL FIELD']
BLOCK_HEADERS = ['DATE', 'SYMBOL', 'SECURITY NAME', 'CLIENT NAME', 'TYPE', 'QUANTITY', 'PRICE', 'VALUE (₹ CR)', 'INSTITUTION_FLAG', 'INTERCEPT SIGNAL']

INSTITUTIONS = [
    'SBI MF', 'HDFC MF', 'ICICI PRUDENTIAL', 'KOTAK MF', 'AXIS MF', 'MIRAE ASSET', 
    'NIPPON', 'DSP', 'FRANKLIN', 'UTI MF', 'MOTILAL OSWAL', 'MORGAN STANLEY', 
    'GOLDMAN SACHS', 'NOMURA', 'CLSA', 'SOCIETE GENERALE', 'LIC', 'BLACKROCK'
]

def fetch_nse_large_deals(deal_type="bulk_deals"):
    """Fetches transaction data by target routing to modern NSE standalone resource paths."""
    cache_buster = random.randint(10000, 99999)
    
    # FIX: Route directly to the modern structural paths instead of old query strings
    if deal_type == "bulk_deals":
        url = f"https://www.nseindia.com/api/large-deals/bulk?v={cache_buster}"
    else:
        url = f"https://www.nseindia.com/api/large-deals/block?v={cache_buster}"
        
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }
    
    try:
        session = requests.Session(impersonate="chrome")
        session.headers.update(base_headers)
        
        # Step 1: Hit root domain for core cookie state assignment
        print("[+] Step 1: Requesting root exchange tokens...")
        session.get("https://www.nseindia.com/", timeout=15)
        time.sleep(2)
        
        # Step 2: Hit landing page container to grab security tracking keys
        print("[+] Step 2: Extracting structural tracking keys...")
        session.get("https://www.nseindia.com/market-data/large-deals", timeout=15)
        time.sleep(2)
        
        # AJAX Endpoint specific transmission headers
        api_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "https://www.nseindia.com/market-data/large-deals",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        # Step 3: Call the updated URL path directly
        print(f"[+] Step 3: Requesting direct path stream from: {url}")
        response = session.get(url, headers=api_headers, timeout=15)
        
        print(f"[!] Server Network Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            raw_data = response.json()
            
            # Extract lists cleanly out of the JSON response block
            if isinstance(raw_data, dict):
                # The modern endpoint uses lowercase 'data' array nesting
                data_list = raw_data.get('data', raw_data.get('DATA', []))
                if isinstance(data_list, list) and len(data_list) > 0:
                    return data_list
            elif isinstance(raw_data, list):
                return raw_data
                
            print("⚠️ Endpoint route hit cleanly, but active transaction list arrays are currently empty.")
            
    except Exception as e:
        print(f"[-] Critical exception during data pull sequence: {str(e)}")
        
    return []

def clear_and_reset_tab(worksheet, headers):
    try:
        row_count = worksheet.row_count
        if row_count > 2:
            worksheet.delete_rows(3, row_count)
    except Exception as e:
        print(f"[!] Truncation maintenance note: {e}")
    worksheet.update(range_name='A2', values=[headers], value_input_option='USER_ENTERED')

def pipeline_sync_to_sheets():
    print("🚀 Booting Velocity Institutional Smart Money Flow Pipeline...")
    
    creds_json = os.environ.get("GOOGLE_CREDS_SECRET")
    if not creds_json:
        raise ValueError("CRITICAL ERROR: GOOGLE_CREDS_SECRET repository variable is completely empty!")
        
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
            
            sym_raw = item.get('BD_SYMBOL', item.get('symbol', ''))
            if not sym_raw: continue
            
            sym = f"NSE:{str(sym_raw).upper()}"
            client_name = item.get('BD_CLIENT_NAME', item.get('clientName', '—'))
            bs = str(item.get('BD_BUY_SELL', item.get('buySell', ''))).upper()
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
                sym, item.get('BD_SCRIP_NAME', item.get('name', '—')),
                client_name, "BUY" if is_buy else "SELL", qty, px, cr_val, is_inst, size_index, signal
            ])
            
        if rows_to_write:
            clear_and_reset_tab(bulk_tab, BULK_HEADERS)
            bulk_tab.append_rows(rows_to_write, value_input_option="USER_ENTERED")
            print(f"✅ Target Verification Passed: {len(rows_to_write)} Bulk Deal rows written.")
            any_data_synced = True
    else:
        print("⚠️ Bulk data array empty. Stamping placeholder.")
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
            
            sym_raw = item.get('BD_SYMBOL', item.get('symbol', ''))
            if not sym_raw: continue
            
            sym = f"NSE:{str(sym_raw).upper()}"
            client_name = item.get('BD_CLIENT_NAME', item.get('clientName', '—'))
            bs = str(item.get('BD_BUY_SELL', item.get('buySell', ''))).upper()
            qty = float(item.get('BD_QTY_TRD', item.get('quantity', 0)))
            px = float(item.get('BD_TP_WATP', item.get('price', 0)))
            cr_val = round((qty * px) / 1e7, 2)
            
            rows_to_write.append([
                item.get('BD_DT_DATE', item.get('date', '')),
                sym, item.get('BD_SCRIP_NAME', item.get('name', '—')),
                client_name, "BUY" if "BUY" in bs else "SELL",
                qty, px, cr_val, "YES", "🧱 CONSOLIDATION CROSS"
            ])
            
        if rows_to_write:
            clear_and_reset_tab(block_tab, BLOCK_HEADERS)
            block_tab.append_rows(rows_to_write, value_input_option="USER_ENTERED")
            print(f"✅ Target Verification Passed: {len(rows_to_write)} Block Deal rows written.")
            any_data_synced = True
    else:
        print("⚠️ Block data array empty. Stamping placeholder.")
        clear_and_reset_tab(block_tab, BLOCK_HEADERS)
        block_tab.append_rows([["—", "No transactions logged on the exchange today.", "—", "—", "—", 0, 0, 0, "—", "—"]], value_input_option="USER_ENTERED")

    # ---- 3. DASHBOARD STATUS UPDATE ----
    try:
        dash_tab = sheet.worksheet("🎯 Platform Dashboard")
        sync_time = time.strftime("%d %b %Y @ %H:%M IST", time.localtime(time.time() + 19800))
        status_text = f"System Sync Status: Active via Actions Engine Pipeline | Last Data Lock: {sync_time}"
        if not any_data_synced:
            status_text += " (Market Dormant/Offline)"
        dash_tab.update(range_name='A2', values=[[status_text]], value_input_option='USER_ENTERED')
        print("📊 Dashboard status flag locked successfully.")
    except Exception as e:
        print(f"[-] Dashboard status update skipped: {e}")

if __name__ == "__main__":
    pipeline_sync_to_sheets()
