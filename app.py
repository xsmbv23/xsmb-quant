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
import concurrent.futures
from datetime import datetime, timedelta
import traceback
import gradio as gr

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG
# ==============================================================================
class Config:
    VERSION = "V36.26 PRO (AI DIAGNOSTIC LÕI SÂU)" 
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    BACKUP_PREFIX = "Ket_Qua_Loto27_Backup_" 
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    MODES = [
        "🚀 Giao Dịch T-7 ĐỘNG LƯỢNG TỐI ƯU (Cải Tiến Quant V36.2)",
        "Giao Dịch Toàn Bộ T-7 (Chuẩn Gốc)",
        "Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
        "Chỉ Giao Dịch SỐ KHUYẾT (Không Rơi/Đảo)",
    ]
    MENU_OPTIONS = [
        "🔄 1. ĐỒNG BỘ & CẬP NHẬT DỮ LIỆU",
        "🎯 2. KHUYẾN NGHỊ LỆNH",
        "🔍 3. KIỂM TOÁN CHUYÊN SÂU",
        "📈 4. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 5. KẾT QUẢ LOTO THEO NGÀY",
        "🤖 6. CHẨN ĐOÁN AI (HỘP ĐEN PROMPT)"
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
# 🕸️ BLOCK 3: CRAWLER ĐA TÊN MIỀN
# ==============================================================================
class Crawler:
    @staticmethod
    def _fetch_single_domain(domain):
        url = f"https://{domain}/so-ket-qua-truyen-thong/300"
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if res.status_code == 200:
                html_text = res.text
                parts = re.split(r'(\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b)', html_text)
                parsed_data = {}
                for i in range(1, len(parts)-1, 2):
                    res_date = Utils.chuan_hoa_ngay(parts[i])
                    if res_date:
                        clean_text = re.sub(r'<[^>]+>', ' ', html.unescape(parts[i+1]))
                        nums = re.findall(r'\b\d{2,}\b', clean_text)
                        if len(nums) >= 27:
                            parsed_data[res_date[1]] = " ".join([x[-2:] for x in nums[:27]])
                if len(parsed_data) > 10: 
                    return True, parsed_data, domain
        except Exception: pass
        return False, {}, domain

    @staticmethod
    def fetch_ketqua_radar():
        if not HAS_REQUESTS: return False, {}, "Thiếu thư viện 'requests'"
        base_domains = ["ketqua.net", "ketqua.vn", "ketquaxoso.net"]
        numeric_domains = [f"ketqua{i}.net" for i in range(16, 51)] + [f"ketqua{i}.net" for i in range(1, 16)]
        domains_to_scan = numeric_domains + base_domains
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_domain = {executor.submit(Crawler._fetch_single_domain, dom): dom for dom in domains_to_scan}
            for future in concurrent.futures.as_completed(future_to_domain):
                success, data, domain_name = future.result()
                if success: return True, data, f"Quét thành công {len(data)} ngày từ [{domain_name}]"
        return False, {}, "Toàn bộ mạng lưới Ketqua đã sập."

# ==============================================================================
# 💾 BLOCK 4: DATABASE & AUTO-BACKUP
# ==============================================================================
class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        if not os.path.exists(Config.DATA_FILE):
            backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
            if backups: shutil.copy(backups[0], Config.DATA_FILE)
            else:
                pd.DataFrame(columns=["Ngày", "Kết Quả Loto"]).to_excel(Config.DATA_FILE, index=False)
                return db, "⚠️ Tệp dữ liệu rỗng."
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
            return db, f"🟢 ĐỒNG BỘ: {len(db)} PHIÊN."
        except Exception as e: 
            backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
            if backups:
                shutil.copy(backups[0], Config.DATA_FILE)
                return DatabaseManager.load_db() 
            return db, f"🛑 LỖI ĐỌC:\n{traceback.format_exc()}"

    @staticmethod
    def rewrite_clean_db(db):
        all_rows = []
        for d_str, info in db.items():
            all_rows.append({"Ngày": d_str, "Kết Quả Loto": info["raw_str"], "date_parse": info["date_obj"]})
        if all_rows:
            df_final = pd.DataFrame(all_rows)
            df_final = df_final.sort_values(by='date_parse', ascending=False).drop(columns=['date_parse'])
            if os.path.exists(Config.DATA_FILE):
                timestamp = Utils.get_vn_time().strftime("%Y%m%d_%H%M%S")
                shutil.copy(Config.DATA_FILE, f"{Config.BACKUP_PREFIX}{timestamp}.bak")
                existing_backups = sorted(glob.glob(Config.BACKUP_PREFIX + "*.bak"), reverse=True)
                for old_bak in existing_backups[3:]: os.remove(old_bak)
            df_final.to_excel(Config.DATA_FILE, index=False)

    @staticmethod
    def save_manual_data(date_str, numbers_str):
        res_date = Utils.chuan_hoa_ngay(date_str)
        if not res_date: return "🛑 LỖI NHẬP LIỆU: Ngày không đúng định dạng."
        dt_obj, std_date = res_date
        nums = re.findall(r'\d{2}', str(numbers_str))
        if len(nums) < 27: return f"🛑 LỖI NHẬP LIỆU: Chỉ tìm thấy {len(nums)}/27 con số."
        try:
            db, _ = DatabaseManager.load_db()
            db[std_date] = {"date_obj": dt_obj, "prizes_int": [int(x) for x in nums[:27]], "raw_str": " ".join(nums[:27])}
            DatabaseManager.rewrite_clean_db(db)
            return f"✅ NHẬP TAY THÀNH CÔNG: {std_date}!"
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def auto_heal_history():
        db, _ = DatabaseManager.load_db()
        now_vn = Utils.get_vn_time()
        success, parsed_data, msg = Crawler.fetch_ketqua_radar()
        if not success: return f"🛑 LỖI CRAWLER:\n{msg}"
        healed_count = 0
        for date_str, prizes_str in parsed_data.items():
            res_date = Utils.chuan_hoa_ngay(date_str)
            if res_date:
                dt_obj, std_str = res_date
                if dt_obj.date() > now_vn.date(): continue
                if dt_obj.date() == now_vn.date() and now_vn.hour < 19: continue
                if std_str not in db:
                    nums = re.findall(r'\d{2}', prizes_str)
                    if len(nums) >= 27:
                        db[std_str] = {"date_obj": dt_obj, "prizes_int": [int(x) for x in nums[:27]], "raw_str": " ".join(nums[:27])}
                        healed_count += 1
        if healed_count > 0 or len(db) > 0:
            try:
                DatabaseManager.rewrite_clean_db(db)
                if healed_count > 0: return f"✅ AUTO-HEAL: {msg}. Bổ sung {healed_count} phiên bị mất."
                else: return "✅ AUTO-HEAL: Dữ liệu liền mạch."
            except Exception as e: return f"🛑 LỖI GHI FILE:\n{traceback.format_exc()}"
        return "✅ AUTO-HEAL: Dữ liệu đã liền mạch."

    @staticmethod
    def get_boundaries(db):
        now_vn = Utils.get_vn_time()
        today = datetime(now_vn.year, now_vn.month, now_vn.day)
        default_next = today + timedelta(days=1) if now_vn.hour >= 19 else today
        if not db: return None, None, default_next
        all_dates = [info["date_obj"] for info in db.values()]
        return min(all_dates), max(all_dates), max(all_dates) + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 5: QUANT ENGINE (AUTONOMOUS TRACE TRUY VẾT TOÁN HỌC)
# ==============================================================================
class QuantEngine:
    @staticmethod
    def get_signal(target_dt, db, mode):
        trace_log = []
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        if not past_dates: return None, "[THIẾU DỮ LIỆU]", "Không có lịch sử."

        target_weekday = target_dt.weekday()
        t_minus_7_dt = None
        for p_dt in past_dates:
            if p_dt.weekday() == target_weekday and (target_dt - p_dt).days >= 7:
                t_minus_7_dt = p_dt
                break
                
        if t_minus_7_dt is None: 
            return None, "[THIẾU DỮ LIỆU T-7 ĐỒNG PHA]", "Không tìm thấy ngày cùng Thứ trong quá khứ."
        
        str_t7 = t_minus_7_dt.strftime("%d/%m/%Y")
        prizes_t7 = db[str_t7]["prizes_int"]
        dan_t7 = set(prizes_t7)
        trace_log.append(f"[T-7 Log] Ngày cần đánh: {target_dt.strftime('%d/%m/%Y')} (Thứ {target_weekday+1}). Lùi quá khứ tìm thấy T-7 hợp lệ tại ngày {str_t7}.")

        t_minus_1 = past_dates[0]
        str_t1 = t_minus_1.strftime("%d/%m/%Y")
        trace_log.append(f"[T-1 Log] Phiên quay thưởng gần nhất (T-1) được xác định là: {str_t1}.")

        if mode == Config.MODES[0]:  
            recent_3d = set()
            for p_dt in past_dates[:3]:
                str_p = p_dt.strftime("%d/%m/%Y")
                recent_3d.update(db[str_p]["prizes_int"])
            dan_opt = [x for x in dan_t7 if prizes_t7.count(x) >= 2 or x in recent_3d]
            return sorted(list(dan_opt)), "OK", "\n".join(trace_log)
            
        elif mode in [Config.MODES[2], Config.MODES[3]]: 
            kq_t1 = set(db[str_t1]["prizes_int"])
            tinh_hoa = set()
            for x in dan_t7:
                lon = (x % 10) * 10 + (x // 10)
                if x in kq_t1 or lon in kq_t1: tinh_hoa.add(x)
            
            if mode == Config.MODES[2]: return sorted(list(tinh_hoa)), "OK", "\n".join(trace_log)
            else: return sorted(list(dan_t7 - tinh_hoa)), "OK", "\n".join(trace_log)
        else: return sorted(list(dan_t7)), "OK", "\n".join(trace_log)

    @staticmethod
    def get_mm_multiplier(target_dt, db, mode):
        streak = 0
        trace_log = []
        past_dates = sorted([info["date_obj"] for info in db.values() if info["date_obj"] < target_dt], reverse=True)
        
        for curr_dt in past_dates[:40]: 
            str_curr = curr_dt.strftime("%d/%m/%Y")
            dan, _, _ = QuantEngine.get_signal(curr_dt, db, mode)
            if dan is not None and len(dan) > 0:
                nhay = sum(db[str_curr]["prizes_int"].count(x) for x in dan)
                cost = len(dan) * Config.COST_PER_POINT
                rev = nhay * Config.WIN_PER_NHAY
                if rev - cost > 0:
                    trace_log.append(f"[MM Log] Gặp ngày WIN ({str_curr}). Cắt đứt đếm chuỗi.")
                    break 
                else:
                    streak += 1
                    trace_log.append(f"[MM Log] Ngày {str_curr} THUA -> Chuỗi = {streak}.")
                    if streak >= 4:
                        trace_log.append("[MM Log] Đạt max 4 ngày thua. Kích hoạt Đứng Ngoài.")
                        break 
                        
        if streak == 0: mult = 1.0   
        elif streak == 1: mult = 0.8 
        elif streak == 2: mult = 0.5 
        elif streak == 3: mult = 0.3 
        else: mult = 0.0             
        
        trace_log.append(f"[MM Result] Tổng chuỗi thua = {streak} -> Hệ số vốn = {mult}")
        return mult, "\n".join(trace_log)

# ==============================================================================
# 📊 BLOCK 6: AUDIT, REPORTING & AI DIAGNOSTICS (V36.26)
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = "ℹ️ Chế độ Offline. Chưa kích hoạt Crawler."
        if auto_crawl: crawl_msg = DatabaseManager.auto_heal_history()
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        latest_str = latest_dt.strftime('%d/%m/%Y') if latest_dt else "⚠️ CHƯA CÓ DỮ LIỆU NÀO TRONG DB!"
        lines = [
            "📑 BÁO CÁO ĐỒNG BỘ CƠ SỞ DỮ LIỆU",
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
    def phan_he_2_predict(pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            _, _, next_dt = DatabaseManager.get_boundaries(db)
            is_valid, err_msg = Utils.check_valid_number(pts_per_code_base, "Vốn Cơ sở")
            if not is_valid: return err_msg
            base_pts = float(pts_per_code_base)
            multiplier, mm_trace = QuantEngine.get_mm_multiplier(next_dt, db, mode)
            adjusted_pts = int(base_pts * multiplier)
            
            dan, msg, sig_trace = QuantEngine.get_signal(next_dt, db, mode)
            lines = [
                "📑 BÁO CÁO KHUYẾN NGHỊ GIAO DỊCH",
                "=======================================================",
                f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}",
                f"🎚️ CHIẾN LƯỢC ÁP DỤNG: {mode}", ""
            ]
            if dan is None:
                lines.extend([f"🛑 CẢNH BÁO: {msg}.", "👉 TRUY VẾT LỖI:", sig_trace])
                return "\n".join(lines)
                
            so_luong_lo = len(dan)
            if so_luong_lo > 0:
                dan_str = " ".join([f"{x:02d}" for x in dan])
                if adjusted_pts == 0:
                    lines.extend([
                        f"📋 DANH MỤC MÃ SỐ ({so_luong_lo} MÃ):", f" [ {dan_str} ]",
                        "-------------------------------------------------------",
                        "🛑 LỆNH ĐỨNG NGOÀI: Hệ thống đang trong chu kỳ sụt giảm vốn."
                    ])
                else:
                    von_ngay = so_luong_lo * adjusted_pts * Config.COST_PER_POINT
                    diem_hoa_von = math.ceil(von_ngay / (adjusted_pts * Config.WIN_PER_NHAY))
                    lines.extend([
                        f"📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN ({so_luong_lo} MÃ):", f" [ {dan_str} ]",
                        "-------------------------------------------------------",
                        f" • Phân bổ : {adjusted_pts} điểm/mã (Hệ số x{multiplier}) | 💰 TỔNG VỐN: {von_ngay:,.0f} VND",
                        f"💡 MỤC TIÊU HÒA VỐN   : Cần tối thiểu {diem_hoa_von} lượt trúng."
                    ])
            else: lines.append("📋 👉 🚫 [KHÔNG CÓ TÍN HIỆU KHẢ THI]")
            lines.extend(["\n--- BẢN GHI TRUY VẾT TOÁN HỌC (TRACE LOG) ---", sig_trace, mm_trace])
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_router(audit_type, date_raw, month_raw, mode, pts_per_code_base):
        if audit_type == "Kiểm toán 1 Ngày (Kèm Log Truy Vết)": return Auditor.phan_he_3_single(date_raw, pts_per_code_base)
        else: return Auditor.phan_he_3_monthly_detail(month_raw, mode, pts_per_code_base)

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
                "📑 BÁO CÁO KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN (CÓ TRACE LOG)",
                "========================================================================",
                f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str}",
                "========================================================================"
            ]
            
            for i, mode in enumerate(Config.MODES):
                dan, msg, sig_trace = QuantEngine.get_signal(d_obj, db, mode)
                mode_name = f"CHIẾN LƯỢC {i+1}"
                if dan is None: 
                    lines.extend([f"🛑 [{mode_name}] {mode}: Thiếu dữ liệu {msg}", f"   > Lý do truy vết: {sig_trace}"])
                else: 
                    mult, mm_trace = QuantEngine.get_mm_multiplier(d_obj, db, mode)
                    sl = len(dan)
                    if sl == 0:
                        lines.append(f"🛑 [{mode_name}] 👉 KHÔNG CÓ MÃ ĐẠT CHUẨN")
                    else:
                        adjusted_pts = int(float(pts_per_code_base) * mult)
                        nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in dan)
                        if adjusted_pts == 0:
                            lines.extend([
                                f"📌 [{mode_name}]",
                                f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in dan]),
                                f" • Đạt {nhay} lượt. Điểm đánh: 0 (Đứt Cầu Đứng Ngoài)",
                                f" 👉 PnL RÒNG: 0 VNĐ (Chế độ Backtest)\n"
                            ])
                        else:
                            chi = sl * adjusted_pts * Config.COST_PER_POINT
                            thu = nhay * adjusted_pts * Config.WIN_PER_NHAY
                            lai = thu - chi
                            st = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                            lines.extend([
                                f"📌 [{mode_name}]",
                                f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in dan]),
                                f" • Đạt {nhay} lượt. Phân bổ: {adjusted_pts}đ | Vốn: {chi/1000:,.0f}k | Thu: {thu/1000:,.0f}k",
                                f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})\n"
                            ])
                    lines.extend(["   --- MẬT LỆNH BỘ NÃO AI (LOG TRUY VẾT TOÁN HỌC) ---", "   " + sig_trace.replace("\n", "\n   "), "   " + mm_trace.replace("\n", "\n   ")])
                lines.append("------------------------------------------------------------------------")
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_3_monthly_detail(month_raw, mode, pts_per_code_base):
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
                f"🎚️ CHIẾN LƯỢC: {mode}",
                "=============================================================================================================================",
                f"{'NGÀY':<6} | {'MÃ ĐÁNH':<26} | {'ĐIỂM':<4} | {'VỐN (k)':<8} | {'THU (k)':<8} | {'LÃI/LỖ (k)':<11} | {'ROI':<8}",
                "-----------------------------------------------------------------------------------------------------------------------------"
            ]
            curr = start_dt
            tot_von, tot_thu, tot_lai = 0, 0, 0
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                short_date = curr.strftime("%d/%m")
                if ngay_str in db:
                    dan, msg, _ = QuantEngine.get_signal(curr, db, mode)
                    multiplier, _ = QuantEngine.get_mm_multiplier(curr, db, mode)
                    adjusted_pts = int(base_pts * multiplier)
                    if dan is not None:
                        sl = len(dan)
                        if sl > 0:
                            dan_str = " ".join([f"{x:02d}" for x in dan])
                            if len(dan_str) > 20: dan_str = dan_str[:17] + "..."
                            d_list = f"{sl:>2} mã: {dan_str}"
                            if adjusted_pts == 0:
                                lines.append(f"{short_date:<6} | {d_list:<26} | {0:<4} | {'0':<8} | {'0':<8} | {'[ĐỨNG NGOÀI]':<11} | {'-':<8}")
                            else:
                                von = sl * adjusted_pts * Config.COST_PER_POINT
                                nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in dan)
                                thu = nhay * adjusted_pts * Config.WIN_PER_NHAY
                                lai = thu - von
                                roi = (lai / von * 100) if von > 0 else 0
                                tot_von += von
                                tot_thu += thu
                                tot_lai += lai
                                lines.append(f"{short_date:<6} | {d_list:<26} | {adjusted_pts:<4} | {von/1000:>8,.0f} | {thu/1000:>8,.0f} | {lai/1000:>+11,.0f} | {roi:>+6.1f}%")
                        else: lines.append(f"{short_date:<6} | {'🚫 KHÔNG CÓ TÍN HIỆU':<26} | {'-':<4} | {'-':<8} | {'-':<8} | {'-':<11} | {'-':<8}")
                    else: lines.append(f"{short_date:<6} | ⚠️ Thiếu dữ liệu T-7/T-1{'':<4} | {'-':<4} | {'-':<8} | {'-':<8} | {'-':<11} | {'-':<8}")
                else: lines.append(f"{short_date:<6} | ⚪ Chưa có dữ liệu trên DB{'':<1} | {'-':<4} | {'-':<8} | {'-':<8} | {'-':<11} | {'-':<8}")
                curr += timedelta(days=1)
                
            tot_roi = (tot_lai / tot_von * 100) if tot_von > 0 else 0
            lines.extend([
                "=============================================================================================================================",
                f"📝 TỔNG KẾT THÁNG {thang:02d}/{nam}:",
                f"💰 TỔNG VỐN THỰC ĐÁNH : {tot_von:,.0f} VNĐ",
                f"💵 TỔNG DOANH THU     : {tot_thu:,.0f} VNĐ",
                f"🚀 LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ",
                f"📈 TỶ SUẤT R.O.I      : {tot_roi:+.2f} %"
            ])
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_4_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base, mode):
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
                f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (CHIẾN LƯỢC: {mode})",
                "==================================================================================================================="
            ]
            curr = start_dt
            daily_records = []
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                if ngay_str in db:
                    dan, _, _ = QuantEngine.get_signal(curr, db, mode)
                    multiplier, _ = QuantEngine.get_mm_multiplier(curr, db, mode)
                    adjusted_pts = int(base_pts * multiplier)
                    if dan is not None and len(dan) > 0 and adjusted_pts > 0:
                        sl = len(dan)
                        von = sl * adjusted_pts * Config.COST_PER_POINT
                        nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in dan)
                        thuong = nhay * adjusted_pts * Config.WIN_PER_NHAY
                        lai = thuong - von
                        daily_records.append({
                            "dt": curr, "year": curr.year, "month_str": curr.strftime("%m/%Y"),
                            "codes": sl, "chi": von, "lai": lai,
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
            lines.extend(["===================================================================================================================", f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN | Win: {df_rec['win'].sum()} - Loss: {df_rec['loss'].sum()}):", f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ", f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ", f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %", f"• SỤT GIẢM VỐN LỚN NHẤT (Max Drawdown) : {max_dd:,.0f} VNĐ", "==================================================================================================================="])
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
    def phan_he_6_diagnostic_prompt(mode):
        try:
            db, msg = DatabaseManager.load_db()
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if not min_dt or not max_dt: return "🛑 HỆ THỐNG RỖNG: Không thể chạy chẩn đoán do chưa có dữ liệu."
            
            end_dt = max_dt
            start_dt = end_dt - timedelta(days=30)
            curr = start_dt
            
            wins, losses, total_chi, total_thu = 0, 0, 0, 0
            daily_pnls = []
            win_pnls = []
            loss_pnls = []
            total_codes = 0
            days_with_codes = 0
            
            multipliers_count = {1.0: 0, 0.8: 0, 0.5: 0, 0.3: 0, 0.0: 0}
            weekday_stats = {i: {'wins': 0, 'total': 0} for i in range(7)}
            current_losing_streak = 0
            max_losing_streak = 0
            
            day_names = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"]
            
            while curr <= end_dt:
                str_dt = curr.strftime("%d/%m/%Y")
                if str_dt in db:
                    dan, _, _ = QuantEngine.get_signal(curr, db, mode)
                    multiplier, _ = QuantEngine.get_mm_multiplier(curr, db, mode)
                    
                    mult_key = round(multiplier, 1)
                    if mult_key in multipliers_count: multipliers_count[mult_key] += 1
                    
                    pts = int(10 * multiplier)
                    wd = curr.weekday()
                    
                    if dan is not None and len(dan) > 0:
                        total_codes += len(dan)
                        days_with_codes += 1
                        
                        if pts > 0:
                            nhay = sum(db[str_dt]["prizes_int"].count(x) for x in dan)
                            chi = len(dan) * pts * Config.COST_PER_POINT
                            thu = nhay * pts * Config.WIN_PER_NHAY
                            lai = thu - chi
                            
                            total_chi += chi
                            total_thu += thu
                            daily_pnls.append(lai)
                            weekday_stats[wd]['total'] += 1
                            
                            if lai > 0:
                                wins += 1
                                win_pnls.append(lai)
                                weekday_stats[wd]['wins'] += 1
                                current_losing_streak = 0
                            else:
                                losses += 1
                                loss_pnls.append(lai)
                                current_losing_streak += 1
                                if current_losing_streak > max_losing_streak: max_losing_streak = current_losing_streak
                        else:
                            # Đứng ngoài nhưng vẫn tính nháp để bẻ cầu
                            nhay = sum(db[str_dt]["prizes_int"].count(x) for x in dan)
                            paper_chi = len(dan) * 10 * Config.COST_PER_POINT
                            paper_thu = nhay * 10 * Config.WIN_PER_NHAY
                            if paper_thu > paper_chi:
                                current_losing_streak = 0
                            else:
                                current_losing_streak += 1
                                if current_losing_streak > max_losing_streak: max_losing_streak = current_losing_streak
                curr += timedelta(days=1)
                
            roi = ((total_thu - total_chi) / total_chi * 100) if total_chi > 0 else 0
            profit_factor = (total_thu / total_chi) if total_chi > 0 else 0
            avg_win = (sum(win_pnls) / len(win_pnls)) if win_pnls else 0
            avg_loss = (sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0
            avg_codes = (total_codes / days_with_codes) if days_with_codes > 0 else 0
            
            # Tính Max Drawdown
            cum_pnl = np.cumsum(daily_pnls) if daily_pnls else []
            peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else []
            drawdowns = cum_pnl - peak if len(cum_pnl) > 0 else []
            max_dd = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
            
            # Chuẩn bị chuỗi ngày tuần
            wd_str = ""
            for i in range(7):
                t = weekday_stats[i]['total']
                w = weekday_stats[i]['wins']
                if t > 0:
                    wd_str += f"\n   - {day_names[i]}: Thắng {w}/{t} ({w/t*100:.1f}%)"
                    
            prompt = f"""[HỒ SƠ SINH HỌC QUANT LÕI - VUI LÒNG COPY GỬI CHO GEMINI TỰ PHẢN BIỆN]

Lệnh cho Gemini: Phân tích sâu Mật lệnh này và nâng cấp thuật toán.

1. BẢN CHẤT HỆ THỐNG: {Config.VERSION} (Chiến lược: {mode})
2. QUÉT TRONG 30 NGÀY QUA ({start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')})

🔬 [A] CHỈ SỐ RỦI RO & HIỆU SUẤT:
- Tỷ suất lợi nhuận (ROI): {roi:.2f}%
- Max Drawdown (Sụt vốn tối đa): {max_dd:,.0f} VNĐ
- Profit Factor (Hệ số LN): {profit_factor:.2f}
- Tỷ lệ Lệnh: Thắng {wins} / Thua {losses} (Tổng thực đánh: {wins + losses})
- Trung bình Lãi/ngày thắng: {avg_win:+,.0f} VNĐ
- Trung bình Lỗ/ngày thua: {avg_loss:+,.0f} VNĐ

🛡️ [B] HIỆU SUẤT BỘ LỌC VỐN ANTI-MARTINGALE:
- Chuỗi thua Max (Losing Streak): {max_losing_streak} ngày.
- Hoạt động Vốn: 100% ({multipliers_count.get(1.0,0)} ngày) | 80% ({multipliers_count.get(0.8,0)} ngày) | 50% ({multipliers_count.get(0.5,0)} ngày) | 30% ({multipliers_count.get(0.3,0)} ngày) | 0% Đứng ngoài ({multipliers_count.get(0.0,0)} ngày)

🧩 [C] ĐỘ NHIỄU DỮ LIỆU & CHU KỲ:
- Khối lượng mã trung bình: {avg_codes:.1f} mã/ngày
- Tỷ lệ Thắng theo ngày trong tuần: {wd_str}

⚠️ YÊU CẦU DÀNH CHO GEMINI:
Bằng nghiệp vụ Quant: Phân tích Max Drawdown và Tỷ lệ thắng theo ngày. Nếu bộ lọc quá lỏng (mã/ngày cao) hoặc có ngày nào đó tỷ lệ thua > 80%, hãy tự viết đè lại thuật toán T-7 để cắt đuôi rủi ro. Xuất mã Python mới."""
            return prompt
        except Exception as e: return f"🛑 LỖI TRUY VẾT:\n{traceback.format_exc()}"

def create_ui():
    db_init, _ = DatabaseManager.load_db()
    _, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title=Config.VERSION, theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 XSMB QUANT {Config.VERSION}")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (QUÉT NHANH ĐA LUỒNG)", variant="primary")
            
            gr.Markdown("---")
            gr.Markdown("✍️ **HOẶC NHẬP KẾT QUẢ BẰNG TAY (DÀNH CHO NGÀY CRAWLER BỊ CHẶN)**")
            with gr.Row():
                manual_date = gr.Textbox(label="Ngày (DD/MM/YYYY)", placeholder="Ví dụ: 01/08/2026")
                manual_numbers = gr.Textbox(label="Chuỗi 27 số (54 ký tự liền nhau)", placeholder="Copy/Paste thẳng chuỗi số vào đây...")
            btn_manual_save = gr.Button("📥 LƯU DỮ LIỆU VÀO MÁY CHỦ", variant="primary")
            gr.Markdown("---")

            out_1 = gr.Textbox(label="Biên bản Hệ thống", lines=8)
            title_2 = gr.Markdown(f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt_init.strftime('%d/%m/%Y')}")
            
        with gr.Column(visible=False) as col_2:
            with gr.Row():
                pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
                mode_2 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_2 = gr.Button("🔍 XUẤT KHUYẾN NGHỊ GIAO DỊCH", variant="primary")
            out_2 = gr.Textbox(label="Hồ sơ Giao dịch", lines=16)
            btn_2.click(Auditor.phan_he_2_predict, inputs=[pts_2, mode_2], outputs=out_2)
            
        with gr.Column(visible=False) as col_3:
            gr.Markdown("### 🔍 MODULE KIỂM TOÁN CHUYÊN SÂU & TRUY VẾT")
            audit_type = gr.Radio(choices=["Kiểm toán 1 Ngày (Kèm Log Truy Vết)", "Kiểm toán Cả Tháng (Chi tiết)"], value="Kiểm toán 1 Ngày (Kèm Log Truy Vết)", label="Loại Kiểm toán")
            
            with gr.Row(visible=True) as row_audit_day:
                date_3 = gr.Textbox(label="Ngày Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            
            with gr.Row(visible=False) as row_audit_month:
                month_3 = gr.Textbox(label="Tháng Truy xuất (MM/YYYY)", value=latest_dt_init.strftime('%m/%Y') if latest_dt_init else "")
                mode_3 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
                
            pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_3 = gr.Button("📡 THỰC THI KIỂM TOÁN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Kiểm toán", lines=24)
            
            def toggle_audit(choice):
                return gr.update(visible=choice=="Kiểm toán 1 Ngày (Kèm Log Truy Vết)"), gr.update(visible=choice=="Kiểm toán Cả Tháng (Chi tiết)")
            
            audit_type.change(fn=toggle_audit, inputs=audit_type, outputs=[row_audit_day, row_audit_month])
            btn_3.click(Auditor.phan_he_3_router, inputs=[audit_type, date_3, month_3, mode_3, pts_3], outputs=out_3)

        with gr.Column(visible=False) as col_4:
            with gr.Row():
                t1_4 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
                t2_4 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_4 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_4 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền & Max Drawdown", lines=22)
            btn_4.click(Auditor.phan_he_4_range, inputs=[t1_4, t2_4, pts_4, mode_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            date_5 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_5 = gr.Button("💾 TRUY XUẤT KẾT QUẢ LOTO", variant="primary")
            out_5 = gr.Textbox(label="Biên Bản Kết Quả", lines=10)
            btn_5.click(Auditor.phan_he_5_raw, inputs=date_5, outputs=out_5)

        with gr.Column(visible=False) as col_6:
            gr.Markdown("### 🤖 BỘ NÃO AI - CHẨN ĐOÁN & NÂNG CẤP LÕI SÂU")
            mode_6 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chọn Chiến lược muốn Chẩn đoán")
            btn_6 = gr.Button("🧬 TRÍCH XUẤT HỒ SƠ SINH HỌC (TẠO PROMPT)", variant="primary")
            out_6 = gr.Textbox(label="Mật lệnh Prompt (Copy toàn bộ Text dưới đây gửi cho AI để tự vá lỗi)", lines=22)
            btn_6.click(Auditor.phan_he_6_diagnostic_prompt, inputs=[mode_6], outputs=out_6)

        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])
        btn_manual_save.click(Auditor.process_manual_input, inputs=[manual_date, manual_numbers], outputs=[out_1, title_2])

        def update_visibility(choice):
            return [
                gr.update(visible=(choice == Config.MENU_OPTIONS[0])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[1])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[2])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[3])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[4])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[5])),
            ]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6])
    return demo

if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
