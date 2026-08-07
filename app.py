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
    VERSION = "V6.3 OMNI QUANT ENGINE (LOCAL SERVER DATABASE INTEGRATED)" 
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    BACKUP_PREFIX = "Ket_Qua_Loto27_Backup_" 
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    BASE_PTS = 10.0
    LOOKBACK_DAYS = 21
    STORM_THRESHOLD = 0.35
    
    ACTIVE_MODE = "🤖 [VERSION 6.3] V6.3 OMNI TIERED QUANT (LOTO + STOCKS SERVER DB)"
    
    MENU_OPTIONS = [
        "🔄 1. ĐỒNG BỘ & CẬP NHẬT DỮ LIỆU LOTO",
        "🎯 2. KHUYẾN NGHỊ LỆNH GIAO DỊCH",
        "🔍 3. KIỂM TOÁN CHUYÊN SÂU",
        "📈 4. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 5. BẢNG KẾT QUẢ LOTO TRUYỀN THỐNG",
        "🤖 6. BỘ NÃO AI (QUÉT LỊCH SỬ DB)",
        "⚖️ 7. HỆ THỐNG RADAR ARBITRAGE (TỶ LỆ)",
        "📈 8. CẢM BIẾN DÒNG TIỀN CHỨNG KHOÁN (OFFLINE & API)"
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
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    @staticmethod
    def fetch_single_date(target_date):
        if not HAS_REQUESTS: return None
        date_str_url = target_date.strftime("%d-%m-%Y")
        date_str_db = target_date.strftime("%d/%m/%Y")
        
        numeric_domains = [f"ketqua{i}.net" for i in range(16, 51)] + [f"ketqua{i}.net" for i in range(1, 16)]
        
        urls = []
        for dom in numeric_domains:
            urls.append(f"https://{dom}/xo-so-truyen-thong.php?ngay={date_str_url}")
            urls.append(f"https://{dom}/xsmb-ngay-{date_str_url}.html")
        urls.append(f"https://ketqua.net/ngay-{date_str_url}")
        urls.append(f"https://ketquaxoso.net/ket-qua-xo-so-mien-bac-ngay-{date_str_url}")
        
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
            except Exception:
                pass
        return None

# ==============================================================================
# 📊 BLOCK 4: DATABASE MANAGER (TỰ ĐỘNG CHUẨN HÓA & BACKUP NGẦM)
# ==============================================================================
class GoogleSheetsManager:
    @staticmethod
    def get_worksheet():
        if not HAS_GSPREAD:
            return None, "Thiếu thư viện 'gspread' hoặc 'google-auth'."
            
        sheet_name = os.environ.get("GOOGLE_SHEET_NAME", "Ket_Qua_Loto27").strip()
        sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
        creds_json_str = os.environ.get("GOOGLE_CREDENTIALS", "").strip() or os.environ.get("GOOGLE_SHEETS_JSON", "").strip()
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = None
        if creds_json_str:
            try:
                creds_dict = json.loads(creds_json_str)
                creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            except Exception:
                pass
                
        if not creds:
            for fname in ["google_credentials.json", "credentials.json", "service_account.json"]:
                if os.path.exists(fname):
                    try:
                        creds = Credentials.from_service_account_file(fname, scopes=scopes)
                        break
                    except Exception:
                        pass
                        
        if not creds:
            return None, "Chưa cấu hình Google Credentials."
            
        try:
            gc = gspread.authorize(creds)
            if sheet_id:
                ws = gc.open_by_key(sheet_id).sheet1
            else:
                ws = gc.open(sheet_name).sheet1
            return ws, "OK"
        except Exception as e:
            return None, f"Lỗi kết nối Google Sheets: {str(e)}"

class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        ws_msg = "Chạy Local Excel - Cấu trúc chuẩn hóa"
        if not os.path.exists(Config.DATA_FILE):
            backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
            if backups: shutil.copy(backups[0], Config.DATA_FILE)
            else:
                pd.DataFrame(columns=["Ngày", "Kết Quả Loto"]).to_excel(Config.DATA_FILE, index=False)
                return db, f"⚠️ Tệp dữ liệu rỗng. ({ws_msg})"
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str)
            needs_rewrite = False
            for _, row in df.iterrows():
                res_date = Utils.chuan_hoa_ngay(row.iloc[0])
                if not res_date: continue
                dt_obj, ngay_str = res_date
                
                loto_raw = re.sub(r"[^\d\s]", " ", str(row.iloc[1]))
                loto_list = [int(x.strip()[-2:]) for x in loto_raw.split() if x.strip().isdigit()]
                
                if len(loto_list) >= 27:
                    clean_str = " ".join([f"{x:02d}" for x in loto_list[:27]])
                    db[ngay_str] = {"date_obj": dt_obj, "prizes_int": loto_list[:27], "raw_str": clean_str}
                    
                    if str(row.iloc[0]) != ngay_str or str(row.iloc[1]) != clean_str:
                        needs_rewrite = True
                        
            if needs_rewrite:
                DatabaseManager.rewrite_clean_db(db)
                return db, f"🟢 TỰ ĐỘNG DỌN DẸP DB: Đã chuẩn hóa định dạng ngày & số."
            return db, f"🟢 LOCAL EXCEL: Đồng bộ {len(db)} phiên."
        except Exception as e: 
            backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
            if backups:
                shutil.copy(backups[0], Config.DATA_FILE)
                return DatabaseManager.load_db() 
            return db, f"🛑 LỖI ĐỌC:\n{traceback.format_exc()}"

    @staticmethod
    def _push_to_google_sheets(df_final):
        try:
            ws, msg = GoogleSheetsManager.get_worksheet()
            if ws is not None:
                matrix = [["Ngày", "Kết Quả Loto"]]
                for _, row in df_final.iterrows():
                    matrix.append([str(row["Ngày"]), str(row["Kết Quả Loto"])])
                ws.clear()
                try:
                    ws.update(values=matrix, range_name="A1")
                except TypeError:
                    ws.update("A1", matrix)
        except Exception:
            pass

    @staticmethod
    def rewrite_clean_db(db):
        all_rows = []
        for d_str, info in db.items():
            all_rows.append({"Ngày": d_str, "Kết Quả Loto": info["raw_str"], "date_parse": info["date_obj"]})
        if not all_rows: return

        df_final = pd.DataFrame(all_rows)
        df_final = df_final.sort_values(by='date_parse', ascending=False).drop(columns=['date_parse'])
        
        if os.path.exists(Config.DATA_FILE):
            timestamp = Utils.get_vn_time().strftime("%Y%m%d_%H%M%S")
            shutil.copy(Config.DATA_FILE, f"{Config.BACKUP_PREFIX}{timestamp}.bak")
            existing_backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
            for old_bak in existing_backups[3:]: 
                try: os.remove(old_bak)
                except Exception: pass
        df_final.to_excel(Config.DATA_FILE, index=False)

        thread = threading.Thread(target=DatabaseManager._push_to_google_sheets, args=(df_final,))
        thread.daemon = True
        thread.start()

    @staticmethod
    def save_manual_data(date_str, numbers_str):
        res_date = Utils.chuan_hoa_ngay(date_str)
        if not res_date: return "🛑 LỖI NHẬP LIỆU: Ngày không đúng định dạng (DD/MM/YYYY)."
        dt_obj, std_date = res_date
        nums = re.findall(r'\d{2}', str(numbers_str))
        if len(nums) < 27: return f"🛑 LỖI NHẬP LIỆU: Chỉ tìm thấy {len(nums)}/27 con số."
        try:
            db, _ = DatabaseManager.load_db()
            db[std_date] = {"date_obj": dt_obj, "prizes_int": [int(x) for x in nums[:27]], "raw_str": " ".join(nums[:27])}
            DatabaseManager.rewrite_clean_db(db)
            QuantEngine.clear_cache()
            return f"✅ NHẬP TAY THÀNH CÔNG (Đã lưu File & Kích hoạt đồng bộ ngầm): {std_date}!"
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def auto_heal_history():
        db, _ = DatabaseManager.load_db()
        now_vn = Utils.get_vn_time()
        
        end_dt = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
        if now_vn.hour < 19:
            end_dt -= timedelta(days=1)
            
        min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
        if not max_dt:
            return "🛑 LỖI: Database rỗng. Hãy nạp file Excel trước."
            
        if max_dt >= end_dt:
            return f"✅ Dữ liệu đã đồng bộ tuyệt đối đến {max_dt.strftime('%d/%m/%Y')}."
            
        missing_dates = [max_dt + timedelta(days=x) for x in range(1, (end_dt - max_dt).days + 1)]
        healed_count = 0
        msg_log = []
        
        if not HAS_REQUESTS:
            return "🛑 CẢNH BÁO: Thiếu thư viện 'requests', không thể cào dữ liệu."

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(Crawler.fetch_single_date, dt): dt for dt in missing_dates}
            for future in concurrent.futures.as_completed(futures):
                dt = futures[future]
                try:
                    res = future.result()
                    if res:
                        std_str = res["Ngày"]
                        nums_str = res["Kết Quả Loto"]
                        nums = [int(x) for x in nums_str.split()]
                        db[std_str] = {"date_obj": dt, "prizes_int": nums, "raw_str": nums_str}
                        healed_count += 1
                    else:
                        msg_log.append(f"Khuyết {dt.strftime('%d/%m')}")
                except Exception as e:
                    msg_log.append(f"Lỗi {dt.strftime('%d/%m')}")
                    
        if healed_count > 0:
            try:
                DatabaseManager.rewrite_clean_db(db)
                QuantEngine.clear_cache()
                return f"✅ THÀNH CÔNG: Đã cào thêm {healed_count} ngày mới (Từ {missing_dates[0].strftime('%d/%m')} đến {end_dt.strftime('%d/%m/%Y')})!"
            except Exception as e:
                return f"🛑 LỖI GHI FILE:\n{traceback.format_exc()}"
                
        err_str = ", ".join(msg_log[:5])
        return f"⚠️ KHÔNG THỂ LẤY DỮ LIỆU. Web xổ số bị nghẽn hoặc kết quả chưa ra. ({err_str}...)"

    @staticmethod
    def get_boundaries(db):
        now_vn = Utils.get_vn_time()
        today = datetime(now_vn.year, now_vn.month, now_vn.day)
        default_next = today + timedelta(days=1) if now_vn.hour >= 19 else today
        if not db: return None, None, default_next
        all_dates = [info["date_obj"] for info in db.values()]
        return min(all_dates), max(all_dates), max(all_dates) + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 5: QUANT ENGINE (LÕI LOTO V6.3)
# ==============================================================================
class QuantEngine:
    _sig_cache = {}
    _mm_cache = {}

    @staticmethod
    def clear_cache():
        QuantEngine._sig_cache.clear()
        QuantEngine._mm_cache.clear()

    @staticmethod
    def get_signal(target_dt, db):
        cache_key = (target_dt, "V6.3_SIGNAL")
        if cache_key in QuantEngine._sig_cache:
            return QuantEngine._sig_cache[cache_key]

        trace_log = []
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates: 
            res = (None, "[THIẾU DỮ LIỆU]")
            QuantEngine._sig_cache[cache_key] = res
            return res

        target_weekday = target_dt.weekday()
        t_minus_7_dt = None
        for p_dt in past_dates:
            if p_dt.weekday() == target_weekday and (target_dt - p_dt).days >= 7:
                t_minus_7_dt = p_dt
                break
                
        if t_minus_7_dt is None: 
            res = (None, "[THIẾU DỮ LIỆU T-7 ĐỒNG PHA]")
            QuantEngine._sig_cache[cache_key] = res
            return res
        
        str_t7 = t_minus_7_dt.strftime("%d/%m/%Y")
        prizes_t7 = db[str_t7]["prizes_int"]
        dan_t7 = set(prizes_t7)

        str_t1 = past_dates[0].strftime("%d/%m/%Y")
        kq_t1 = set(db[str_t1]["prizes_int"])
        tinh_hoa = set()
        for x in dan_t7:
            lon = (x % 10) * 10 + (x // 10)
            if x in kq_t1 or lon in kq_t1: tinh_hoa.add(x)
        so_khuyet_goc = set(dan_t7) - tinh_hoa

        recent_2d_3d = set()
        if len(past_dates) >= 3:
            for p_dt in past_dates[1:3]: 
                str_p = p_dt.strftime("%d/%m/%Y")
                recent_2d_3d.update(db[str_p]["prizes_int"])
        dan_opt = [x for x in so_khuyet_goc if x in recent_2d_3d]
        
        res = (sorted(list(dan_opt)), "OK")
        QuantEngine._sig_cache[cache_key] = res
        return res

    @staticmethod
    def get_full_prediction(target_dt, db):
        dan_opt, msg = QuantEngine.get_signal(target_dt, db)
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        
        if not past_dates or dan_opt is None:
            return None, f"{msg}\n👉 Truy vết: Không đủ điều kiện tạo dàn khuyết."

        recent_14 = past_dates[:14]
        freq_14 = {}
        hundreds_freq = {i: 0 for i in range(10)}
        
        for p_dt in recent_14:
            p_str = p_dt.strftime("%d/%m/%Y")
            prizes = db[p_str]["prizes_int"]
            raw_tokens = db[p_str]["raw_str"].split()
            
            for num in prizes:
                freq_14[num] = freq_14.get(num, 0) + 1
            
            for token in raw_tokens:
                if len(token) >= 3:
                    h_digit = int(token[-3])
                    hundreds_freq[h_digit] += 1

        prizes_t7 = set(db[past_dates[6].strftime("%d/%m/%Y")]["prizes_int"]) if len(past_dates) >= 7 else set()
        
        scored_candidates = sorted(
            dan_opt, 
            key=lambda x: (freq_14.get(x, 0) * 1.5 + (2.0 if x in prizes_t7 else 0.0), x), 
            reverse=True
        )
        
        final_dan = list(scored_candidates)
        best_btl = final_dan[0] if len(final_dan) > 0 else 0

        lon_btl = (best_btl % 10) * 10 + (best_btl // 10)
        if len(final_dan) >= 3:
            stl_pair = (final_dan[1], final_dan[2])
        elif len(final_dan) == 2:
            stl_pair = (final_dan[1], lon_btl if lon_btl != best_btl and lon_btl != final_dan[1] else (best_btl + 11) % 100)
        else:
            stl_pair = (lon_btl if lon_btl != best_btl else (best_btl + 11) % 100, (best_btl + 22) % 100)

        sec1 = stl_pair[0]
        sec2 = stl_pair[1]
        xien2_pair1 = f"{best_btl:02d} - {sec1:02d}"
        xien2_pair2 = f"{best_btl:02d} - {sec2:02d}"
        loto_xien2 = f"{xien2_pair1} | {xien2_pair2}"

        top_hundreds = sorted(hundreds_freq.keys(), key=lambda h: -hundreds_freq[h])[:2]
        h1 = top_hundreds[0] if len(top_hundreds) > 0 else 0
        h2 = top_hundreds[1] if len(top_hundreds) > 1 else 1
        loto_3cang = f"{h1}{best_btl:02d} - {h2}{stl_pair[0]:02d}"

        keps = [0, 11, 22, 33, 44, 55, 66, 77, 88, 99]
        sorted_keps = sorted(keps, key=lambda k: (- (1 if k in final_dan else 0), -freq_14.get(k, 0)))
        lo_kep = f"{sorted_keps[0]:02d} - {sorted_keps[1]:02d}"

        str_t1 = past_dates[0].strftime("%d/%m/%Y")
        gdb_t1 = db[str_t1]["prizes_int"][0]
        de_head, de_tail = gdb_t1 // 10, gdb_t1 % 10
        de_set = set([best_btl, lon_btl, stl_pair[0], stl_pair[1]])
        for i in range(10):
            de_set.add(de_head * 10 + i)
            de_set.add(i * 10 + de_tail)
            if len(de_set) >= 10: break
        sorted_de = sorted(sorted(list(de_set), key=lambda x: (- (1 if x in final_dan else 0), -freq_14.get(x, 0)))[:10])
        dan_de_10 = ", ".join([f"{x:02d}" for x in sorted_de])

        return {
            "btl": f"{best_btl:02d}",
            "stl": f"{stl_pair[0]:02d} - {stl_pair[1]:02d}",
            "xien2": loto_xien2,
            "cang3d": loto_3cang,
            "kep": lo_kep,
            "dan_de_10": dan_de_10,
            "sorted_dan_scored": final_dan,
            "sig_trace": f"[Lõi V6.3] Bắt được {len(final_dan)} mã khuyết. Xếp hạng BTL, STL thành công."
        }, "OK"

    @staticmethod
    def _get_monthly_stats_base(year, month, target_dt, db):
        cost, pnl = 0.0, 0.0
        w_mtd, l_mtd = 0, 0
        all_dts = sorted([info["date_obj"] for info in db.values() if info["date_obj"].year == year and info["date_obj"].month == month and info["date_obj"] < target_dt])
        for dt in all_dts:
            str_dt = dt.strftime("%d/%m/%Y")
            dan, _ = QuantEngine.get_signal(dt, db)
            if dan:
                sl = len(dan)
                nhay = sum(db[str_dt]["prizes_int"].count(x) for x in dan)
                c = sl * Config.BASE_PTS * Config.COST_PER_POINT
                r = nhay * Config.BASE_PTS * Config.WIN_PER_NHAY
                cost += c
                p = r - c
                pnl += p
                if p > 0: w_mtd += 1
                else: l_mtd += 1
        roi = (pnl / cost) if cost > 0 else 0.0
        return cost, pnl, roi, w_mtd, l_mtd

    @staticmethod
    def _get_ytd_stats_base(year, target_dt, db):
        cost, pnl = 0.0, 0.0
        all_dts = sorted([info["date_obj"] for info in db.values() if info["date_obj"].year == year and info["date_obj"] < target_dt])
        for dt in all_dts:
            str_dt = dt.strftime("%d/%m/%Y")
            dan, _ = QuantEngine.get_signal(dt, db)
            if dan:
                sl = len(dan)
                nhay = sum(db[str_dt]["prizes_int"].count(x) for x in dan)
                c = sl * Config.BASE_PTS * Config.COST_PER_POINT
                r = nhay * Config.BASE_PTS * Config.WIN_PER_NHAY
                cost += c
                pnl += (r - c)
        roi = (pnl / cost) if cost > 0 else 0.0
        return cost, pnl, roi

    @staticmethod
    def _get_rolling_stats_base(days, target_dt, db):
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)[:days]
        cost, pnl = 0.0, 0.0
        for dt in past_dates:
            str_dt = dt.strftime("%d/%m/%Y")
            dan, _ = QuantEngine.get_signal(dt, db)
            if dan:
                sl = len(dan)
                nhay = sum(db[str_dt]["prizes_int"].count(x) for x in dan)
                c = sl * Config.BASE_PTS * Config.COST_PER_POINT
                r = nhay * Config.BASE_PTS * Config.WIN_PER_NHAY
                cost += c
                pnl += (r - c)
        roi = (pnl / cost) if cost > 0 else 0.0
        return cost, pnl, roi

    @staticmethod
    def get_mm_multiplier(target_dt, db):
        cache_key = (target_dt, "V6.3_MM")
        if cache_key in QuantEngine._mm_cache:
            return QuantEngine._mm_cache[cache_key]
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates: 
            res = (1.0, "Không có dữ liệu lịch sử.")
            QuantEngine._mm_cache[cache_key] = res
            return res

        trace_log = []
        streak = 0
        for curr_dt in past_dates[:40]: 
            str_curr = curr_dt.strftime("%d/%m/%Y")
            dan, _ = QuantEngine.get_signal(curr_dt, db)
            if dan is not None and len(dan) > 0:
                nhay = sum(db[str_curr]["prizes_int"].count(x) for x in dan)
                cost = len(dan) * Config.BASE_PTS * Config.COST_PER_POINT
                rev = nhay * Config.BASE_PTS * Config.WIN_PER_NHAY
                if rev - cost > 0:
                    trace_log.append(f"[Streak Log] Cắt chuỗi tại ngày WIN ({str_curr}).")
                    break 
                else:
                    streak += 1
                    trace_log.append(f"[Streak Log] Ngày {str_curr} THUA -> Chuỗi = {streak}.")
                    if streak >= 4:
                        trace_log.append("[Streak Log] Đạt Max chuỗi thua 4. Kích hoạt Cắt Lỗ tuyệt đối.")
                        break 

        cur_m, cur_y = target_dt.month, target_dt.year
        cost_mtd, pnl_mtd, roi_mtd, w_mtd, l_mtd = QuantEngine._get_monthly_stats_base(cur_y, cur_m, target_dt, db)
        cost_ytd, pnl_ytd, roi_ytd = QuantEngine._get_ytd_stats_base(cur_y, target_dt, db)
        cost_7d, pnl_7d, roi_7d = QuantEngine._get_rolling_stats_base(7, target_dt, db)

        recent_14 = past_dates[:14]
        tot_nhay_14, tot_codes_14 = 0, 0
        daily_pnls_14 = []
        for r_dt in recent_14:
            r_dan, _ = QuantEngine.get_signal(r_dt, db)
            if r_dan and len(r_dan) > 0:
                r_str = r_dt.strftime("%d/%m/%Y")
                tot_codes_14 += len(r_dan)
                nhay_r = sum(db[r_str]["prizes_int"].count(x) for x in r_dan)
                tot_nhay_14 += nhay_r
                pnl_r = nhay_r * Config.BASE_PTS * Config.WIN_PER_NHAY - len(r_dan) * Config.BASE_PTS * Config.COST_PER_POINT
                daily_pnls_14.append(pnl_r)
        p_hit_14d = (tot_nhay_14 / tot_codes_14) if tot_codes_14 > 0 else 0.27

        recent_21 = past_dates[:21]
        wins_21, played_21 = 0, 0
        for r_dt in recent_21:
            r_str = r_dt.strftime("%d/%m/%Y")
            r_dan, _ = QuantEngine.get_signal(r_dt, db)
            if r_dan and len(r_dan) > 0:
                played_21 += 1
                nhay = sum(db[r_str]["prizes_int"].count(x) for x in r_dan)
                if (nhay * Config.WIN_PER_NHAY - len(r_dan) * Config.COST_PER_POINT) > 0: wins_21 += 1
        wr_21d = (wins_21 / played_21) if played_21 > 0 else 1.0

        is_storm_v1 = (played_21 >= 10 and wr_21d < Config.STORM_THRESHOLD)
        if is_storm_v1:
            v1_base = 1.0 if streak == 0 else (0.3 if streak == 1 else 0.0)
        else:
            v1_base = 1.0 if streak == 0 else (0.5 if streak == 1 else (0.2 if streak == 2 else 0.0))

        c_pnl = 0.0
        p_eq = 0.0
        all_ytd = sorted([info["date_obj"] for info in db.values() if info["date_obj"].year == cur_y and info["date_obj"] < target_dt])
        for p_dt in all_ytd:
            p_dan, _ = QuantEngine.get_signal(p_dt, db)
            if p_dan:
                p_str = p_dt.strftime("%d/%m/%Y")
                nhay_p = sum(db[p_str]["prizes_int"].count(x) for x in p_dan)
                c_pnl += nhay_p * Config.BASE_PTS * Config.WIN_PER_NHAY - len(p_dan) * Config.BASE_PTS * Config.COST_PER_POINT
                if c_pnl > p_eq: p_eq = c_pnl
        drawdown_from_peak = p_eq - c_pnl

        st_roi_sign = "🟢 DƯƠNG" if roi_7d > 0 else "🔴 ÂM"
        mt_roi_sign = "🟢 DƯƠNG" if roi_mtd > 0 else "🔴 ÂM"
        lt_roi_sign = "🟢 DƯƠNG" if roi_ytd > 0 else "🔴 ÂM"

        trace_log.append(f"[QUAN SÁT CẢM BIẾN] WR_21d: {wr_21d*100:.1f}% | P_Hit(14d): {p_hit_14d:.2f} | Streak: {streak}")
        trace_log.append(f" • 📈 ROI Ngắn (7d): {roi_7d*100:+.2f}% ({st_roi_sign}) | 📅 MTD: {roi_mtd*100:+.2f}% ({mt_roi_sign}) | 🗓️ YTD: {roi_ytd*100:+.2f}% ({lt_roi_sign})")
        trace_log.append(f" • 🏔️ Đỉnh Tài Sản (Peak): {p_eq/1e6:,.1f}M | Sub_Drawdown từ Đỉnh: {drawdown_from_peak/1e6:,.1f}M")

        recent_pnls_15 = daily_pnls_14[-15:] if len(daily_pnls_14) >= 10 else []
        if len(recent_pnls_15) >= 10:
            x_a = np.arange(len(recent_pnls_15))
            cum_p = np.cumsum(recent_pnls_15)
            slope_val, _ = np.polyfit(x_a, cum_p, 1)
        else:
            slope_val = 0.0

        slope_scale = 1.0 + 0.10 * np.tanh(slope_val / 300000.0)
        vol_14d = np.std(daily_pnls_14) if len(daily_pnls_14) >= 10 else 1200000.0
        vol_scale = 0.88 if vol_14d > 2200000 else (1.08 if (vol_14d < 1100000 and pnl_mtd > 0) else 1.00)

        is_cppi_active = (p_eq >= 15000000 and drawdown_from_peak >= 5000000 and streak >= 1)
        cppi_scale = 0.60 if is_cppi_active else 1.00

        x_diff = l_mtd - w_mtd
        sigmoid_macro = 0.50 + 1.00 / (1.0 + np.exp(-0.30 * x_diff))

        if streak >= 3 or v1_base == 0.0:
            mult = 0.0
            active_ver = "CIRCUIT BREAKER CẮT LỖ (0.00x)"
        else:
            mult = v1_base * sigmoid_macro * slope_scale * vol_scale * cppi_scale
            active_ver = f"RISK-PARITY TIERED (Sigmoid={sigmoid_macro:.2f} | Slope_scale={slope_scale:.2f})"

        trace_log.append(f"🤖 [V6.3 ROBUST TIERED] Chế độ: {active_ver}")
        trace_log.append(f"[MM Result] Hệ số vốn cơ sở chuẩn hóa = x{mult:.2f}")
        res = (mult, "\n".join(trace_log))
        QuantEngine._mm_cache[cache_key] = res
        return res

# ==============================================================================
# 📊 BLOCK 6: AUDIT & REPORTING MANAGER
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = "ℹ️ Chế độ Offline. Bấm nút cập nhật để kích hoạt Radar."
        if auto_crawl: crawl_msg = DatabaseManager.auto_heal_history()
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        latest_str = latest_dt.strftime('%d/%m/%Y') if latest_dt else "⚠️ CHƯA CÓ DỮ LIỆU!"
        lines = [
            "📑 BÁO CÁO ĐỒNG BỘ CƠ SỞ DỮ LIỆU TOÀN MẠNG",
            "=================================================================================",
            f"• Phiên bản hệ thống : {Config.VERSION}",
            f"• Trạng thái Dữ liệu : {msg}",
            f"• Báo cáo Crawler    : {crawl_msg}",
            "---------------------------------------------------------------------------------",
            f"• Dữ liệu cập nhật đến ngày : 📅 [{latest_str}]",
            f"• Sẵn sàng tính toán cho kỳ : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
        ]
        return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"

    @staticmethod
    def process_manual_input(date_str, num_str):
        save_msg = DatabaseManager.save_manual_data(date_str, num_str)
        report, title = Auditor.phan_he_1_sync(auto_crawl=False)
        return f"{save_msg}\n\n{report}", title

    @staticmethod
    def phan_he_2_predict(pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            _, _, next_dt = DatabaseManager.get_boundaries(db)
            is_valid, err_msg = Utils.check_valid_number(pts_per_code_base, "Vốn Cơ sở")
            if not is_valid: return err_msg
            base_pts = float(pts_per_code_base)
            multiplier, mm_trace = QuantEngine.get_mm_multiplier(next_dt, db)
            
            pred_data, status = QuantEngine.get_full_prediction(next_dt, db)
            if pred_data is None:
                return f"🛑 CẢNH BÁO: Lỗi trích xuất tín hiệu.\n👉 TRUY VẾT LỖI:\n{status}\n{mm_trace}"

            sorted_dan = pred_data["sorted_dan_scored"]
            so_luong_lo = len(sorted_dan)

            if so_luong_lo == 0:
                return f"📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN: 👉 🚫 [ĐỨNG NGOÀI]\n-------------------------------------------------------\n💡 KHÔNG CÓ TÍN HIỆU SỐ KHUYẾT HỢP LỆ TRONG KỲ NÀY."

            dan_goc_str = " ".join([f"{x:02d}" for x in sorted(sorted_dan)])

            dan_alloc_lines = []
            total_von = 0.0
            allocated_items = []

            for idx_code, code_val in enumerate(sorted_dan):
                k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                tag = "BẠCH THỦ (1.30x)" if idx_code == 0 else ("SONG THỦ (1.15x)" if idx_code in [1, 2] else "Lót dàn (0.85x)")
                
                pts_this = int(round(base_pts * multiplier * k_tier))
                cost_this = pts_this * Config.COST_PER_POINT
                total_von += cost_this
                allocated_items.append((code_val, tag, pts_this, cost_this))
                dan_alloc_lines.append(f"   + Mã [{code_val:02d}] ({tag:<16}) : {pts_this:>3} điểm | Vốn: {cost_this:,.0f} VND")

            alloc_detail_str = "\n".join(dan_alloc_lines)

            pts_needed = math.ceil(total_von / Config.WIN_PER_NHAY) if total_von > 0 else 0
            
            if allocated_items and pts_needed > 0:
                low_p = allocated_items[-1][2]
                nhay_low_needed = math.ceil(pts_needed / low_p) if low_p > 0 else 0
                btl_p = allocated_items[0][2]
                rem_p = max(0, pts_needed - btl_p)
                
                breakeven_explanation = (
                    f"💡 MỤC TIÊU HÒA VỐN       : Cần tổng tối thiểu {pts_needed} ĐIỂM LÔ nổ (Thu về >= {pts_needed * Config.WIN_PER_NHAY:,.0f} VND)\n"
                    f"   👉 Ví dụ thực tế có LÃI : Chỉ cần {nhay_low_needed} nháy Lót ({low_p}đ/nháy), "
                    f"hoặc 1 nháy BTL ({btl_p}đ) + {rem_p}đ nổ bổ sung là LÃI ngay."
                )
            else:
                breakeven_explanation = "💡 MỤC TIÊU HÒA VỐN       : Lệnh cắt lỗ đứng ngoài (0 điểm)."

            lines = [
                "📑 BÁO CÁO KHUYẾN NGHỊ GIAO DỊCH QUANT CAO CẤP",
                "=======================================================",
                f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}",
                f"🎚️ CHIẾN LƯỢC ĐỘC TÔN  : {Config.ACTIVE_MODE}",
                f"📋 DÀN SỐ GỐC TỪ LÕI V6.3: [ {dan_goc_str} ] (Đã tìm thấy đúng {so_luong_lo} mã)",
                "=======================================================",
                "📊 HỒ SƠ CHỐT SỐ THƯỞNG KÊ (DỰ BÁO KQXS CAO CẤP)",
                "-------------------------------------------------------",
                f"{'Danh Mục':<22} | Con Số Thưởng Kê",
                "-------------------------------------------------------",
                f"{'Bạch Thủ Lô':<22} | {pred_data['btl']}",
                f"{'Song Thủ Lô':<22} | {pred_data['stl']}",
                f"{'Lô Xiên 2':<22} | {pred_data['xien2']}",
                f"{'Lô 3 Càng (3 Số)':<22} | {pred_data['cang3d']}",
                f"{'Lô Kép Bằng':<22} | {pred_data['kep']}",
                f"{'Dàn Đề 10 Số':<22} | {pred_data['dan_de_10']}",
                "-------------------------------------------------------",
                f"💰 QUẢN TRỊ VỐN & CHI TIẾT PHÂN BỔ BẬC THANG ({so_luong_lo} MÃ):",
                alloc_detail_str,
                "-------------------------------------------------------",
                f"💰 TỔNG VỐN DỒN TIERED   : {total_von:,.0f} VNĐ",
                breakeven_explanation,
                "\n--- BẢN GHI TRUY VẾT TOÁN HỌC (TRACE LOG) ---",
                pred_data['sig_trace'],
                mm_trace
            ]

            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_router(audit_type, date_raw, month_raw, pts_per_code_base):
        if audit_type == "Kiểm toán 1 Ngày": 
            return Auditor.phan_he_3_single(date_raw, pts_per_code_base)
        else: 
            return Auditor.phan_he_3_monthly_detail(month_raw, pts_per_code_base)

    @staticmethod
    def phan_he_3_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            if ngay_str not in db: return f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên {ngay_str} chưa cập nhật."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            
            lines = [
                "📑 BÁO CÁO KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN",
                "========================================================================",
                f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str}",
                "========================================================================"
            ]
            
            pred_data, msg = QuantEngine.get_full_prediction(d_obj, db)
            mode_name = Config.ACTIVE_MODE.split(']')[1].strip()
            if pred_data is None: 
                lines.extend([f"🛑 [{mode_name}]: Thiếu dữ liệu", f"   > Lý do truy vết: {msg}"])
            else: 
                mult, mm_trace = QuantEngine.get_mm_multiplier(d_obj, db)
                sorted_dan = pred_data["sorted_dan_scored"]
                sl = len(sorted_dan)
                if sl == 0:
                    lines.append(f"🛑 [{mode_name}] 👉 KHÔNG CÓ MÃ ĐẠT CHUẨN (ĐỨNG NGOÀI)")
                else:
                    prizes_today = db[ngay_str]["prizes_int"]
                    day_cost = 0.0
                    day_rev = 0.0
                    
                    hit_details = []
                    for idx_code, code_val in enumerate(sorted_dan):
                        k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                        pts_code = int(round(float(pts_per_code_base) * mult * k_tier))
                        if pts_code > 0:
                            c_code = pts_code * Config.COST_PER_POINT
                            nhay_code = prizes_today.count(code_val)
                            r_code = nhay_code * pts_code * Config.WIN_PER_NHAY
                            day_cost += c_code
                            day_rev += r_code
                            if nhay_code > 0:
                                hit_details.append(f"[{code_val:02d}] nổ {nhay_code} nháy x {pts_code}đ = +{r_code:,.0f} đ")
                            
                    lai = day_rev - day_cost
                    st = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                    lines.extend([
                        f"📌 [{mode_name}]",
                        f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in sorted_dan]),
                        f" • Chi tiết trúng: " + (", ".join(hit_details) if hit_details else "🚫 Không trúng mã nào"),
                        f" • Tổng vốn dồn: {day_cost/1000:,.0f}k | Thu thưởng: {day_rev/1000:,.0f}k",
                        f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})\n"
                    ])
                lines.extend(["   --- LOG TRUY VẾT CẢM BIẾN & ĐI VỐN ---", "   " + pred_data['sig_trace'].replace("\n", "\n   "), "   " + mm_trace.replace("\n", "\n   ")])
            lines.append("------------------------------------------------------------------------")
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_monthly_detail(month_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            m = re.match(r'^(\d{1,2})[-/.](\d{4})$', str(month_raw).strip())
            if not m: return "🛑 LỖI ĐỊNH DẠNG: Vui lòng nhập tháng dạng MM/YYYY."
            thang, nam = int(m.group(1)), int(m.group(2))
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = float(pts_per_code_base)
            start_dt = datetime(nam, thang, 1)
            max_day = calendar.monthrange(nam, thang)[1]
            end_dt = datetime(nam, thang, max_day)
            
            lines = [
                f"📑 BÁO CÁO CHI TIẾT TỪNG NGÀY: THÁNG {thang:02d}/{nam}",
                f"🎚️ LÕI ĐỘC TÔN: V6.3 ROBUST TIERED",
                "=============================================================================================================================",
                f"{'NGÀY':<6} | {'MÃ ĐÁNH':<26} | {'VỐN DỒN (k)':<12} | {'THU (k)':<8} | {'LÃI/LỖ (k)':<11} | {'ROI':<8}",
                "-----------------------------------------------------------------------------------------------------------------------------"
            ]
            curr = start_dt
            tot_von, tot_thu, tot_lai = 0, 0, 0
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                short_date = curr.strftime("%d/%m")
                if ngay_str in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db)
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        sl = len(sorted_dan)
                        dan_str = " ".join([f"{x:02d}" for x in sorted_dan])
                        if len(dan_str) > 20: dan_str = dan_str[:17] + "..."
                        d_list = f"{sl:>2} mã: {dan_str}"
                        
                        prizes_today = db[ngay_str]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(base_pts * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c
                                day_rev += r_c
                                
                        if day_cost <= 0:
                            lines.append(f"{short_date:<6} | {d_list:<26} | {'0':<12} | {'0':<8} | {'[ĐỨNG NGOÀI]':<11} | {'-':<8}")
                        else:
                            lai = day_rev - day_cost
                            roi = (lai / day_cost * 100) if day_cost > 0 else 0
                            tot_von += day_cost
                            tot_thu += day_rev
                            tot_lai += lai
                            lines.append(f"{short_date:<6} | {d_list:<26} | {day_cost/1000:>12,.0f} | {day_rev/1000:>8,.0f} | {lai/1000:>+11,.0f} | {roi:>+6.1f}%")
                    else: lines.append(f"{short_date:<6} | {'🚫 [ĐỨNG NGOÀI]':<26} | {'-':<12} | {'-':<8} | {'-':<11} | {'-':<8}")
                else: lines.append(f"{short_date:<6} | ⚪ Chưa có dữ liệu DB{'':<1} | {'-':<12} | {'-':<8} | {'-':<11} | {'-':<8}")
                curr += timedelta(days=1)
                
            tot_roi = (tot_lai / tot_von * 100) if tot_von > 0 else 0
            lines.extend([
                "=============================================================================================================================",
                f"📝 TỔNG KẾT THÁNG {thang:02d}/{nam}:",
                f"💰 TỔNG VỐN DỒN TIERED   : {tot_von:,.0f} VNĐ",
                f"💵 TỔNG DOANH THU THƯỞNG  : {tot_thu:,.0f} VNĐ",
                f"🚀 LỢI NHUẬN RÒNG          : {tot_lai:+,.0f} VNĐ",
                f"📈 TỶ SUẤT R.O.I           : {tot_roi:+.2f} %"
            ])
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_4_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI THÔNG SỐ."
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = float(pts_per_code_base)
            lines = [
                "📑 BÁO CÁO ĐẠI KẾ TOÁN QUÉT CHU KỲ TỔNG HỢP",
                "===================================================================================================================",
                f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (LÕI V6.3 TIERED ĐỘC TÔN)",
                "==================================================================================================================="
            ]
            curr = start_dt
            daily_records = []
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                if ngay_str in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db)
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        prizes_today = db[ngay_str]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(base_pts * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c
                                day_rev += r_c
                        if day_cost > 0:
                            sl = len(sorted_dan)
                            lai = day_rev - day_cost
                            daily_records.append({
                                "dt": curr, "year": curr.year, "month_str": curr.strftime("%m/%Y"),
                                "codes": sl, "chi": day_cost, "lai": lai,
                                "win": 1 if lai > 0 else 0, "loss": 1 if lai <= 0 else 0,
                            })
                curr += timedelta(days=1)
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO XUẤT LỆNH THỰC TẾ."
            df_rec = pd.DataFrame(daily_records)
            lines.extend(["", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG", "-------------------------------------------------------------------------------------------------------------------", f"{'THÁNG/NĂM':<10} | {'PHIÊN':<7} | {'WIN/LOSS':<10} | {'VỐN ĐẦU TƯ':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}", "-------------------------------------------------------------------------------------------------------------------"])
            for m_str, g_m in df_rec.groupby("month_str", sort=False):
                m_chi, m_lai = g_m["chi"].sum(), g_m["lai"].sum()
                m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
                lines.append(f"Tháng {m_str:<5} | {len(g_m):<7} | {g_m['win'].sum()}W/{g_m['loss'].sum()}L | {m_chi:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%")
                
            tot_chi, tot_lai = df_rec["chi"].sum(), df_rec["lai"].sum()
            tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
            df_rec['cum_pnl'] = df_rec['lai'].cumsum()
            df_rec['peak'] = df_rec['cum_pnl'].cummax()
            max_dd = (df_rec['cum_pnl'] - df_rec['peak']).min()
            lines.extend(["===================================================================================================================", f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN | Win: {df_rec['win'].sum()} - Loss: {df_rec['loss'].sum()}):", f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ", f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ", f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %", f"• SỤT GIẢM VỐN LỚN NHẤT (Max Drawdown) : {abs(max_dd):,.0f} VNĐ", "==================================================================================================================="])
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_5_raw(ngay_raw):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            _, ngay_str = res
            if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại trên hệ thống."
            
            lo_to_raw = sorted(db[ngay_str]["prizes_int"])
            lines = ["📑 KẾT QUẢ LOTO THEO NGÀY", "=======================================================", f"📅 BIÊN BẢN KẾT QUẢ PHIÊN GIAO DỊCH: {ngay_str}", "🎰 Danh sách 27 giải ma trận phẳng (Đã sắp xếp tăng dần):"]
            row_str = ""
            for idx, lo in enumerate(lo_to_raw):
                row_str += f"[{lo:02d}] "
                if (idx + 1) % 9 == 0:
                    lines.append(row_str.strip())
                    row_str = ""
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_6_master_diagnostic_prompt():
        try:
            db, msg = DatabaseManager.load_db()
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if not min_dt or not max_dt: return "🛑 HỆ THỐNG RỖNG: Chưa có dữ liệu."
            
            start_dt = min_dt
            end_dt = max_dt
            total_days_scanned = (end_dt - start_dt).days + 1
            
            prompt_lines = [
                f"[HỒ SƠ SINH HỌC TOÀN HỆ THỐNG V6.3 ROBUST - DÀNH CHO BÁO CÁO ĐỊNH LƯỢNG CHUẨN TRUY VẾT]",
                f"1. PHIÊN BẢN HỆ THỐNG: {Config.VERSION}",
                f"2. QUÉT TRỌN VẸN LỊCH SỬ {total_days_scanned} NGÀY QUA ({start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')})\n",
                "📊 [BÁO CÁO HIỆU SUẤT ĐỘC TÔN V6.3]"
            ]
            
            curr = start_dt
            wins, losses, total_chi, total_thu = 0, 0, 0, 0
            daily_pnls = []
            
            while curr <= end_dt:
                str_dt = curr.strftime("%d/%m/%Y")
                if str_dt in db:
                    pred_data, _ = QuantEngine.get_full_prediction(curr, db)
                    mult, _ = QuantEngine.get_mm_multiplier(curr, db)
                    
                    if pred_data and pred_data["sorted_dan_scored"]:
                        sorted_dan = pred_data["sorted_dan_scored"]
                        prizes_today = db[str_dt]["prizes_int"]
                        day_cost, day_rev = 0.0, 0.0
                        
                        for idx_code, code_val in enumerate(sorted_dan):
                            k_tier = 1.30 if idx_code == 0 else (1.15 if idx_code in [1, 2] else 0.85)
                            pts_code = int(round(Config.BASE_PTS * mult * k_tier))
                            if pts_code > 0:
                                c_c = pts_code * Config.COST_PER_POINT
                                nh_c = prizes_today.count(code_val)
                                r_c = nh_c * pts_code * Config.WIN_PER_NHAY
                                day_cost += c_c
                                day_rev += r_c
                                
                        if day_cost > 0:
                            lai = day_rev - day_cost
                            total_chi += day_cost
                            total_thu += day_rev
                            daily_pnls.append(lai)
                            if lai > 0: wins += 1
                            else: losses += 1

                curr += timedelta(days=1)

            roi = ((total_thu - total_chi) / total_chi * 100) if total_chi > 0 else 0
            cum_pnl = np.cumsum(daily_pnls) if daily_pnls else []
            peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else []
            drawdowns = cum_pnl - peak if len(cum_pnl) > 0 else []
            max_dd = abs(min(drawdowns)) if len(drawdowns) > 0 else 0

            prompt_lines.extend([
                f"➤ LÕI DUY NHẤT: {Config.ACTIVE_MODE}",
                f"   - Total PnL: {(total_thu - total_chi):+,.0f} VNĐ | ROI: {roi:.2f}% | Max Drawdown: {max_dd:,.0f} VNĐ",
                f"   - Win/Loss: {wins}W / {losses}L | Vốn đầu tư: {total_chi:,.0f} VNĐ | Doanh thu: {total_thu:,.0f} VNĐ",
                "-" * 65
            ])

            prompt_lines.extend([
                "\n⚠️ XÁC NHẬN BÁO CÁO V6.3 ROBUST TIERED QUANT ENGINE:",
                "1. Tích hợp cơ chế Dồn vốn Bậc thang Risk-Parity chuẩn hóa: Bạch Thủ Lô (1.30x), Song Thủ Lô (1.15x), Lô Dàn Lót (0.85x).",
                "2. Đã thêm cơ chế Cache (Bộ nhớ đệm) giải quyết triệt để lỗi Load chậm và tràn RAM Menu 6.",
                "3. Hệ thống chạy 1 lõi toán học thuần túy duy nhất, không rườm rà, đảm bảo minh bạch và tối ưu tuyệt đối."
            ])
            return "\n".join(prompt_lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

# ==============================================================================
# ⚖️ BLOCK 7: ARBITRAGE & AUTO-CRAWL ODDS ENGINE (SĂN CHÊNH LỆCH TỶ LỆ)
# ==============================================================================
class OddsCrawler:
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }
    
    @staticmethod
    def crawl_bookie_a():
        try:
            return {"name": "Sàn A (Mẫu Crawl API)", "payout": 99.0, "rebate_percent": 1.0}
        except Exception as e:
            return {"name": "Sàn A (Lỗi)", "payout": 0, "rebate_percent": 0, "error": str(e)}

    @staticmethod
    def crawl_bookie_b():
        try:
            return {"name": "Sàn B (Mẫu Crawl HTML)", "payout": 99.5, "rebate_percent": 0.5}
        except Exception as e:
            return {"name": "Sàn B (Lỗi)", "payout": 0, "rebate_percent": 0, "error": str(e)}
            
    @staticmethod
    def get_all_live_odds():
        b1 = OddsCrawler.crawl_bookie_a()
        b2 = OddsCrawler.crawl_bookie_b()
        return [b1, b2]

class ArbitrageEngine:
    @staticmethod
    def auto_scan_surebet():
        bookies_data = OddsCrawler.get_all_live_odds()
        return ArbitrageEngine.calculate_surebet_de(bookies_data)

    @staticmethod
    def calculate_surebet_de(bookies_data):
        best_bookie = None
        best_effective_payout = 0
        
        for b in bookies_data:
            if b.get('payout', 0) == 0: continue
            
            actual_cost = 1.0 - (b.get('rebate_percent', 0) / 100.0)
            effective_payout = b['payout'] / actual_cost
            
            if effective_payout > best_effective_payout:
                best_effective_payout = effective_payout
                best_bookie = b

        if not best_bookie:
            return "🛑 LỖI: Không lấy được dữ liệu hoặc dữ liệu đầu vào trống."

        total_numbers = 100
        total_actual_cost = total_numbers * (1.0 - (best_bookie['rebate_percent'] / 100.0))
        net_profit = best_bookie['payout'] - total_actual_cost
        
        is_surebet = net_profit > 0
        roi = (net_profit / total_actual_cost) * 100 if total_actual_cost > 0 else 0
        
        lines = [
            "📑 BÁO CÁO RADAR QUÉT SUREBET",
            "=======================================================",
            f"🏆 Sàn tối ưu nhất: {best_bookie['name']} (Thưởng 1 ăn {best_bookie['payout']}, Hoàn trả {best_bookie['rebate_percent']}%)",
            f"💰 Vốn thực tế để bao trọn 100 số: {total_actual_cost:,.2f} điểm",
            f"💵 Tổng thu về khi trúng 1 số    : {best_bookie['payout']:,.2f} điểm",
            "-------------------------------------------------------"
        ]
        
        if is_surebet:
            lines.append(f"✅ TRẠNG THÁI: PHÁT HIỆN KẼ HỞ ARBITRAGE (SUREBET)!")
            lines.append(f"🚀 Lợi nhuận chắc chắn: +{net_profit:,.2f} điểm / vòng quay")
            lines.append(f"📈 Tỷ suất sinh lời (ROI): +{roi:.2f}%")
        else:
            lines.append(f"❌ TRẠNG THÁI: KHÔNG CÓ SUREBET.")
            lines.append(f"🔴 Mức lỗ nếu bao trọn 100 số: {net_profit:,.2f} điểm")
            
        return "\n".join(lines)
        
    @staticmethod
    def calculate_loto_ev(cost_per_point, payout_per_point, rebate_percent):
        expected_hits = 0.27 
        actual_cost = cost_per_point * (1.0 - (rebate_percent / 100.0))
        expected_revenue = expected_hits * payout_per_point
        ev_per_point = expected_revenue - actual_cost
        roi = (ev_per_point / actual_cost) * 100 if actual_cost > 0 else 0
        
        lines = [
            "📑 BÁO CÁO ĐỊNH GIÁ TRỊ KỲ VỌNG (EV) CHO LOTO 27 GIẢI",
            "=======================================================",
            f"• Giá mua 1 điểm (Thực tế) : {actual_cost:,.0f} VNĐ (Đã trừ {rebate_percent}% hoàn trả)",
            f"• Trả thưởng 1 nháy        : {payout_per_point:,.0f} VNĐ",
            f"• Kỳ vọng nháy/con số      : 0.27 nháy (Toán học tuyệt đối)",
            "-------------------------------------------------------",
            f"💵 Doanh thu kỳ vọng/điểm  : {expected_revenue:,.0f} VNĐ",
            f"📊 Lợi nhuận kỳ vọng (EV)  : {ev_per_point:+,.0f} VNĐ / 1 điểm",
            f"📈 Tỷ suất EV (Edge)       : {roi:+.2f}%"
        ]
        
        if ev_per_point > 0:
            lines.append("\n✅ KẾT LUẬN: ĐÁNH DÀI HẠN CHẮC CHẮN LÃI (POSITIVE EV).")
        else:
            lines.append("\n🔴 KẾT LUẬN: ĐÁNH DÀI HẠN CHẮC CHẮN LỖ (NEGATIVE EV).")
            
        return "\n".join(lines)

# ==============================================================================
# 📈 BLOCK 8: CHỨNG KHOÁN (AUTO-API & LOCAL SERVER DATABASE ENGINE)
# ==============================================================================
class StockQuantEngine:
    @staticmethod
    def fetch_stock_data(ticker, days=120):
        # 1. THỬ DNSE ENTRADE API
        try:
            end_date = Utils.get_vn_time()
            start_date = end_date - timedelta(days=days + 60)
            from_ts = int(start_date.timestamp())
            to_ts = int(end_date.timestamp())
            
            url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ticker.upper()}&from={from_ts}&to={to_ts}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if 't' in data and data['t']:
                    df = pd.DataFrame({'timestamp': data['t'], 'Close': data['c'], 'Volume': data['v']})
                    df['Date'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)
                    df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
                    df = df[['Date', 'Close', 'Volume']].dropna().reset_index(drop=True)
                    if len(df) >= 21:
                        return df, "DNSE Open API"
        except Exception:
            pass

        # 2. THỬ YAHOO FINANCE GLOBAL
        try:
            yf_ticker = f"{ticker.upper()}.VN"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}?range=1y&interval=1d"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get('chart', {}).get('result'):
                    result = data['chart']['result'][0]
                    timestamps = result['timestamp']
                    quote = result['indicators']['quote'][0]
                    df = pd.DataFrame({
                        'timestamp': timestamps,
                        'Close': quote['close'],
                        'Volume': quote['volume']
                    }).dropna()
                    df['Date'] = pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)
                    df['Date'] = df['Date'].dt.strftime('%d/%m/%Y')
                    df = df[['Date', 'Close', 'Volume']].reset_index(drop=True)
                    if len(df) >= 21:
                        return df, "Yahoo Finance Global API"
        except Exception:
            pass
            
        return None, "🛑 LỖI API: Sàn chứng khoán hiện đang chặn IP Cloud. Vui lòng sử dụng Tab 2 để đọc Database Excel cố định."

    @staticmethod
    def process_stock_dataframe(df, source_label, ticker):
        if len(df) < 21:
            return f"🛑 THIẾU DỮ LIỆU: Cần ít nhất 21 phiên lịch sử. Hiện tại có {len(df)} phiên.", gr.update(visible=False)

        # Chuẩn hóa cột
        df['Close'] = df['Close'].astype(str).str.replace(',', '').astype(float)
        df['Volume'] = df['Volume'].astype(str).str.replace(',', '').astype(float)

        df['Prev_Close'] = df['Close'].shift(1)
        df['MA20_Price'] = df['Close'].rolling(window=20).mean()
        df['StdDev20_Price'] = df['Close'].rolling(window=20).std()
        df['MA20_Vol'] = df['Volume'].rolling(window=20).mean()
        df['Z_Score'] = (df['Close'] - df['MA20_Price']) / df['StdDev20_Price']
        
        latest = df.iloc[-1]
        alerts = []
        
        vol_ratio = latest['Volume'] / latest['MA20_Vol'] if latest['MA20_Vol'] > 0 else 0
        if vol_ratio > 2.5 and latest['Close'] > latest['Prev_Close']:
            alerts.append(f"🟢 [SMART MONEY]: NỔ KHỐI LƯỢNG! Vol gấp {vol_ratio:.1f} lần trung bình. Dòng tiền cá mập vào gom hàng, MUA BREAKOUT.")
        elif vol_ratio > 2.5 and latest['Close'] < latest['Prev_Close']:
            alerts.append(f"🔴 [DUMP]: Bị xả hàng cực mạnh. Vol gấp {vol_ratio:.1f} lần trung bình. NÉ NGAY.")
            
        z = latest['Z_Score']
        if pd.notna(z):
            if z < -2.0:
                alerts.append(f"🟣 [QUÁ BÁN]: Z-Score = {z:.2f}. Giá rơi tự do quá mốc 2 độ lệch chuẩn. CHUẨN BỊ BẮT ĐÁY.")
            elif z > 2.0:
                alerts.append(f"🔴 [QUÁ MUA]: Z-Score = {z:.2f}. Hưng phấn ảo, rủi ro cực cao. CHỐT LỜI.")
            
        if not alerts:
            alerts.append("⚪ [TRẠNG THÁI BÌNH THƯỜNG]: Dao động an toàn, không có tín hiệu bất thường.")
            
        lines = [
            f"📑 BÁO CÁO CẢM BIẾN DÒNG TIỀN MÃ: {ticker.upper()}",
            "=======================================================",
            f"✅ ĐÃ XỬ LÝ THÀNH CÔNG {len(df)} PHIÊN TỪ NGUỒN: {source_label}",
            "=======================================================",
            f"📅 Phiên giao dịch gần nhất : {latest['Date']}",
            f"💵 Giá Đóng Cửa             : {latest['Close']:,.2f} VNĐ",
            f"📊 Khối Lượng               : {latest['Volume']:,.0f} Cổ phiếu",
            "-------------------------------------------------------",
            f"• MA20 Giá                  : {latest['MA20_Price']:,.2f}",
            f"• Chỉ số Z-Score            : {latest['Z_Score']:+.2f}",
            f"• Đột biến Vol (Vol Ratio)  : x{vol_ratio:.2f}",
            "=======================================================",
            "🤖 KHUYẾN NGHỊ TỪ LÕI QUANT:"
        ]
        lines.extend(alerts)
        
        filename = f"Data_Stock_{ticker.upper()}.xlsx"
        df[['Date', 'Close', 'Volume']].to_excel(filename, index=False)
        
        return "\n".join(lines), gr.update(value=filename, visible=True)

    @staticmethod
    def run_auto_stock_sensors(ticker, days=120):
        df, source_msg = StockQuantEngine.fetch_stock_data(ticker, days)
        if df is None: 
            return source_msg, gr.update(visible=False)
        return StockQuantEngine.process_stock_dataframe(df.tail(days), source_msg, ticker)

    @staticmethod
    def run_server_database_sensors(ticker):
        ticker_clean = ticker.strip().upper()
        
        # Tìm file chuẩn dạng Data_Stock_HPG.xlsx hoặc Data_HPG.xlsx
        possible_files = [
            f"Data_Stock_{ticker_clean}.xlsx",
            f"Data_Quant_{ticker_clean}.xlsx",
            f"Data_{ticker_clean}.xlsx"
        ]
        
        target_file = None
        for f in possible_files:
            if os.path.exists(f):
                target_file = f
                break
                
        if not target_file:
            matches = glob.glob(f"*{ticker_clean}*.xlsx")
            if matches:
                target_file = matches[0]
                
        if not target_file:
            all_excel = glob.glob("*.xlsx")
            excel_str = ", ".join(all_excel) if all_excel else "Chưa có file .xlsx nào"
            return f"🛑 KHÔNG TÌM THẤY DATABASE SERVER: Không có file Excel chứa mã '{ticker_clean}' trên máy chủ.\n👉 Các file Excel hiện có trên Server: [{excel_str}]", gr.update(visible=False)
            
        try:
            df = pd.read_excel(target_file)
            if not set(['Date', 'Close', 'Volume']).issubset(df.columns):
                return f"🛑 LỖI CẤU TRÚC FILE '{target_file}': File Excel cần chứa đủ 3 cột 'Date', 'Close', 'Volume'.", gr.update(visible=False)
                
            return StockQuantEngine.process_stock_dataframe(df, f"DATABASE CỐ ĐỊNH SERVER ({target_file})", ticker_clean)
        except Exception as e:
            return f"🛑 LỖI ĐỌC FILE DATABASE SERVER: {str(e)}", gr.update(visible=False)

# ==============================================================================
# 🎨 UI & APP LAUNCHER
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    min_dt_init, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title=Config.VERSION, theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 MULTI-MARKET QUANT ENGINE {Config.VERSION}")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        # [Cột 1] Đồng bộ Loto
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (QUÉT RADAR CRAWLER ĐA LUỒNG)", variant="primary")
            
            gr.Markdown("---")
            gr.Markdown("✍️ **NHẬP KẾT QUẢ BẰNG TAY (DÀNH CHO NGÀY WEB CRAWLER BỊ KHÓA IP)**")
            with gr.Row():
                manual_date = gr.Textbox(label="Ngày (DD/MM/YYYY)", placeholder="Ví dụ: 01/08/2026")
                manual_numbers = gr.Textbox(label="Chuỗi 27 số (54 ký tự liền nhau)", placeholder="Copy/Paste chuỗi số vào đây...")
            btn_manual_save = gr.Button("📥 LƯU DỮ LIỆU VÀO DATABASE", variant="primary")
            gr.Markdown("---")

            out_1 = gr.Textbox(label="Biên bản Báo cáo Hệ thống", lines=8)
            title_2 = gr.Markdown(f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt_init.strftime('%d/%m/%Y') if next_predict_dt_init else ''}")
            
            gr.Markdown("---")
            gr.Markdown("### 📥 TẢI DATABASE LOTO VỀ MÁY TRỰC TIẾP")
            with gr.Row():
                btn_prepare_dl = gr.Button("1️⃣ BẤM ĐỂ TRÍCH XUẤT FILE TỪ MÁY CHỦ", variant="primary")
            with gr.Row():
                dl_output = gr.DownloadButton("2️⃣ 📥 BẤM VÀO ĐÂY ĐỂ TẢI FILE XUỐNG", variant="primary", visible=False)
                
            def get_excel_file():
                path = os.path.abspath(Config.DATA_FILE)
                if os.path.exists(path):
                    return gr.update(value=path, visible=True)
                return gr.update(visible=False)
                
            btn_prepare_dl.click(fn=get_excel_file, inputs=[], outputs=dl_output)
            
        # [Cột 2] Khuyến nghị Loto
        with gr.Column(visible=False) as col_2:
            with gr.Row():
                pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
            btn_2 = gr.Button("🔍 XUẤT LỆNH GIAO DỊCH CAO CẤP", variant="primary")
            out_2 = gr.Textbox(label="Hồ sơ Lệnh Tác Chiến", lines=25)
            btn_2.click(Auditor.phan_he_2_predict, inputs=[pts_2], outputs=out_2)
            
        # [Cột 3] Kiểm toán
        with gr.Column(visible=False) as col_3:
            gr.Markdown("### 🔍 MODULE KIỂM TOÁN CHUYÊN SÂU & TRUY VẾT")
            audit_type = gr.Radio(
                choices=["Kiểm toán 1 Ngày", "Kiểm toán Cả Tháng"], 
                value="Kiểm toán 1 Ngày", 
                label="Loại Kiểm toán"
            )
            with gr.Column(visible=True) as row_audit_day:
                date_3 = gr.Textbox(label="Ngày Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            with gr.Column(visible=False) as row_audit_month:
                month_3 = gr.Textbox(label="Tháng Truy xuất (MM/YYYY)", value=latest_dt_init.strftime('%m/%Y') if latest_dt_init else "")
            pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_3 = gr.Button("📡 THỰC THI KIỂM TOÁN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Kiểm toán", lines=24)
            
            def toggle_audit(choice):
                is_day = (choice == "Kiểm toán 1 Ngày")
                return gr.Column(visible=is_day), gr.Column(visible=not is_day)
            
            audit_type.change(fn=toggle_audit, inputs=audit_type, outputs=[row_audit_day, row_audit_month])
            btn_3.click(Auditor.phan_he_3_router, inputs=[audit_type, date_3, month_3, pts_3], outputs=out_3)

        # [Cột 4] Phân tích Chu kỳ
        with gr.Column(visible=False) as col_4:
            with gr.Row():
                t1_4 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value=min_dt_init.strftime('%d/%m/%Y') if min_dt_init else "")
                t2_4 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Dòng Tiền & Max Drawdown", lines=22)
            btn_4.click(Auditor.phan_he_4_range, inputs=[t1_4, t2_4, pts_4], outputs=out_4)

        # [Cột 5] Bảng Loto Gốc
        with gr.Column(visible=False) as col_5:
            date_5 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_5 = gr.Button("💾 TRUY XUẤT KẾT QUẢ LOTO TRUYỀN THỐNG", variant="primary")
            out_5 = gr.Textbox(label="Bảng Kết Quả Loto", lines=15)
            btn_5.click(Auditor.phan_he_5_raw, inputs=date_5, outputs=out_5)

        # [Cột 6] AI Tổng hợp Loto
        with gr.Column(visible=False) as col_6:
            gr.Markdown("### 🤖 BỘ NÃO AI - QUÉT TOÀN BỘ LỊCH SỬ DB")
            btn_6 = gr.Button("🧬 BẮT ĐẦU QUÉT TOÀN DB", variant="primary")
            out_6 = gr.Textbox(label="Báo cáo Tổng hợp V6.3", lines=25)
            btn_6.click(Auditor.phan_he_6_master_diagnostic_prompt, inputs=[], outputs=out_6)

        # [Cột 7] HỆ THỐNG RADAR ARBITRAGE
        with gr.Column(visible=False) as col_7:
            gr.Markdown("### ⚖️ MODULE ARBITRAGE KẼ HỞ NHÀ CÁI")
            
            with gr.Tab("1. Quét Surebet Đề Tự Động"):
                gr.Markdown("*(Yêu cầu cấu hình lại Link API trong code lõi Block 7)*")
                btn_auto_scan = gr.Button("🌐 CHẠY RADAR CRAWL TỰ ĐỘNG", variant="primary")
                out_arbitrage_auto = gr.Textbox(label="Kết quả Radar Tự động", lines=10)
                btn_auto_scan.click(ArbitrageEngine.auto_scan_surebet, inputs=[], outputs=out_arbitrage_auto)
                
            with gr.Tab("2. Quét Surebet Nhập Tay (An Toàn)"):
                with gr.Row():
                    b1_name = gr.Textbox(label="Sàn A", value="Nhà Cái 1")
                    b1_payout = gr.Number(label="Ăn (VD: 99.0)", value=99.0)
                    b1_rebate = gr.Number(label="Hoàn trả %", value=0.0)
                with gr.Row():
                    b2_name = gr.Textbox(label="Sàn B", value="Nhà Cái 2")
                    b2_payout = gr.Number(label="Ăn (VD: 99.5)", value=99.5)
                    b2_rebate = gr.Number(label="Hoàn trả %", value=0.5)
                btn_manual_arb = gr.Button("🔍 KIỂM TRA SUREBET", variant="primary")
                out_arb_manual = gr.Textbox(label="Báo Cáo Surebet Nhập Tay", lines=10)
                
                def run_surebet_manual(n1, p1, r1, n2, p2, r2):
                    return ArbitrageEngine.calculate_surebet_de([
                        {'name': n1, 'payout': p1, 'rebate_percent': r1},
                        {'name': n2, 'payout': p2, 'rebate_percent': r2}
                    ])
                btn_manual_arb.click(run_surebet_manual, inputs=[b1_name, b1_payout, b1_rebate, b2_name, b2_payout, b2_rebate], outputs=out_arb_manual)
                
            with gr.Tab("3. Đo lường Lợi thế EV Loto"):
                with gr.Row():
                    cost_loto = gr.Number(label="Giá 1 điểm (VNĐ)", value=27000)
                    payout_loto = gr.Number(label="Trả thưởng 1 điểm (VNĐ)", value=99000)
                    rebate_loto = gr.Number(label="Hoàn trả %", value=1.0)
                btn_ev = gr.Button("⚖️ ĐO LƯỜNG LỢI THẾ TOÁN HỌC (EV)", variant="primary")
                out_ev = gr.Textbox(label="Báo cáo EV", lines=12)
                btn_ev.click(ArbitrageEngine.calculate_loto_ev, inputs=[cost_loto, payout_loto, rebate_loto], outputs=out_ev)

        # [Cột 8] CẢM BIẾN CHỨNG KHOÁN (DUAL MODE: OFFLINE SERVER DB & ONLINE API)
        with gr.Column(visible=False) as col_8:
            gr.Markdown("### 🧠 HỆ THỐNG CẢM BIẾN CHỨNG KHOÁN (QUANT SCANNER)")
            
            with gr.Tab("1. Đọc Database Server Cố Định (KHÔNG CẦN MẠNG / BẮT CẢM BIẾN SÂU)"):
                gr.Markdown("**Hướng dẫn:** Nhập mã chứng khoán (Ví dụ: `HPG`). Hệ thống sẽ tự động đọc file Excel đã commit trên GitHub (`Data_Stock_HPG.xlsx`), phân tích Z-Score và Volume Ratio.")
                with gr.Row():
                    stock_ticker_db = gr.Textbox(label="Mã Cổ Phiếu Cần Truy Xuất Database", value="HPG")
                btn_server_db_stock = gr.Button("📊 ĐỌC DATABASE SERVER & QUÉT CẢM BIẾN", variant="primary")
                out_stock_db_report = gr.Textbox(label="Báo cáo Phân tích từ Database Server", lines=15)
                dl_stock_db_file = gr.DownloadButton("📥 BẤM VÀO ĐÂY ĐỂ TẢI FILE EXCEL SERVER", variant="primary", visible=False)
                
                btn_server_db_stock.click(
                    StockQuantEngine.run_server_database_sensors,
                    inputs=[stock_ticker_db],
                    outputs=[out_stock_db_report, dl_stock_db_file]
                )

            with gr.Tab("2. Cào Online Live API (Khi Cần Cập Nhật Dữ Liệu Mới)"):
                gr.Markdown("**Hướng dẫn:** Nhập mã cổ phiếu. Hệ thống sẽ tự động móc API Đa Tầng (DNSE/Yahoo) để cào dữ liệu mới.")
                with gr.Row():
                    stock_ticker_api = gr.Textbox(label="Mã Cổ Phiếu Online (SSI, HPG, FPT)", value="SSI")
                    days_to_fetch = gr.Slider(minimum=30, maximum=365, value=120, step=10, label="Số ngày muốn cào lịch sử")
                btn_auto_stock = gr.Button("🚀 CÀO DỮ LIỆU & QUÉT CẢM BIẾN", variant="primary")
                out_stock_report = gr.Textbox(label="Báo cáo Phân tích Live API", lines=15)
                dl_stock_file = gr.DownloadButton("📥 BẤM VÀO ĐÂY ĐỂ TẢI FILE EXCEL VỪA CÀO", variant="primary", visible=False)
                
                btn_auto_stock.click(
                    StockQuantEngine.run_auto_stock_sensors, 
                    inputs=[stock_ticker_api, days_to_fetch], 
                    outputs=[out_stock_report, dl_stock_file]
                )

        # Mapping Events Loto Cột 1
        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])
        btn_manual_save.click(Auditor.process_manual_input, inputs=[manual_date, manual_numbers], outputs=[out_1, title_2])

        # Control UI Visibility
        def update_visibility(choice):
            return [
                gr.Column(visible=(choice == Config.MENU_OPTIONS[0])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[1])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[2])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[3])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[4])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[5])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[6])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[7])),
            ]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6, col_7, col_8])
        
    return demo

# ==============================================================================
# 🚀 LAUNCHER CONFIGURATION FOR RENDER
# ==============================================================================
if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
