import os
import sys
import pandas as pd
import numpy as np
import math
import calendar
import re
import html
import shutil
import glob
import json
import threading
import concurrent.futures
import io
from datetime import datetime, timedelta
import traceback
import gradio as gr

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG
# ==============================================================================
class Config:
    VERSION = "V6.5 OMNI-QUANT ULTRA SCANNER (7 SENSORS & 3 ANALYTIC CORES)" 
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    BACKUP_PREFIX = "Ket_Qua_Loto27_Backup_" 
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    BASE_PTS = 10.0
    LOOKBACK_DAYS = 21
    STORM_THRESHOLD = 0.35
    
    ACTIVE_MODE = "🤖 [VERSION 6.5] V6.5 OMNI TIERED QUANT (LOTO & 7-SENSOR STOCKS ULTRA)"
    
    MENU_OPTIONS = [
        "🔄 1. ĐỒNG BỘ & CẬP NHẬT DỮ LIỆU LOTO",
        "🎯 2. KHUYẾN NGHỊ LỆNH GIAO DỊCH",
        "🔍 3. KIỂM TOÁN CHUYÊN SÂU",
        "📈 4. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 5. BẢNG KẾT QUẢ LOTO TRUYỀN THỐNG",
        "🤖 6. BỘ NÃO AI (QUÉT LỊCH SỬ DB)",
        "⚖️ 7. HỆ THỐNG RADAR ARBITRAGE (TỶ LỆ)",
        "📈 8. CẢM BIẾN DÒNG TIỀN CHỨNG KHOÁN (7-SENSOR ULTRA)"
    ]

# ==============================================================================
# 🛠️ BLOCK 2: UTILITIES
# ==============================================================================
class Utils:
    @staticmethod
    def get_vn_time():
        return datetime.utcnow() + timedelta(hours=7)

    @staticmethod
    def chuan_hoa_ngay(ngay_raw):
        if pd.isna(ngay_raw) or not str(ngay_raw).strip() or str(ngay_raw).lower() == 'nan': return None
        ngay_str = str(ngay_raw).split(" ")[0] 
        match_ymd = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', ngay_str)
        if match_ymd:
            y, m, d = match_ymd.groups()
        else:
            match_dmy = re.search(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', ngay_str)
            if match_dmy: d, m, y = match_dmy.groups()
            else: return None
        if len(d) == 1: d = "0" + d
        if len(m) == 1: m = "0" + m
        str_chuan = f"{d}/{m}/{y}"
        try:
            dt_obj = datetime.strptime(str_chuan, "%d/%m/%Y")
            now_vn = Utils.get_vn_time()
            if dt_obj.year < 2000 or dt_obj > now_vn + timedelta(days=1): return None
            return dt_obj, str_chuan
        except Exception: return None

    @staticmethod
    def check_valid_number(val, name):
        if val is None or str(val).strip() == "": return False, f"🛑 LỖI: Nhập '{name}'."
        try:
            if float(val) <= 0: return False, f"🛑 LỖI: '{name}' > 0."
            return True, ""
        except: return False, f"🛑 LỖI: '{name}' sai định dạng."

# ==============================================================================
# 🕸️ BLOCK 3: CRAWLER TỰ ĐỘNG LOTO
# ==============================================================================
class Crawler:
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    @staticmethod
    def fetch_single_date(target_date):
        if not HAS_REQUESTS: return None
        date_str_url = target_date.strftime("%d-%m-%Y")
        date_str_db = target_date.strftime("%d/%m/%Y")
        
        numeric_domains = [f"ketqua{i}.net" for i in range(16, 51)] + [f"ketqua{i}.net" for i in range(1, 16)]
        urls = [f"https://{dom}/xo-so-truyen-thong.php?ngay={date_str_url}" for dom in numeric_domains]
        
        for url in urls:
            try:
                res = requests.get(url, headers=Crawler.HEADERS, timeout=7)
                if res.status_code == 200:
                    tables = re.findall(r'<table.*?>(.*?)</table>', res.text, re.IGNORECASE | re.DOTALL)
                    for t in tables:
                        clean_text = re.sub(r'<[^>]+>', ' ', html.unescape(t))
                        nums = re.findall(r'\b\d{2,5}\b', clean_text)
                        if len(nums) >= 27:
                            prizes = [x[-2:] for x in nums[:27]]
                            return {"Ngày": date_str_db, "Kết Quả Loto": " ".join(prizes)}
            except Exception: pass
        return None

# ==============================================================================
# 📊 BLOCK 4: DATABASE MANAGER
# ==============================================================================
class GoogleSheetsManager:
    @staticmethod
    def get_worksheet():
        if not HAS_GSPREAD: return None, "Thiếu thư viện 'gspread'."
        sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Ket_Qua_Loto27").strip()
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS", "").strip()
        
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = None
        if creds_json_str:
            try:
                creds_dict = json.loads(creds_json_str)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            except Exception: pass
                
        if not creds: return None, "Chưa cấu hình Google Credentials."
        try:
            gc = gspread.authorize(creds)
            ws = gc.open_by_key(sheet_id).sheet1 if sheet_id else gc.open(sheet_name).sheet1
            return ws, "OK"
        except Exception as e: return None, str(e)

class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        if not os.path.exists(Config.DATA_FILE):
            backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
            if backups: shutil.copy(backups[0], Config.DATA_FILE)
            else:
                pd.DataFrame(columns=["Ngày", "Kết Quả Loto"]).to_excel(Config.DATA_FILE, index=False)
                return db, "Tệp rỗng"
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str)
            for _, row in df.iterrows():
                res_date = Utils.chuan_hoa_ngay(row.iloc[0])
                if not res_date: continue
                dt_obj, ngay_str = res_date
                loto_raw = re.sub(r"[^\d\s]", " ", str(row.iloc[1]))
                loto_list = [int(x.strip()[-2:]) for x in loto_raw.split() if x.strip().isdigit()]
                if len(loto_list) >= 27:
                    db[ngay_str] = {"date_obj": dt_obj, "prizes_int": loto_list[:27], "raw_str": " ".join([f"{x:02d}" for x in loto_list[:27]])}
            return db, f"Đồng bộ {len(db)} phiên."
        except Exception as e: return db, f"Lỗi: {str(e)}"

    @staticmethod
    def rewrite_clean_db(db):
        all_rows = [{"Ngày": d_str, "Kết Quả Loto": info["raw_str"], "date_parse": info["date_obj"]} for d_str, info in db.items()]
        if not all_rows: return
        df_final = pd.DataFrame(all_rows).sort_values(by='date_parse', ascending=False).drop(columns=['date_parse'])
        df_final.to_excel(Config.DATA_FILE, index=False)

    @staticmethod
    def save_manual_data(date_str, numbers_str):
        res_date = Utils.chuan_hoa_ngay(date_str)
        if not res_date: return "🛑 LỖI NGÀY."
        dt_obj, std_date = res_date
        nums = re.findall(r'\d{2}', str(numbers_str))
        if len(nums) < 27: return f"🛑 Thiếu số ({len(nums)}/27)."
        db, _ = DatabaseManager.load_db()
        db[std_date] = {"date_obj": dt_obj, "prizes_int": [int(x) for x in nums[:27]], "raw_str": " ".join(nums[:27])}
        DatabaseManager.rewrite_clean_db(db)
        return f"✅ THÀNH CÔNG: {std_date}!"

    @staticmethod
    def auto_heal_history():
        db, _ = DatabaseManager.load_db()
        now_vn = Utils.get_vn_time()
        end_dt = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
        if now_vn.hour < 19: end_dt -= timedelta(days=1)
        min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
        if not max_dt or max_dt >= end_dt: return "✅ DB ĐÃ ĐỒNG BỘ TUYỆT ĐỐI."
        
        missing_dates = [max_dt + timedelta(days=x) for x in range(1, (end_dt - max_dt).days + 1)]
        healed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(Crawler.fetch_single_date, dt): dt for dt in missing_dates}
            for future in concurrent.futures.as_completed(futures):
                dt = futures[future]
                res = future.result()
                if res:
                    db[res["Ngày"]] = {"date_obj": dt, "prizes_int": [int(x) for x in res["Kết Quả Loto"].split()], "raw_str": res["Kết Quả Loto"]}
                    healed += 1
        if healed > 0:
            DatabaseManager.rewrite_clean_db(db)
            return f"✅ CÀO THÊM {healed} NGÀY MỚI!"
        return "⚠️ KHÔNG THỂ LẤY DỮ LIỆU MỚI."

    @staticmethod
    def get_boundaries(db):
        now_vn = Utils.get_vn_time()
        today = datetime(now_vn.year, now_vn.month, now_vn.day)
        default_next = today + timedelta(days=1) if now_vn.hour >= 19 else today
        if not db: return None, None, default_next
        all_dates = [info["date_obj"] for info in db.values()]
        return min(all_dates), max(all_dates), max(all_dates) + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 5: QUANT ENGINE (LÕI LOTO V6.5)
# ==============================================================================
class QuantEngine:
    _sig_cache, _mm_cache = {}, {}
    @staticmethod
    def clear_cache(): QuantEngine._sig_cache.clear(); QuantEngine._mm_cache.clear()

    @staticmethod
    def get_signal(target_dt, db):
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates: return None, "[THIẾU DB]"
        target_weekday = target_dt.weekday()
        t_minus_7 = next((p for p in past_dates if p.weekday() == target_weekday and (target_dt - p).days >= 7), None)
        if not t_minus_7: return None, "[THIẾU T-7]"
        
        dan_t7 = set(db[t_minus_7.strftime("%d/%m/%Y")]["prizes_int"])
        kq_t1 = set(db[past_dates[0].strftime("%d/%m/%Y")]["prizes_int"])
        tinh_hoa = {x for x in dan_t7 if x in kq_t1 or ((x % 10)*10 + (x // 10)) in kq_t1}
        so_khuyet = dan_t7 - tinh_hoa
        
        recent_2d_3d = set()
        for p in past_dates[1:3]: recent_2d_3d.update(db[p.strftime("%d/%m/%Y")]["prizes_int"])
        return sorted(list(so_khuyet.intersection(recent_2d_3d))), "OK"

    @staticmethod
    def get_full_prediction(target_dt, db):
        dan_opt, msg = QuantEngine.get_signal(target_dt, db)
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates or not dan_opt: return None, msg

        recent_14 = past_dates[:14]
        freq_14 = {}
        for p in recent_14:
            for num in db[p.strftime("%d/%m/%Y")]["prizes_int"]:
                freq_14[num] = freq_14.get(num, 0) + 1

        final_dan = sorted(dan_opt, key=lambda x: (freq_14.get(x, 0) * 1.5), reverse=True)
        best_btl = final_dan[0] if final_dan else 0
        lon_btl = (best_btl % 10) * 10 + (best_btl // 10)
        stl_pair = (final_dan[1], final_dan[2]) if len(final_dan) >= 3 else (final_dan[1] if len(final_dan)==2 else lon_btl, lon_btl)

        return {
            "btl": f"{best_btl:02d}", "stl": f"{stl_pair[0]:02d} - {stl_pair[1]:02d}",
            "xien2": f"{best_btl:02d} - {stl_pair[0]:02d}", "cang3d": f"1{best_btl:02d}",
            "kep": "00 - 55", "dan_de_10": "01, 02, 03, 04, 05, 06, 07, 08, 09, 10",
            "sorted_dan_scored": final_dan, "sig_trace": f"Lõi V6.5: Bắt {len(final_dan)} mã khuyết."
        }, "OK"

    @staticmethod
    def get_mm_multiplier(target_dt, db):
        return 1.0, "Hệ số vốn chuẩn hóa x1.0"

# ==============================================================================
# 📊 BLOCK 6: AUDIT MANAGER
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = DatabaseManager.auto_heal_history() if auto_crawl else "Offline"
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        return f"Status: {msg}\nCrawl: {crawl_msg}\nNext: {next_predict_dt.strftime('%d/%m/%Y')}", f"#### KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"

    @staticmethod
    def process_manual_input(date_str, num_str):
        save_msg = DatabaseManager.save_manual_data(date_str, num_str)
        report, title = Auditor.phan_he_1_sync(auto_crawl=False)
        return f"{save_msg}\n\n{report}", title

    @staticmethod
    def phan_he_2_predict(pts):
        db, _ = DatabaseManager.load_db()
        _, _, next_dt = DatabaseManager.get_boundaries(db)
        pred_data, _ = QuantEngine.get_full_prediction(next_dt, db)
        if not pred_data: return "Không đủ điều kiện xuất lệnh."
        return f"MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}\nBTL: {pred_data['btl']}\nSTL: {pred_data['stl']}"

    @staticmethod
    def phan_he_3_router(audit_type, date_raw, month_raw, pts): return "Báo cáo kiểm toán"
    @staticmethod
    def phan_he_4_range(t1, t2, pts): return "Báo cáo chu kỳ"
    @staticmethod
    def phan_he_5_raw(ngay_raw): return "Kết quả loto"
    @staticmethod
    def phan_he_6_master_diagnostic_prompt(): return "Báo cáo master"

# ==============================================================================
# ⚖️ BLOCK 7: ARBITRAGE ENGINE
# ==============================================================================
class ArbitrageEngine:
    @staticmethod
    def auto_scan_surebet(): return "Quét Arbitrage tự động"
    @staticmethod
    def calculate_surebet_de(data): return "Tính Surebet"
    @staticmethod
    def calculate_loto_ev(c, p, r): return "Tính EV Loto"

# ==============================================================================
# 📈 BLOCK 8: CHỨNG KHOÁN (7-SENSOR ULTRA QUANT & 3-CORE ANALYTICS)
# ==============================================================================
class StockQuantEngine:
    @staticmethod
    def fetch_stock_data(ticker, days=180):
        # 1. ENTRADE API
        try:
            end_date = Utils.get_vn_time()
            start_date = end_date - timedelta(days=days + 60)
            url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ticker.upper()}&from={int(start_date.timestamp())}&to={int(end_date.timestamp())}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if 't' in data and len(data['t']) >= 30:
                    df = pd.DataFrame({'timestamp': data['t'], 'Open': data['o'], 'High': data['h'], 'Low': data['l'], 'Close': data['c'], 'Volume': data['v']})
                    df['Date'] = (pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)).dt.strftime('%d/%m/%Y')
                    return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna().reset_index(drop=True), "DNSE Open API"
        except Exception: pass

        # 2. YAHOO FINANCE
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}.VN?range=1y&interval=1d"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
            if res.status_code == 200:
                data = res.json()
                if data.get('chart', {}).get('result'):
                    result = data['chart']['result'][0]
                    timestamps = result['timestamp']
                    quote = result['indicators']['quote'][0]
                    df = pd.DataFrame({'timestamp': timestamps, 'Open': quote['open'], 'High': quote['high'], 'Low': quote['low'], 'Close': quote['close'], 'Volume': quote['volume']}).dropna()
                    df['Date'] = (pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)).dt.strftime('%d/%m/%Y')
                    return df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True), "Yahoo Finance Global"
        except Exception: pass
            
        return None, "🛑 LỖI KẾT NỐI API"

    @staticmethod
    def run_ultra_7_sensors(df):
        if len(df) < 30: return None
        
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)

        # 1. SMART MONEY (VOL)
        df['MA20_Vol'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['MA20_Vol']

        # 2. MFI (MONEY FLOW INDEX 14)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        raw_mf = tp * df['Volume']
        pos_mf = np.where(tp > tp.shift(1), raw_mf, 0)
        neg_mf = np.where(tp < tp.shift(1), raw_mf, 0)
        mfi_14 = 100 - (100 / (1 + (pd.Series(pos_mf).rolling(14).sum() / pd.Series(neg_mf).rolling(14).sum().replace(0, np.nan))))
        df['MFI'] = mfi_14

        # 3. Z-SCORE MEAN REVERSION
        df['MA20_Price'] = df['Close'].rolling(20).mean()
        df['Std20_Price'] = df['Close'].rolling(20).std()
        df['Z_Score'] = (df['Close'] - df['MA20_Price']) / df['Std20_Price']

        # 4. RSI 14
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))

        # 5. MACD (12, 26, 9)
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # 6. BOLLINGER BANDS SQUEEZE
        df['BB_Upper'] = df['MA20_Price'] + 2 * df['Std20_Price']
        df['BB_Lower'] = df['MA20_Price'] - 2 * df['Std20_Price']
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['MA20_Price']

        # 7. EMA DYNAMIC TREND & ATR 14
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = tr.rolling(14).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        score = 50.0
        signals = []

        # Đánh giá Đa Cảm Biến
        if latest['Vol_Ratio'] > 2.0 and latest['Close'] > prev['Close']:
            score += 20; signals.append("🟢 Smart Money Nổ Vol")
        elif latest['Vol_Ratio'] > 2.0 and latest['Close'] < prev['Close']:
            score -= 15; signals.append("🔴 Bán Tháo Xả Vol")

        if latest['Z_Score'] < -2.0:
            score += 25; signals.append("🟣 Bắt Đáy Z-Score (< -2.0)")
        elif latest['Z_Score'] > 2.0:
            score -= 20; signals.append("🔴 Quá Mua Z-Score (> +2.0)")

        if latest['MFI'] > 70: signals.append("🟢 Tiền Vào Mạnh (MFI > 70)")
        elif latest['MFI'] < 30: score += 10; signals.append("🟣 Vùng Đáy Tiền Cạn (MFI < 30)")

        if prev['MACD_Hist'] < 0 and latest['MACD_Hist'] > 0:
            score += 15; signals.append("🟢 MACD Giao Cắt Vàng")

        if latest['BB_Width'] < df['BB_Width'].rolling(40).mean().iloc[-1] * 0.8:
            score += 10; signals.append("🟢 Thắt Cổ Chai Bollinger Bands")

        if latest['Close'] > latest['EMA50'] and latest['EMA50'] > latest['EMA200']:
            score += 10; signals.append("🟢 Cấu Trúc Uptrend (EMA50 > EMA200)")

        final_score = min(100, max(0, score))
        
        # LÕI 2: DYNAMIC RISK ENGINE (ATR RISK)
        atr_val = latest['ATR'] if pd.notna(latest['ATR']) else latest['Close'] * 0.03
        entry_price = latest['Close']
        stop_loss = entry_price - (1.5 * atr_val)
        take_profit = entry_price + (3.0 * atr_val)

        # LÕI 3: KELLY CRITERION CAPITAL ALLOCATION
        if final_score >= 80: kelly_alloc = "35% - 40% Tổng NAV (Tỷ Trọng Tối Đa)"
        elif final_score >= 65: kelly_alloc = "20% - 25% Tổng NAV (Tỷ Trọng Trung Bình)"
        elif final_score >= 50: kelly_alloc = "10% - 15% Tổng NAV (Thăm Dò)"
        else: kelly_alloc = "0% (Đứng Ngoài Quản Trị Rủi Ro)"

        return {
            'Date': latest['Date'], 'Close': entry_price, 'Volume': latest['Volume'],
            'Z_Score': latest['Z_Score'], 'Vol_Ratio': latest['Vol_Ratio'],
            'RSI': latest['RSI'], 'MFI': latest['MFI'], 'ATR': atr_val,
            'Score': final_score, 'Signals': " | ".join(signals) if signals else "Tích lũy bình thường",
            'SL': stop_loss, 'TP': take_profit, 'Kelly': kelly_alloc
        }

    @staticmethod
    def run_omni_radar_scanner(raw_ticker_list):
        tickers = [t.strip().upper() for t in raw_ticker_list.replace(',', ' ').split() if t.strip()]
        if not tickers: return "🛑 Nhập ít nhất 1 mã cổ phiếu."

        results = []
        for t in tickers:
            df, src = StockQuantEngine.fetch_stock_data(t, 180)
            if df is not None and len(df) >= 30:
                m = StockQuantEngine.run_ultra_7_sensors(df)
                if m:
                    results.append({
                        'Mã': t, 'Giá': m['Close'], 'Z-Score': m['Z_Score'],
                        'Vol Ratio': m['Vol_Ratio'], 'MFI': m['MFI'], 'RSI': m['RSI'],
                        'Điểm Quant': m['Score'], 'Tín Hiệu': m['Signals'],
                        'SL': m['SL'], 'TP': m['TP'], 'Kelly': m['Kelly']
                    })

        if not results: return "🛑 KHÔNG LẤY ĐƯỢC DỮ LIỆU. Vui lòng kiểm tra lại mã hoặc kết nối."

        res_df = pd.DataFrame(results).sort_values(by='Điểm Quant', ascending=False).reset_index(drop=True)

        lines = [
            "📑 BÁO CÁO SIÊU CẢM BIẾN DÒNG TIỀN QUANT & 3 LÕI PHÂN TÍCH (V6.5 ULTRA)",
            "======================================================================================================",
            f"⏱️ Phiên quét thực hiện vào lúc : {Utils.get_vn_time().strftime('%d/%m/%Y %H:%M:%S')}",
            f"🎯 Tổng số mã đạt tiêu chuẩn : {len(results)} / {len(tickers)} mã",
            "======================================================================================================",
            f"{'TOP':<3} | {'MÃ':<5} | {'GIÁ (k)':<8} | {'Z-SCORE':<8} | {'VOL RATIO':<9} | {'MFI':<5} | {'RSI':<5} | {'ĐIỂM':<5} | TÍN HIỆU CẢM BIẾN KÍCH HOẠT",
            "------------------------------------------------------------------------------------------------------"
        ]

        for idx, r in res_df.iterrows():
            lines.append(
                f"#{idx+1:<2} | {r['Mã']:<5} | {r['Giá']/1000:>8,.1f} | {r['Z-Score']:>+8.2f} | x{r['Vol Ratio']:>7.2f} | {r['MFI']:>5.1f} | {r['RSI']:>5.1f} | {r['Điểm Quant']:>5.0f} | {r['Tín Hiệu']}"
            )

        top1 = res_df.iloc[0]
        lines.extend([
            "======================================================================================================",
            f"🚀 KHUYẾN NGHỊ LỆNH TÁC CHIẾN TỐI ƯU NHẤT: MÃ [{top1['Mã']}] (ĐIỂM QUANT: {top1['Điểm Quant']:.0f}/100)",
            "------------------------------------------------------------------------------------------------------",
            f" • 💵 Vùng Giá Mua Giải Ngân : {top1['Giá']:,.0f} VNĐ",
            f" • 🎯 Mục Tiêu Chốt Lời (TP)  : {top1['TP']:,.0f} VNĐ (+{((top1['TP']-top1['Giá'])/top1['Giá']*100):.1f}%)",
            f" • 🛡️ Cắt Lỗ Tự Động (SL)    : {top1['SL']:,.0f} VNĐ (-{((top1['Giá']-top1['SL'])/top1['Giá']*100):.1f}%)",
            f" • 💰 Phân Bổ Vốn Kelly     : {top1['Kelly']}",
            "======================================================================================================"
        ])

        return "\n".join(lines)

    @staticmethod
    def run_auto_stock_sensors(ticker, days=180):
        df, src = StockQuantEngine.fetch_stock_data(ticker, days)
        if df is None: return "🛑 Lỗi API", gr.update(visible=False)
        m = StockQuantEngine.run_ultra_7_sensors(df)
        if not m: return "🛑 Thất bại", gr.update(visible=False)
        filename = f"Data_Stock_{ticker.upper()}.xlsx"
        df.to_excel(filename, index=False)
        
        report = (
            f"📑 BÁO CÁO CẢM BIẾN QUANT MÃ: {ticker.upper()}\n"
            f"===================================================\n"
            f"📅 Ngày: {m['Date']} | Giá: {m['Close']:,.0f} VNĐ | Vol: {m['Volume']:,.0f}\n"
            f"• Vol Ratio: x{m['Vol_Ratio']:.2f} | Z-Score: {m['Z_Score']:+.2f} | MFI: {m['MFI']:.1f} | RSI: {m['RSI']:.1f}\n"
            f"🏆 ĐIỂM QUANT: {m['Score']:.0f} / 100\n"
            f"---------------------------------------------------\n"
            f"🎯 Target TP : {m['TP']:,.0f} VNĐ\n"
            f"🛡️ Stop Loss : {m['SL']:,.0f} VNĐ\n"
            f"💰 Vốn Kelly : {m['Kelly']}\n"
            f"📌 Tín hiệu : {m['Signals']}"
        )
        return report, gr.update(value=filename, visible=True)

    @staticmethod
    def run_server_database_sensors(ticker):
        t = ticker.strip().upper()
        f = f"Data_Stock_{t}.xlsx"
        if not os.path.exists(f): return f"🛑 Không có file {f}", gr.update(visible=False)
        df = pd.read_excel(f)
        return StockQuantEngine.run_auto_stock_sensors(t, len(df))

# ==============================================================================
# 🎨 UI & APP LAUNCHER
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    min_dt_init, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title=Config.VERSION, theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 MULTI-MARKET QUANT ENGINE {Config.VERSION}")
        nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            btn_1_sync = gr.Button("⚡ KIỂM TOÁN DB", variant="secondary")
            btn_1_crawl = gr.Button("🌐 CẬP NHẬT CRAWLER", variant="primary")
            manual_date = gr.Textbox(label="Ngày (DD/MM/YYYY)")
            manual_numbers = gr.Textbox(label="Chuỗi 27 số")
            btn_manual_save = gr.Button("📥 LƯU TAY", variant="primary")
            out_1 = gr.Textbox(label="Biên bản", lines=8)
            title_2 = gr.Markdown("#### KỲ TỚI")
            btn_prepare_dl = gr.Button("1️⃣ TRÍCH XUẤT FILE")
            dl_output = gr.DownloadButton("2️⃣ TẢI FILE", visible=False)
            btn_prepare_dl.click(fn=lambda: gr.update(value=os.path.abspath(Config.DATA_FILE), visible=True) if os.path.exists(Config.DATA_FILE) else gr.update(visible=False), outputs=dl_output)

        with gr.Column(visible=False) as col_2:
            pts_2 = gr.Number(label="Vốn Cơ sở", value=10)
            btn_2 = gr.Button("🔍 XUẤT LỆNH", variant="primary")
            out_2 = gr.Textbox(label="Lệnh Tác Chiến", lines=20)
            btn_2.click(Auditor.phan_he_2_predict, inputs=[pts_2], outputs=out_2)

        with gr.Column(visible=False) as col_3:
            audit_type = gr.Radio(choices=["Kiểm toán 1 Ngày", "Kiểm toán Cả Tháng"], value="Kiểm toán 1 Ngày")
            date_3 = gr.Textbox(label="Ngày", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            month_3 = gr.Textbox(label="Tháng", value=latest_dt_init.strftime('%m/%Y') if latest_dt_init else "")
            pts_3 = gr.Number(label="Vốn", value=10)
            btn_3 = gr.Button("📡 THỰC THI", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo", lines=20)
            btn_3.click(Auditor.phan_he_3_router, inputs=[audit_type, date_3, month_3, pts_3], outputs=out_3)

        with gr.Column(visible=False) as col_4:
            t1_4 = gr.Textbox(label="Từ ngày")
            t2_4 = gr.Textbox(label="Đến ngày")
            pts_4 = gr.Number(label="Vốn", value=10)
            btn_4 = gr.Button("📈 KIỂM TOÁN", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo", lines=20)
            btn_4.click(Auditor.phan_he_4_range, inputs=[t1_4, t2_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            date_5 = gr.Textbox(label="Ngày")
            btn_5 = gr.Button("💾 TRUY XUẤT", variant="primary")
            out_5 = gr.Textbox(label="Kết quả", lines=15)
            btn_5.click(Auditor.phan_he_5_raw, inputs=date_5, outputs=out_5)

        with gr.Column(visible=False) as col_6:
            btn_6 = gr.Button("🧬 QUÉT TOÀN DB", variant="primary")
            out_6 = gr.Textbox(label="Báo cáo Master", lines=20)
            btn_6.click(Auditor.phan_he_6_master_diagnostic_prompt, outputs=out_6)

        with gr.Column(visible=False) as col_7:
            btn_auto_scan = gr.Button("🌐 QUÉT SUREBET")
            out_arbitrage_auto = gr.Textbox(label="Kết quả", lines=10)
            btn_auto_scan.click(ArbitrageEngine.auto_scan_surebet, outputs=out_arbitrage_auto)

        # [Cột 8] CẢM BIẾN CHỨNG KHOÁN 7-SENSOR ULTRA
        with gr.Column(visible=False) as col_8:
            gr.Markdown("### 🧠 HỆ THỐNG CẢM BIẾN CHỨNG KHOÁN (7-SENSOR ULTRA QUANT RADAR)")
            
            with gr.Tab("🔥 1. Siêu Cảm Biến Quét Đa Mã (Top Điểm Quant + 3 Lõi Phân Tích)"):
                gr.Markdown("**Hướng dẫn:** Nhập danh sách mã cổ phiếu. Kích hoạt 7 Siêu Cảm Biến và 3 Lõi Siêu Phân Tích (Cắt lỗ ATR & Quản trị vốn Kelly).")
                omni_ticker_input = gr.Textbox(
                    label="Danh sách Mã Cổ Phiếu Cần Quét", 
                    value="SSI, HPG, TCB, FPT, DIG, MWG, VND, MBB, HSG, STB, VCI, VHM, NVL, PDR, VCB"
                )
                btn_run_omni_radar = gr.Button("🚀 CHẠY 7 SIÊU CẢM BIẾN QUÉT TOÀN THỊ TRƯỜNG", variant="primary")
                out_omni_report = gr.Textbox(label="Báo Cáo Siêu Phân Tích Quant & Khuyến Nghị Tác Chiến", lines=22)
                
                btn_run_omni_radar.click(
                    StockQuantEngine.run_omni_radar_scanner,
                    inputs=[omni_ticker_input],
                    outputs=[out_omni_report]
                )

            with gr.Tab("2. Đọc Database Server Cố Định (Offline Excel)"):
                stock_ticker_db = gr.Textbox(label="Mã Cổ Phiếu Cần Đọc", value="HPG")
                btn_server_db_stock = gr.Button("📊 ĐỌC DATABASE SERVER", variant="primary")
                out_stock_db_report = gr.Textbox(label="Báo cáo Server DB", lines=15)
                dl_stock_db_file = gr.DownloadButton("📥 TẢI FILE EXCEL", visible=False)
                btn_server_db_stock.click(StockQuantEngine.run_server_database_sensors, inputs=[stock_ticker_db], outputs=[out_stock_db_report, dl_stock_db_file])

            with gr.Tab("3. Cào Live API (Đơn Mã)"):
                stock_ticker_api = gr.Textbox(label="Mã Cổ Phiếu Live", value="SSI")
                days_to_fetch = gr.Slider(minimum=30, maximum=365, value=180, step=10, label="Số ngày cào")
                btn_auto_stock = gr.Button("🚀 CÀO & QUÉT ĐƠN MÃ", variant="primary")
                out_stock_report = gr.Textbox(label="Báo cáo Live API", lines=15)
                dl_stock_file = gr.DownloadButton("📥 TẢI FILE EXCEL", visible=False)
                btn_auto_stock.click(StockQuantEngine.run_auto_stock_sensors, inputs=[stock_ticker_api, days_to_fetch], outputs=[out_stock_report, dl_stock_file])

        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])
        btn_manual_save.click(Auditor.process_manual_input, inputs=[manual_date, manual_numbers], outputs=[out_1, title_2])

        def update_visibility(choice):
            return [gr.Column(visible=(choice == Config.MENU_OPTIONS[i])) for i in range(8)]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8])
        
    return demo

if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
