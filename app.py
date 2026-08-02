import os
import sys
import pandas as pd
import numpy as np
import math
import calendar
import re
import html
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
    VERSION = "V36.14 PRO ALGO (BỌC THÉP DATABASE & NHẬP LIỆU TEXTBOX)"
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
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
        "🛡️ 3. QUẢN TRỊ RỦI RO",
        "🔍 4. KIỂM TOÁN ĐƠN PHIÊN",
        "📈 5. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 6. DỮ LIỆU THÔ"
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
        if pd.isna(ngay_raw) or not str(ngay_raw).strip(): return None
        try:
            match = re.search(r'\d{1,2}[-/.]\d{1,2}[-/.]\d{4}', str(ngay_raw))
            if not match: return None
            s = match.group().replace("-", "/").replace(".", "/")
            parts = s.split("/")
            if len(parts) < 3: return None
            d, m, y = parts[0], parts[1], parts[2]
            if len(d) == 1: d = "0" + d
            if len(m) == 1: m = "0" + m
            str_chuan = f"{d}/{m}/{y}"
            dt_obj = datetime.strptime(str_chuan, "%d/%m/%Y")
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
# 🕸️ BLOCK 3: CRAWLER
# ==============================================================================
class Crawler:
    @staticmethod
    def extract_date(html_text):
        d_m = re.search(r'\b(?:mb_date|tit-mien)\b[^>]*>(.*?)</', html_text, re.IGNORECASE | re.DOTALL)
        if d_m:
            clean = re.sub(r'<[^>]+>', ' ', html.unescape(d_m.group(1)))
            m = re.search(r'\d{1,2}[-/.]\d{1,2}[-/.]\d{4}', clean)
            if m: return m.group().replace('-', '/').replace('.', '/')
        return None

    @staticmethod
    def extract_numbers(html_text):
        blocks = re.findall(r'\b(?:v-giai|day-so)\b[^>]*>(.*?)</', html_text, re.IGNORECASE | re.DOTALL)
        numbers = []
        for b in blocks:
            clean = re.sub(r'<[^>]+>', ' ', html.unescape(b))
            digits = re.findall(r'\d+', clean)
            for d in digits:
                if len(d) >= 2: numbers.append(d[-2:])
        return numbers

    @staticmethod
    def fetch_source_1(target_dt):
        d_str_url = target_dt.strftime('%d-%m-%Y') if target_dt else ""
        url = f"https://xoso.com.vn/xsmb-{d_str_url}.html" if target_dt else "https://xoso.com.vn/xsmb.html"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        if res.status_code == 200:
            date_str = Crawler.extract_date(res.text)
            if not date_str: return False, None, "Dữ liệu trống (Không có ngày)"
            numbers = Crawler.extract_numbers(res.text)
            if len(numbers) >= 27: return True, (date_str, " ".join(numbers[:27])), "xoso.com.vn"
            return False, None, f"Dữ liệu trống (Thiếu giải, chỉ có {len(numbers)})"
        return False, None, f"HTTP {res.status_code}"

    @staticmethod
    def fetch_source_2(target_dt):
        d_str_url = target_dt.strftime('%d-%m-%Y') if target_dt else ""
        url = f"https://kqxs.vn/mien-bac/ngay-{d_str_url}" if target_dt else "https://kqxs.vn/mien-bac"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        if res.status_code == 200:
            date_str = Crawler.extract_date(res.text)
            if not date_str: return False, None, "Dữ liệu trống (Không có ngày)"
            numbers = Crawler.extract_numbers(res.text)
            if len(numbers) >= 27: return True, (date_str, " ".join(numbers[:27])), "kqxs.vn"
            return False, None, f"Dữ liệu trống (Thiếu giải, chỉ có {len(numbers)})"
        return False, None, f"HTTP {res.status_code}"

    @staticmethod
    def fetch_by_date(target_dt=None):
        if not HAS_REQUESTS: return False, None, "Thiếu thư viện 'requests'"
        logs = []
        try:
            s1, res1, msg1 = Crawler.fetch_source_1(target_dt)
            if s1: return True, res1, msg1
            logs.append(f"Src1: {msg1}")
        except Exception as e: logs.append(f"Src1 Lỗi: {str(e)[:15]}")
            
        try:
            s2, res2, msg2 = Crawler.fetch_source_2(target_dt)
            if s2: return True, res2, msg2
            logs.append(f"Src2: {msg2}")
        except Exception as e: logs.append(f"Src2 Lỗi: {str(e)[:15]}")
            
        return False, None, " | ".join(logs)

# ==============================================================================
# 💾 BLOCK 4: AUTO-HEAL & MANUAL DATABASE
# ==============================================================================
class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        # Bảo vệ lỗi file rỗng 0 bytes
        if not os.path.exists(Config.DATA_FILE) or os.path.getsize(Config.DATA_FILE) == 0:
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
                    db[ngay_str] = {"date_obj": dt_obj, "prizes_int": loto_list[:27]}
            return db, f"🟢 ĐỒNG BỘ: {len(db)} PHIÊN."
        except Exception as e: return db, f"🛑 LỖI ĐỌC: {e}"

    @staticmethod
    def auto_heal_history():
        db, _ = DatabaseManager.load_db()
        now_vn = Utils.get_vn_time()
        if now_vn.hour < 19: max_check_dt = now_vn - timedelta(days=1)
        else: max_check_dt = now_vn
            
        new_rows, healed_count, error_logs = [], 0, []
        for i in range(15):
            check_dt = max_check_dt - timedelta(days=i)
            str_check = check_dt.strftime("%d/%m/%Y")
            if str_check not in db:
                success, res, src_msg = Crawler.fetch_by_date(check_dt)
                if success:
                    d_str, loto_27 = res
                    res_date = Utils.chuan_hoa_ngay(d_str)
                    if res_date:
                        _, std_str = res_date
                        if std_str not in db:
                            new_rows.append({"Ngày": std_str, "Kết Quả Loto": loto_27})
                            db[std_str] = True
                            healed_count += 1
                else: error_logs.append(f"[{str_check}] {src_msg}")

        if new_rows:
            df_new = pd.DataFrame(new_rows)
            try:
                if os.path.exists(Config.DATA_FILE) and os.path.getsize(Config.DATA_FILE) > 0:
                    df_old = pd.read_excel(Config.DATA_FILE, dtype=str)
                    df_final = pd.concat([df_new, df_old], ignore_index=True)
                else: df_final = df_new
            except: df_final = df_new
            df_final.to_excel(Config.DATA_FILE, index=False)
            return f"🛠️ AUTO-HEAL: Vá thành công {healed_count} phiên bị mất."
        
        if error_logs and len(db) == 0: return f"🛑 AUTO-HEAL LỖI: {error_logs[0]}"
        return "✅ AUTO-HEAL: Dữ liệu 15 ngày qua liền mạch."

    @staticmethod
    def get_boundaries(db):
        now_vn = Utils.get_vn_time()
        if not db:
            today = datetime(now_vn.year, now_vn.month, now_vn.day)
            if now_vn.hour >= 19: return today, today, today + timedelta(days=1)
            else: return today - timedelta(days=1), today - timedelta(days=1), today
        all_dates = [info["date_obj"] for info in db.values()]
        max_dt = max(all_dates)
        return min(all_dates), max_dt, max_dt + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 5: QUANT ENGINE
# ==============================================================================
class QuantEngine:
    @staticmethod
    def get_signal(target_dt, db, mode):
        t_minus_7 = target_dt - timedelta(days=7)
        str_t7 = t_minus_7.strftime("%d/%m/%Y")
        if str_t7 not in db: return None, f"[THIẾU DỮ LIỆU T-7 ({str_t7})]"
        prizes_t7 = db[str_t7]["prizes_int"]
        dan_t7 = set(prizes_t7)

        if mode == Config.MODES[0]:  
            recent_3d = set()
            for d in range(1, 4):
                str_p = (target_dt - timedelta(days=d)).strftime("%d/%m/%Y")
                if str_p in db: recent_3d.update(db[str_p]["prizes_int"])
            dan_opt = [x for x in dan_t7 if prizes_t7.count(x) >= 2 or x in recent_3d]
            return sorted(list(dan_opt)), "OK"
        elif mode in [Config.MODES[2], Config.MODES[3]]: 
            t_minus_1 = target_dt - timedelta(days=1)
            str_t1 = t_minus_1.strftime("%d/%m/%Y")
            if str_t1 not in db: return None, f"[THIẾU DỮ LIỆU T-1 ({str_t1})]"
            kq_t1 = set(db[str_t1]["prizes_int"])
            tinh_hoa = set()
            for x in dan_t7:
                lon = (x % 10) * 10 + (x // 10)
                if x in kq_t1 or lon in kq_t1: tinh_hoa.add(x)
            if mode == Config.MODES[2]: return sorted(list(tinh_hoa)), "OK"
            else: return sorted(list(dan_t7 - tinh_hoa)), "OK"
        else: return sorted(list(dan_t7)), "OK"

# ==============================================================================
# 📊 BLOCK 6: AUDIT & REPORTING
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = "ℹ️ Chế độ Offline."
        if auto_crawl: crawl_msg = DatabaseManager.auto_heal_history()
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        
        lines = [
            "📑 [PHÂN HỆ 1] BÁO CÁO: ĐỒNG BỘ CƠ SỞ DỮ LIỆU",
            "=================================================================================",
            f"• Phiên bản hệ thống : {Config.VERSION}",
            f"• Trạng thái Dữ liệu : {msg}",
            f"• Báo cáo Crawler    : {crawl_msg}",
            f"• Phiên cập nhật cuối: 📅 [{latest_dt.strftime('%d/%m/%Y')}]",
            f"• Lịch phân tích tới : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
        ]
        return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"

    @staticmethod
    def phan_he_1_manual_input(ngay_raw, chuoi_so):
        try:
            # 1. Kiểm tra ngày
            res_date = Utils.chuan_hoa_ngay(ngay_raw)
            if not res_date:
                return "🛑 LỖI: Ngày không hợp lệ. Vui lòng nhập định dạng DD/MM/YYYY.", "#### LỖI DỮ LIỆU"
            dt_obj, std_date = res_date

            # 2. Xử lý chuỗi số (Lọc sạch chỉ lấy chữ số)
            chuoi_so = re.sub(r'\D', '', str(chuoi_so))
            if len(chuoi_so) < 54:
                return f"🛑 LỖI: Chuỗi số quá ngắn ({len(chuoi_so)} ký tự). Yêu cầu nhập đúng 54 số liền nhau.", "#### LỖI DỮ LIỆU"
            
            # Cắt thành cặp 2 số, lấy đúng 27 giải
            loto_list = [chuoi_so[i:i+2] for i in range(0, 54, 2)]
            loto_str = " ".join(loto_list)

            # 3. Ép ghi vào Database bất chấp file lỗi
            db, _ = DatabaseManager.load_db()
            if std_date in db:
                return f"⚠️ CẢNH BÁO: Phiên {std_date} đã tồn tại trong Hệ thống. Không ghi đè.", "#### BỎ QUA"

            df_new_row = pd.DataFrame([{"Ngày": std_date, "Kết Quả Loto": loto_str}])
            try:
                if os.path.exists(Config.DATA_FILE) and os.path.getsize(Config.DATA_FILE) > 0:
                    df_old = pd.read_excel(Config.DATA_FILE, dtype=str)
                    df_final = pd.concat([df_new_row, df_old], ignore_index=True)
                else: df_final = df_new_row
            except: df_final = df_new_row
            
            df_final.to_excel(Config.DATA_FILE, index=False)
            
            # 4. Báo cáo
            db_new, msg = DatabaseManager.load_db()
            _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db_new)
            
            lines = [
                "📑 [PHÂN HỆ 1] BÁO CÁO: NẠP DỮ LIỆU BẰNG TAY (TEXTBOX)",
                "=================================================================================",
                f"• Phiên bản hệ thống : {Config.VERSION}",
                f"• Trạng thái Dữ liệu : {msg}",
                f"• Kết quả Nạp tay    : 📥 Đã chèn thành công phiên {std_date}",
                f"   [ {loto_str} ]",
                f"• Phiên cập nhật cuối: 📅 [{latest_dt.strftime('%d/%m/%Y')}]",
                f"• Lịch phân tích tới : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
            ]
            return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"
            
        except Exception as e:
            return f"🛑 LỖI HỆ THỐNG: {traceback.format_exc()}", "#### LỖI"

    @staticmethod
    def phan_he_2_predict(pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            _, _, next_dt = DatabaseManager.get_boundaries(db)
            is_valid, err_msg = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not is_valid: return err_msg
            base_pts = int(float(pts_per_code_base))
            dan, msg = QuantEngine.get_signal(next_dt, db, mode)
            
            lines = [
                "📑 [PHÂN HỆ 2] BÁO CÁO: KHUYẾN NGHỊ GIAO DỊCH KẾ TIẾP",
                "=======================================================",
                f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}",
                f"🎚️ CHIẾN LƯỢC ÁP DỤNG: {mode}", ""
            ]
            if dan is None:
                lines.extend([f"🛑 CẢNH BÁO: {msg}.", "👉 LỜI KHUYÊN: Hãy bấm nút [CẬP NHẬT KẾT QUẢ MỚI] ở Bảng 1 để tự động cào bù dữ liệu T-7!"])
                return "\n".join(lines)
                
            so_luong_lo = len(dan)
            von_ngay = so_luong_lo * base_pts * Config.COST_PER_POINT
            if so_luong_lo > 0:
                dan_str = " ".join([f"{x:02d}" for x in dan])
                lines.extend([
                    f"📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN ({so_luong_lo} MÃ):", f" [ {dan_str} ]",
                    "-------------------------------------------------------",
                    f" • Phân bổ : {base_pts} điểm/mã | 💰 TỔNG VỐN: {von_ngay:,.0f} VND"
                ])
                diem_hoa_von = math.ceil(von_ngay / (base_pts * Config.WIN_PER_NHAY)) if base_pts > 0 else 0
                lines.append(f"💡 MỤC TIÊU HÒA VỐN   : Cần tối thiểu {diem_hoa_von} lượt trúng.")
            else:
                lines.extend([
                    "📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN: 👉 🚫 [KHÔNG CÓ TÍN HIỆU KHẢ THI]",
                    "-------------------------------------------------------",
                    "💰 TỔNG VỐN YÊU CẦU: 0 VND",
                    "💡 HỆ THỐNG KHUYẾN NGHỊ ĐỨNG NGOÀI THỊ TRƯỜNG PHIÊN NÀY."
                ])
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI: {e}"

    @staticmethod
    def phan_he_3_risk(base_pts, sim_size):
        try:
            valid1, err1 = Utils.check_valid_number(base_pts, "Khối lượng")
            valid2, err2 = Utils.check_valid_number(sim_size, "Số lượng Mã")
            if not valid1: return err1
            if not valid2: return err2
            base_pts = int(float(base_pts))
            so_luong_lo = int(float(sim_size))
            von_ngay = so_luong_lo * base_pts * Config.COST_PER_POINT
            lines = [
                "📑 [PHÂN HỆ 3] BÁO CÁO: QUẢN TRỊ RỦI RO & MÔ PHỎNG LỢI NHUẬN",
                "====================================================================",
                f"📊 KỊCH BẢN PHÂN BỔ {so_luong_lo} MÃ - TỔNG VỐN ĐẦU TƯ: {von_ngay:,.0f} VNĐ",
                "--------------------------------------------------------------------",
                " LƯỢT TRÚNG   | DOANH THU KỲ VỌNG | LỢI NHUẬN RÒNG | TRẠNG THÁI",
                "--------------------------------------------------------------------"
            ]
            for nhay in range(0, int(so_luong_lo * 0.7) + 2):
                thuong = nhay * base_pts * Config.WIN_PER_NHAY
                lai = thuong - von_ngay
                status = "🟢 LÃI RÒNG" if lai > 0 else "🔴 THUA LỖ"
                if nhay == 0: status += " (MẤT VỐN)"
                lai_str = f"{lai:+,.0f}" if lai != 0 else "0"
                lines.append(f" Đạt {nhay:>2} lượt  | {thuong:>17,.0f} | {lai_str:>14} | {status}")
            lines.append("====================================================================")
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI: {e}"

    @staticmethod
    def phan_he_4_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            if ngay_str not in db: return f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên giao dịch {ngay_str} chưa được cập nhật."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = int(float(pts_per_code_base))
            
            lines = [
                "📑 [PHÂN HỆ 4] BÁO CÁO: KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN",
                "========================================================================",
                f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str} (Phân bổ: {base_pts}đ/mã)",
                "========================================================================"
            ]
            def calc_str(danh_sach, name):
                sl = len(danh_sach)
                if sl == 0: return [f"🛑 [{name}] 👉 KHÔNG CÓ MÃ ĐẠT CHUẨN"]
                chi = sl * base_pts * Config.COST_PER_POINT
                nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in danh_sach)
                thu = nhay * base_pts * Config.WIN_PER_NHAY
                lai = thu - chi
                st = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                return [
                    f"📌 [{name}]",
                    f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in danh_sach]),
                    f" • Đạt {nhay} lượt. Vốn: {chi:,.0f}đ | Thu: {thu:,.0f}đ",
                    f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})"
                ]

            for i, mode in enumerate(Config.MODES):
                dan, msg = QuantEngine.get_signal(d_obj, db, mode)
                mode_name = f"CHIẾN LƯỢC {i+1}"
                if dan is None: lines.append(f"🛑 [{mode_name}] {mode}: Thiếu dữ liệu {msg}")
                else: lines.extend(calc_str(dan, mode))
                lines.append("------------------------------------------------------------------------")
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI: {e}"

    @staticmethod
    def phan_he_5_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            
            base_pts = int(float(pts_per_code_base))
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if start_dt < min_dt: start_dt = min_dt
            if end_dt > max_dt: end_dt = max_dt
            if start_dt > end_dt: return "🛑 LỖI: Khoảng thời gian tra cứu nằm ngoài Phạm vi Dữ liệu hệ thống."
            
            lines = [
                "📑 [PHÂN HỆ 5] BÁO CÁO: ĐẠI KẾ TOÁN QUÉT CHU KỲ",
                "===================================================================================================================",
                f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (CHIẾN LƯỢC: {mode})",
                "==================================================================================================================="
            ]
            curr = start_dt
            daily_records = []
            
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                if ngay_str in db:
                    dan, msg = QuantEngine.get_signal(curr, db, mode)
                    if dan is not None and len(dan) > 0:
                        sl = len(dan)
                        von = sl * base_pts * Config.COST_PER_POINT
                        nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in dan)
                        thuong = nhay * base_pts * Config.WIN_PER_NHAY
                        lai = thuong - von
                        daily_records.append({
                            "dt": curr, "year": curr.year, "month_str": curr.strftime("%m/%Y"),
                            "codes": sl, "chi": von, "lai": lai,
                            "win": 1 if lai > 0 else 0, "loss": 1 if lai <= 0 else 0,
                        })
                curr += timedelta(days=1)
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO ĐẠT ĐIỀU KIỆN XUẤT LỆNH."
            
            df_rec = pd.DataFrame(daily_records)
            lines.extend([
                "", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG",
                "-------------------------------------------------------------------------------------------------------------------",
                f"{'THÁNG/NĂM':<10} | {'PHIÊN':<7} | {'WIN/LOSS':<10} | {'VỐN ĐẦU TƯ':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}",
                "-------------------------------------------------------------------------------------------------------------------"
            ])
            for m_str, g_m in df_rec.groupby("month_str", sort=False):
                m_chi, m_lai = g_m["chi"].sum(), g_m["lai"].sum()
                m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
                lines.append(f"Tháng {m_str:<5} | {len(g_m):<7} | {g_m['win'].sum()}W/{g_m['loss'].sum()}L | {m_chi:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%")
                
            tot_chi, tot_lai = df_rec["chi"].sum(), df_rec["lai"].sum()
            tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
            
            df_rec['cum_pnl'] = df_rec['lai'].cumsum()
            df_rec['peak'] = df_rec['cum_pnl'].cummax()
            df_rec['drawdown'] = df_rec['cum_pnl'] - df_rec['peak']
            max_dd = df_rec['drawdown'].min()
            
            lines.extend([
                "===================================================================================================================",
                f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN | Win: {df_rec['win'].sum()} - Loss: {df_rec['loss'].sum()}):",
                f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ",
                f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ",
                f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %",
                f"• SỤT GIẢM VỐN LỚN NHẤT (Max Drawdown) : {max_dd:,.0f} VNĐ",
                "==================================================================================================================="
            ])
            return "\n".join(lines)
        except Exception as e:
            return f"🛑 LỖI PHÂN HỆ 5: {traceback.format_exc()}"

    @staticmethod
    def phan_he_6_raw(ngay_raw):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            _, ngay_str = res
            if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại trên hệ thống."
            lo_to_raw = db[ngay_str]["prizes_int"]
            lines = [
                "📑 [PHÂN HỆ 6] BÁO CÁO: TRUY XUẤT RAW DB (DỮ LIỆU THÔ)",
                "=======================================================",
                f"📅 BIÊN BẢN KẾT QUẢ PHIÊN GIAO DỊCH: {ngay_str}",
                "🎰 Danh sách 27 giải ma trận phẳng:"
            ]
            row_str = ""
            for idx, lo in enumerate(lo_to_raw):
                row_str += f"[{lo:02d}] "
                if (idx + 1) % 9 == 0:
                    lines.append(row_str.strip())
                    row_str = ""
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 6: {e}"

# ==============================================================================
# 🎮 BLOCK 7: GIAO DIỆN NGƯỜI DÙNG (UI LAYER)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    _, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title="XSMB QUANT V36.14 PRO") as demo:
        gr.Markdown("# 🚀 XSMB QUANT V36.14 PRO — CHỐNG LỖI DB & NHẬP LIỆU TEXTBOX")
        gr.Markdown("*(Đã cấu trúc lại bộ quét Regex siêu đẳng. Bổ sung tính năng Paste thẳng chuỗi 54 ký tự xổ số vào ô văn bản để nạp DB nhanh nhất!)*")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (TỰ ĐỘNG CÀO)", variant="primary")
            
            gr.Markdown("### ✍️ HOẶC NHẬP KẾT QUẢ BẰNG TAY (DÀNH CHO NGÀY CRAWLER BỊ TRỐNG)")
            with gr.Row():
                txt_1_date = gr.Textbox(label="Ngày (DD/MM/YYYY)", placeholder="Ví dụ: 01/08/2026", scale=1)
                txt_1_numbers = gr.Textbox(label="Chuỗi 27 số (54 ký tự liền nhau)", placeholder="Copy/Paste thẳng chuỗi số vào đây (VD: 1223273034...)", scale=3)
            btn_1_manual = gr.Button("📥 LƯU DỮ LIỆU VÀO MÁY CHỦ", variant="primary")

            out_1 = gr.Textbox(label="Biên bản Hệ thống", lines=9)
            title_2 = gr.Markdown(f"#### Dự phóng Tín hiệu cho phiên: {next_predict_dt_init.strftime('%d/%m/%Y')}")
            
        with gr.Column(visible=False) as col_2:
            with gr.Row():
                pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
                mode_2 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_2 = gr.Button("🔍 XUẤT KHUYẾN NGHỊ GIAO DỊCH", variant="primary")
            out_2 = gr.Textbox(label="Hồ sơ Giao dịch", lines=16)
            btn_2.click(Auditor.phan_he_2_predict, inputs=[pts_2, mode_2], outputs=out_2)
            
        with gr.Column(visible=False) as col_3:
            with gr.Row():
                pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                sim_size = gr.Number(label="Quy mô Danh mục (Số lượng mã)", value=12)
            btn_3 = gr.Button("🧪 KHỞI CHẠY MÔ PHỎNG LỢI NHUẬN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Quản trị Rủi ro", lines=16)
            btn_3.click(Auditor.phan_he_3_risk, inputs=[pts_3, sim_size], outputs=out_3)
            
        with gr.Column(visible=False) as col_4:
            with gr.Row():
                date_4 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y'))
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📡 KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Bóc tách Động lượng (Gồm cả 4 kịch bản)", lines=24)
            btn_4.click(Auditor.phan_he_4_single, inputs=[date_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            with gr.Row():
                t1_5 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
                t2_5 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y'))
                pts_5 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_5 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_5 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_5 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền & Max Drawdown", lines=22)
            btn_5.click(Auditor.phan_he_5_range, inputs=[t1_5, t2_5, pts_5, mode_5], outputs=out_5)

        with gr.Column(visible=False) as col_6:
            date_6 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y'))
            btn_6 = gr.Button("💾 TRUY XUẤT DỮ LIỆU THÔ (RAW DATA)", variant="primary")
            out_6 = gr.Textbox(label="Log Dữ Liệu Máy Chủ", lines=10)
            btn_6.click(Auditor.phan_he_6_raw, inputs=date_6, outputs=out_6)

        # Triggers
        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])
        btn_1_manual.click(Auditor.phan_he_1_manual_input, inputs=[txt_1_date, txt_1_numbers], outputs=[out_1, title_2])

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
