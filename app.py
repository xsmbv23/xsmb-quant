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
    VERSION = "V6.0 KINETIC KELLY ENGINE (ANTI-MARTINGALE & LÔ GAN FILTER)" 
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    BACKUP_PREFIX = "Ket_Qua_Loto27_Backup_" 
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    BASE_PTS = 10.0
    
    ACTIVE_MODE = "🤖 [VERSION 6.0] KINETIC KELLY ENGINE"
    
    MENU_OPTIONS = [
        "🔄 1. ĐỒNG BỘ & CẬP NHẬT DỮ LIỆU",
        "🎯 2. KHUYẾN NGHỊ LỆNH GIAO DỊCH",
        "🔍 3. KIỂM TOÁN CHUYÊN SÂU",
        "📈 4. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 5. BẢNG KẾT QUẢ LOTO TRUYỀN THỐNG",
        "🤖 6. BỘ NÃO AI (QUÉT LỊCH SỬ KINETIC KELLY)"
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
# 🕸️ BLOCK 3: CRAWLER TỰ ĐỘNG (KETQUA NỐI TIẾP VỚI TỊNH TIẾN DOMAIN)
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
# 📊 BLOCK 4: DATABASE MANAGER (TỰ ĐỘNG CHUẨN HÓA & BACKUP NGẦM LÊN DRIVE)
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
        
        # Mốc 19:00 hàng ngày (GMT+7)
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
# 🧠 BLOCK 5: QUANT ENGINE (LÕI V6.0 KINETIC KELLY - ANTI MARTINGALE & LÔ GAN FILTER)
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
        cache_key = (target_dt, "V6.0_SIGNAL")
        if cache_key in QuantEngine._sig_cache:
            return QuantEngine._sig_cache[cache_key]

        trace_log = []
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates: 
            res = ([], "[THIẾU DỮ LIỆU]")
            QuantEngine._sig_cache[cache_key] = res
            return res

        target_weekday = target_dt.weekday()
        t_minus_7_dt = None
        for p_dt in past_dates:
            if p_dt.weekday() == target_weekday and (target_dt - p_dt).days >= 7:
                t_minus_7_dt = p_dt
                break
                
        if t_minus_7_dt is None: 
            res = ([], "[THIẾU DỮ LIỆU T-7 ĐỒNG PHA]")
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

        # ⚡ V6.0 MÀNG LỌC LÔ GAN (Loại bỏ các mã không xuất hiện trong 15 ngày qua)
        recent_15_nums = set()
        for p_dt in past_dates[:15]: 
            str_p = p_dt.strftime("%d/%m/%Y")
            recent_15_nums.update(db[str_p]["prizes_int"])
            
        dan_opt = [x for x in so_khuyet_goc if x in recent_15_nums]
        
        res = (sorted(list(dan_opt)), "OK")
        QuantEngine._sig_cache[cache_key] = res
        return res

    @staticmethod
    def get_full_prediction(target_dt, db):
        dan_opt, msg = QuantEngine.get_signal(target_dt, db)
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        
        if not past_dates or not dan_opt:
            return None, f"{msg}\n👉 Truy vết: Không đủ điều kiện tạo dàn hoặc toàn bộ mã khuyết là Lô Gan."

        recent_14 = past_dates[:14]
        freq_14 = {}
        hundreds_freq = {i: 0 for i in range(10)}
        
        for p_dt in recent_14:
            p_str = p_dt.strftime("%d/%m/%Y")
            prizes = db[p_str]["prizes_int"]
            raw_tokens = db[p_str]["raw_str"].split()
            for num in prizes: freq_14[num] = freq_14.get(num, 0) + 1
            for token in raw_tokens:
                if len(token) >= 3:
                    h_digit = int(token[-3])
                    hundreds_freq[h_digit] += 1

        prizes_t7 = set(db[past_dates[6].strftime("%d/%m/%Y")]["prizes_int"]) if len(past_dates) >= 7 else set()
        
        # Scoring logic
        scored_candidates = sorted(
            dan_opt, 
            key=lambda x: (freq_14.get(x, 0) * 1.5 + (2.0 if x in prizes_t7 else 0.0), x), 
            reverse=True
        )
        
        final_dan = list(scored_candidates)
        best_btl = final_dan[0] if len(final_dan) > 0 else 0
        lon_btl = (best_btl % 10) * 10 + (best_btl // 10)
        
        if len(final_dan) >= 3: stl_pair = (final_dan[1], final_dan[2])
        elif len(final_dan) == 2: stl_pair = (final_dan[1], lon_btl if lon_btl != best_btl and lon_btl != final_dan[1] else (best_btl + 11) % 100)
        else: stl_pair = (lon_btl if lon_btl != best_btl else (best_btl + 11) % 100, (best_btl + 22) % 100)

        sec1, sec2 = stl_pair[0], stl_pair[1]
        loto_xien2 = f"{best_btl:02d} - {sec1:02d} | {best_btl:02d} - {sec2:02d}"

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
            "btl": f"{best_btl:02d}", "stl": f"{stl_pair[0]:02d} - {stl_pair[1]:02d}", "xien2": loto_xien2,
            "cang3d": loto_3cang, "kep": lo_kep, "dan_de_10": dan_de_10, "sorted_dan_scored": final_dan,
            "sig_trace": f"[Lõi V6.0] Bắt được {len(final_dan)} mã khuyết (Đã lọc Lô Gan 15 ngày)."
        }, "OK"

    @staticmethod
    def get_mm_multiplier(target_dt, db):
        cache_key = (target_dt, "V6.0_MM")
        if cache_key in QuantEngine._mm_cache:
            return QuantEngine._mm_cache[cache_key]
            
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates: 
            res = (0.0, "Không có dữ liệu lịch sử.")
            QuantEngine._mm_cache[cache_key] = res
            return res

        trace_log = []
        
        # 1. TÍNH TOÁN CHUỖI WIN/LOSS THỰC TẾ (ANTI-MARTINGALE TRACKER)
        win_streak = 0
        loss_streak = 0
        for curr_dt in past_dates[:30]: 
            dan, _ = QuantEngine.get_signal(curr_dt, db)
            if dan and len(dan) > 0:
                str_curr = curr_dt.strftime("%d/%m/%Y")
                nhay = sum(db[str_curr]["prizes_int"].count(x) for x in dan)
                cost = len(dan) * Config.COST_PER_POINT
                rev = nhay * Config.WIN_PER_NHAY
                if rev - cost > 0:
                    if loss_streak > 0: break # Đang đếm Loss mà gặp Win thì dừng
                    win_streak += 1
                else:
                    if win_streak > 0: break # Đang đếm Win mà gặp Loss thì dừng
                    loss_streak += 1

        # 2. TÍNH TIÊU CHUẨN KELLY (KELLY CRITERION) TRÊN 21 NGÀY CHƠI GẦN NHẤT
        played_21 = 0
        wins_21 = 0
        for r_dt in past_dates:
            if played_21 >= 21: break
            str_r = r_dt.strftime("%d/%m/%Y")
            r_dan, _ = QuantEngine.get_signal(r_dt, db)
            if r_dan and len(r_dan) > 0:
                played_21 += 1
                nhay = sum(db[str_r]["prizes_int"].count(x) for x in r_dan)
                if (nhay * Config.WIN_PER_NHAY - len(r_dan) * Config.COST_PER_POINT) > 0:
                    wins_21 += 1
                    
        W = (wins_21 / played_21) if played_21 > 0 else 0.0
        L = 1.0 - W
        R = (Config.WIN_PER_NHAY / Config.COST_PER_POINT) - 1.0 # ~ 2.68
        
        kelly_pct = W - (L / R)
        
        trace_log.append(f"🤖 [V6.0 KINETIC KELLY] Win Rate (21 phiên): {W*100:.1f}% | Tỷ lệ Lợi/Rủi (R): {R:.2f}")
        
        # 3. QUY TRÌNH XUỐNG TIỀN THEO QUỸ PHÒNG HỘ (ANTI-MARTINGALE)
        if kelly_pct <= 0:
            final_mult = 0.0
            action_log = f"Kelly = {kelly_pct*100:.1f}% <= 0 -> ĐỨNG NGOÀI (Thị trường rác, không có lợi thế)"
        else:
            # Base scale: 10% Kelly -> x1.0
            base_mult = kelly_pct * 10.0 
            
            if loss_streak == 1:
                am_mod = 0.5
                desc = "Giảm 50% Vol (Vừa cắt chuỗi Win, rủi ro cao)"
            elif loss_streak == 2:
                am_mod = 0.25
                desc = "Giảm 75% Vol (Loss 2 liên tiếp)"
            elif loss_streak >= 3:
                am_mod = 0.10
                desc = "Cò cưa 10% Vol (Đang trong tâm bão)"
            elif win_streak == 1:
                am_mod = 1.5
                desc = "Bơm 150% Vol (Bắt đầu vào form Win)"
            elif win_streak >= 2:
                am_mod = 2.0
                desc = "Full Margin 200% Vol (Gồng lời - Lấy mỡ nó rán nó)"
            else:
                am_mod = 1.0
                desc = "Bình chuẩn"
                
            final_mult = base_mult * am_mod
            if final_mult > 5.0: final_mult = 5.0 # Max trần x5
            
            action_log = f"Kelly = {kelly_pct*100:.1f}% -> Base: x{base_mult:.2f} | Anti-Martingale: {desc} -> Chốt: x{final_mult:.2f}"
        
        trace_log.append(f"👉 HÀNH ĐỘNG: {action_log}")
        
        res = (final_mult, "\n".join(trace_log))
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

            if so_luong_lo == 0 or multiplier <= 0:
                lines = [
                    "📑 BÁO CÁO KHUYẾN NGHỊ GIAO DỊCH QUANT CAO CẤP",
                    "=======================================================",
                    f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}",
                    f"🎚️ CHIẾN LƯỢC ĐỘC TÔN  : {Config.ACTIVE_MODE}",
                    "=======================================================",
                    "👉 HỆ THỐNG XÁC NHẬN ĐỨNG NGOÀI BẢO TOÀN VỐN (0 ĐIỂM)",
                    "💡 Lý do: Kelly Criterion <= 0 hoặc Không có mã khuyết chuẩn.",
                    "\n--- BẢN GHI TRUY VẾT CẢM BIẾN ---",
                    mm_trace
                ]
                return "\n".join(lines)

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
                if pts_this > 0:
                    dan_alloc_lines.append(f"   + Mã [{code_val:02d}] ({tag:<16}) : {pts_this:>3} điểm | Vốn: {cost_this:,.0f} VND")

            alloc_detail_str = "\n".join(dan_alloc_lines) if total_von > 0 else "   👉 HỆ THỐNG XÁC NHẬN ĐỨNG NGOÀI (BẢO TOÀN VỐN)"

            if total_von > 0:
                pts_needed = math.ceil(total_von / Config.WIN_PER_NHAY)
                low_p = allocated_items[-1][2]
                nhay_low_needed = math.ceil(pts_needed / low_p) if low_p > 0 else 0
                btl_p = allocated_items[0][2]
                rem_p = max(0, pts_needed - btl_p)
                breakeven_explanation = (
                    f"💡 MỤC TIÊU HÒA VỐN       : Cần tổng tối thiểu {pts_needed} ĐIỂM LÔ nổ (Thu về >= {pts_needed * Config.WIN_PER_NHAY:,.0f} VND)\n"
                    f"   👉 Ví dụ thực tế có LÃI : Chỉ cần {nhay_low_needed} nháy Lót ({low_p}đ/nháy), hoặc 1 nháy BTL ({btl_p}đ) + {rem_p}đ nổ bổ sung."
                )
            else:
                breakeven_explanation = "💡 MỤC TIÊU HÒA VỐN       : Không khả dụng do Đứng Ngoài."

            lines = [
                "📑 BÁO CÁO KHUYẾN NGHỊ GIAO DỊCH QUANT CAO CẤP",
                "=======================================================",
                f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}",
                f"🎚️ CHIẾN LƯỢC ĐỘC TÔN  : {Config.ACTIVE_MODE}",
                f"📋 DÀN SỐ GỐC TỪ LÕI V5.6: [ {dan_goc_str} ]",
                "=======================================================",
                "📊 HỒ SƠ CHỐT SỐ THƯỞNG KÊ (DỰ BÁO KQXS CAO CẤP)",
                "-------------------------------------------------------",
                f"{'Bạch Thủ Lô':<22} | {pred_data['btl']}",
                f"{'Song Thủ Lô':<22} | {pred_data['stl']}",
                f"{'Lô Xiên 2':<22} | {pred_data['xien2']}",
                f"{'Lô Kép Bằng':<22} | {pred_data['kep']}",
                f"{'Dàn Đề 10 Số':<22} | {pred_data['dan_de_10']}",
                "-------------------------------------------------------",
                f"💰 QUẢN TRỊ VỐN & CHI TIẾT PHÂN BỔ BẬC THANG:",
                alloc_detail_str,
                "-------------------------------------------------------",
                f"💰 TỔNG VỐN TÁC CHIẾN   : {total_von:,.0f} VNĐ",
                breakeven_explanation,
                "\n--- BẢN GHI TRUY VẾT CẢM BIẾN ---",
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
                if sl == 0 or mult <= 0:
                    lines.append(f"🛑 [{mode_name}] 👉 HỆ THỐNG XÁC NHẬN ĐỨNG NGOÀI")
                    lines.extend(["   --- LOG TRUY VẾT CẢM BIẾN ---", "   " + mm_trace.replace("\n", "\n   ")])
                    return "\n".join(lines)
                    
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
                st = "🟢 WIN" if lai > 0 else ("🔴 LOSS" if day_cost > 0 else "⚪ ĐỨNG NGOÀI")
                lines.extend([
                    f"📌 [{mode_name}]",
                    f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in sorted_dan]),
                    f" • Chi tiết trúng: " + (", ".join(hit_details) if hit_details else "🚫 Không trúng mã nào (hoặc không đánh)"),
                    f" • Tổng vốn: {day_cost/1000:,.0f}k | Thu về: {day_rev/1000:,.0f}k",
                    f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})\n"
                ])
                lines.extend(["   --- LOG TRUY VẾT CẢM BIẾN ---", "   " + mm_trace.replace("\n", "\n   ")])
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
                f"🎚️ LÕI ĐỘC TÔN: V6.0 KINETIC KELLY",
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
                f"💰 TỔNG VỐN XUỐNG TIỀN THỰC : {tot_von:,.0f} VNĐ",
                f"💵 TỔNG DOANH THU THƯỞNG    : {tot_thu:,.0f} VNĐ",
                f"🚀 LỢI NHUẬN RÒNG           : {tot_lai:+,.0f} VNĐ",
                f"📈 TỶ SUẤT R.O.I            : {tot_roi:+.2f} %"
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
                f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (LÕI V6.0 KINETIC KELLY)",
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
            lines.extend(["", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG", "-------------------------------------------------------------------------------------------------------------------", f"{'THÁNG/NĂM':<10} | {'SỐ NGÀY ĐÁNH':<12} | {'WIN/LOSS':<10} | {'VỐN ĐẦU TƯ':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}", "-------------------------------------------------------------------------------------------------------------------"])
            for m_str, g_m in df_rec.groupby("month_str", sort=False):
                m_chi, m_lai = g_m["chi"].sum(), g_m["lai"].sum()
                m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
                lines.append(f"Tháng {m_str:<5} | {len(g_m):<12} | {g_m['win'].sum()}W/{g_m['loss'].sum()}L | {m_chi:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%")
                
            tot_chi, tot_lai = df_rec["chi"].sum(), df_rec["lai"].sum()
            tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
            df_rec['cum_pnl'] = df_rec['lai'].cumsum()
            df_rec['peak'] = df_rec['cum_pnl'].cummax()
            max_dd = (df_rec['cum_pnl'] - df_rec['peak']).min()
            lines.extend(["===================================================================================================================", f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN XUẤT LỆNH | Win: {df_rec['win'].sum()} - Loss: {df_rec['loss'].sum()}):", f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ", f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ", f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %", f"• SỤT GIẢM VỐN LỚN NHẤT (Max Drawdown) : {abs(max_dd):,.0f} VNĐ", "==================================================================================================================="])
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
                f"[HỒ SƠ SINH HỌC TOÀN HỆ THỐNG V6.0 KINETIC KELLY]",
                f"1. PHIÊN BẢN HỆ THỐNG: {Config.VERSION}",
                f"2. QUÉT TRỌN VẸN LỊCH SỬ {total_days_scanned} NGÀY QUA ({start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')})\n",
                "📊 [BÁO CÁO CỤ THỂ CHIẾN LƯỢC QUẢN TRỊ RỦI RO ĐỘNG LƯỢNG]"
            ]
            
            curr = start_dt
            wins, losses = 0, 0
            days_traded, days_skipped = 0, 0
            total_chi, total_thu = 0, 0
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
                            days_traded += 1
                            lai = day_rev - day_cost
                            total_chi += day_cost
                            total_thu += day_rev
                            daily_pnls.append(lai)
                            if lai > 0: wins += 1
                            else: losses += 1
                        else:
                            if len(sorted_dan) > 0:
                                days_skipped += 1

                curr += timedelta(days=1)

            roi = ((total_thu - total_chi) / total_chi * 100) if total_chi > 0 else 0
            cum_pnl = np.cumsum(daily_pnls) if daily_pnls else []
            peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else []
            drawdowns = cum_pnl - peak if len(cum_pnl) > 0 else []
            max_dd = abs(min(drawdowns)) if len(drawdowns) > 0 else 0

            prompt_lines.extend([
                f"➤ TỔNG QUAN LÕI ĐỘC TÔN: {Config.ACTIVE_MODE}",
                f"   - Tổng số ngày quét : {total_days_scanned} ngày",
                f"   - Số ngày Đứng ngoài: {days_skipped} ngày (Thị trường Kelly âm/Tâm bão)",
                f"   - Số ngày Xuống tiền: {days_traded} ngày (Bắn nhồi Vol khi có Trend)",
                f"   - Win/Loss (Thực)   : {wins}W / {losses}L",
                "-" * 65,
                f"💰 KẾT QUẢ ĐẦU TƯ THỰC TẾ TRÊN {days_traded} NGÀY ĐÁNH:",
                f"   - Tổng Vốn Xuống Tiền : {total_chi:,.0f} VNĐ",
                f"   - Tổng Doanh Thu      : {total_thu:,.0f} VNĐ",
                f"   - PnL Ròng (Lợi nhuận): {(total_thu - total_chi):+,.0f} VNĐ",
                f"   - Tỷ suất ROI         : {roi:.2f}%",
                f"   - Max Drawdown (MDD)  : {max_dd:,.0f} VNĐ",
                "-" * 65
            ])

            prompt_lines.extend([
                "\n⚠️ XÁC NHẬN CƠ CHẾ V6.0 KINETIC KELLY:",
                "1. Loại bỏ sai lầm Gấp thếp (Trung bình giá xuống). Ứng dụng Quản trị rủi ro Anti-Martingale: Giảm Vol khi Thua, Bơm Margin khi Thắng.",
                "2. Sử dụng công thức Kelly Criterion đánh giá Tỷ lệ Thắng/Thua thực tế trên 21 phiên. Kelly < 0 lập tức khóa lệnh 0đ.",
                "3. Màng lọc chống Lô Gan: Tự động trảm toàn bộ những mã khuyết góc không thèm về trong 15 ngày."
            ])
            return "\n".join(prompt_lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

# ==============================================================================
# 🖥️ BLOCK 7: GRADIO WEB UI (RENDER READY)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    min_dt_init, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title=Config.VERSION, theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 XSMB QUANT ENGINE {Config.VERSION}")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
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
            
            # --- VŨ KHÍ MỚI: TÁCH RIÊNG BƯỚC TẢI LÊN NÚT TO ĐÙNG ---
            gr.Markdown("---")
            gr.Markdown("### 📥 TẢI DATABASE VỀ MÁY TRỰC TIẾP")
            gr.Markdown("*(Gradio đôi khi bị lỗi cache link ẩn. Bấm nút số 1 để trích xuất file mới nhất, sau đó NÚT TẢI TO ĐÙNG sẽ hiện ra)*")
            with gr.Row():
                btn_prepare_dl = gr.Button("1️⃣ BẤM ĐỂ TRÍCH XUẤT FILE TỪ MÁY CHỦ", variant="primary")
            with gr.Row():
                dl_output = gr.DownloadButton("2️⃣ 📥 BẤM VÀO ĐÂY ĐỂ TẢI FILE XUỐNG", variant="primary", visible=False)
                
            def get_excel_file():
                path = os.path.abspath(Config.DATA_FILE)
                if os.path.exists(path):
                    # Bật cờ cho nút DownloadButton hiện lên cùng với file chuẩn
                    return gr.update(value=path, visible=True)
                return gr.update(visible=False)
                
            btn_prepare_dl.click(fn=get_excel_file, inputs=[], outputs=dl_output)
            
        with gr.Column(visible=False) as col_2:
            with gr.Row():
                pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
            btn_2 = gr.Button("🔍 XUẤT LỆNH GIAO DỊCH CAO CẤP", variant="primary")
            out_2 = gr.Textbox(label="Hồ sơ Lệnh Tác Chiến", lines=25)
            btn_2.click(Auditor.phan_he_2_predict, inputs=[pts_2], outputs=out_2)
            
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

        with gr.Column(visible=False) as col_4:
            with gr.Row():
                t1_4 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value=min_dt_init.strftime('%d/%m/%Y') if min_dt_init else "")
                t2_4 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Dòng Tiền & Max Drawdown", lines=22)
            btn_4.click(Auditor.phan_he_4_range, inputs=[t1_4, t2_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            date_5 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_5 = gr.Button("💾 TRUY XUẤT KẾT QUẢ LOTO TRUYỀN THỐNG", variant="primary")
            out_5 = gr.Textbox(label="Bảng Kết Quả Loto", lines=15)
            btn_5.click(Auditor.phan_he_5_raw, inputs=date_5, outputs=out_5)

        with gr.Column(visible=False) as col_6:
            gr.Markdown("### 🤖 BỘ NÃO AI - QUÉT TOÀN BỘ LỊCH SỬ DB")
            btn_6 = gr.Button("🧬 BẮT ĐẦU QUÉT TOÀN DB", variant="primary")
            out_6 = gr.Textbox(label="Báo cáo Tổng hợp V6.0", lines=25)
            btn_6.click(Auditor.phan_he_6_master_diagnostic_prompt, inputs=[], outputs=out_6)

        def update_visibility(choice):
            return [
                gr.Column(visible=(choice == Config.MENU_OPTIONS[0])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[1])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[2])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[3])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[4])),
                gr.Column(visible=(choice == Config.MENU_OPTIONS[5])),
            ]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6])
    return demo

# ==============================================================================
# 🚀 LAUNCHER CONFIGURATION FOR RENDER
# ==============================================================================
if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
