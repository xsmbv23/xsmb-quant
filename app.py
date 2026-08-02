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
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG LÕI V36.1.1
# ==============================================================================
class Config:
    VERSION = "V36.1.2 PRO ALGO (NỀN TẢNG QUANT V36.1.1 & GIAO DIỆN NHẬP THỦ CÔNG)"
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    MODES = [
        "🚀 Giao Dịch T-7 ĐỘNG LƯỢNG TỐI ƯU (Cải Tiến Quant V36.1.1)",
        "Giao Dịch Toàn Bộ T-7 (Chuẩn Gốc)",
        "Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
        "Chỉ Giao Dịch SỐ KHUYẾT (Không Rơi/Đảo)",
    ]
    MENU_OPTIONS = [
        "🔄 1. ĐỒNG BỘ & CẬP NHẬT DỮ LIỆU",
        "🎯 2. KHUYẾN NGHỊ LỆNH",
        "🛡️ 3. QUẢN TRỊ RỦI RO",
        "🔍 4. KIỂM TOÁN ĐƠN PHIÊN",
        "📈 5. ĐẠI KẾ TOÁN QUÉT CHU KỲ",
        "🎰 6. DỮ LIỆU THÔ"
    ]

# ==============================================================================
# 🛠️ BLOCK 2: CÔNG CỤ XỬ LÝ LÕI
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
# 🕸️ BLOCK 3: TRÌNH THU THẬP DỮ LIỆU (CRAWLER XUYÊN THẤU)
# ==============================================================================
class Crawler:
    @staticmethod
    def extract_date(html_text, identifier):
        html_text = html_text.replace('"', "'")
        raw_blocks = re.findall(identifier + r'[^>]*>(.*?)</', html_text, flags=re.IGNORECASE|re.DOTALL)
        for block in raw_blocks:
            clean_block = re.sub(r'<[^>]+>', ' ', html.unescape(block))
            d_m = re.search(r'\d{1,2}[-/.]\d{1,2}[-/.]\d{4}', clean_block)
            if d_m: return d_m.group().replace("-", "/").replace(".", "/")
        
        idx = html_text.find(identifier.replace("\\", ""))
        if idx != -1:
            snippet = html_text[idx:idx+200]
            clean = re.sub(r'<[^>]+>', ' ', html.unescape(snippet))
            d_m = re.search(r'\d{1,2}[-/.]\d{1,2}[-/.]\d{4}', clean)
            if d_m: return d_m.group().replace("-", "/").replace(".", "/")
        return None

    @staticmethod
    def extract_numbers(html_text, class_name):
        html_text = html_text.replace('"', "'")
        raw_blocks = re.findall(r'class=\'' + class_name + r'\'[^>]*>(.*?)</[a-zA-Z]+>', html_text, flags=re.IGNORECASE|re.DOTALL)
        numbers = []
        for block in raw_blocks:
            clean_block = re.sub(r'<[^>]+>', ' ', html.unescape(block))
            digits = re.findall(r'\d+', clean_block)
            for d in digits:
                if len(d) >= 2: numbers.append(d[-2:])
        return numbers

    @staticmethod
    def fetch_source_1(target_dt):
        d_str_url = target_dt.strftime('%d-%m-%Y') if target_dt else ""
        url = f"https://xoso.com.vn/xsmb-{d_str_url}.html" if target_dt else "https://xoso.com.vn/xsmb.html"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        if res.status_code == 200:
            date_str = Crawler.extract_date(res.text, "id='mb_date'")
            if not date_str: return False, None, "Dữ liệu trống (Không có ngày)"
            numbers = Crawler.extract_numbers(res.text, "v-giai")
            if len(numbers) >= 27: return True, (date_str, " ".join(numbers[:27])), "xoso.com.vn"
            return False, None, f"Thiếu giải ({len(numbers)})"
        return False, None, f"HTTP {res.status_code}"

    @staticmethod
    def fetch_source_2(target_dt):
        d_str_url = target_dt.strftime('%d-%m-%Y') if target_dt else ""
        url = f"https://kqxs.vn/mien-bac/ngay-{d_str_url}" if target_dt else "https://kqxs.vn/mien-bac"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
        if res.status_code == 200:
            date_str = Crawler.extract_date(res.text, "class='tit-mien'")
            if not date_str: return False, None, "Dữ liệu trống (Không có ngày)"
            numbers = Crawler.extract_numbers(res.text, "day-so")
            if len(numbers) >= 27: return True, (date_str, " ".join(numbers[:27])), "kqxs.vn"
            return False, None, f"Thiếu giải ({len(numbers)})"
        return False, None, f"HTTP {res.status_code}"

    @staticmethod
    def fetch_by_date(target_dt=None):
        if not HAS_REQUESTS: return False, None, "Thiếu thư viện 'requests'"
        logs = []
        try:
            s1, res1, msg1 = Crawler.fetch_source_1(target_dt)
            if s1: return True, res1, msg1
            logs.append(f"Src1: {msg1}")
        except Exception as e: logs.append(f"Src1 Err: {str(e)[:15]}")
            
        try:
            s2, res2, msg2 = Crawler.fetch_source_2(target_dt)
            if s2: return True, res2, msg2
            logs.append(f"Src2: {msg2}")
        except Exception as e: logs.append(f"Src2 Err: {str(e)[:15]}")
            
        return False, None, " | ".join(logs)

# ==============================================================================
# 💾 BLOCK 4: QUẢN TRỊ CƠ SỞ DỮ LIỆU & AUTO HEAL
# ==============================================================================
class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        if not os.path.exists(Config.DATA_FILE):
            pd.DataFrame(columns=["Ngày", "Kết Quả Loto"]).to_excel(Config.DATA_FILE, index=False)
            return db, "⚠️ Tệp dữ liệu rỗng (0 Phiên)."
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
        except Exception as e: return db, f"🛑 LỖI ĐỌC DB: {e}"

    @staticmethod
    def save_manual_data(date_str, numbers_str):
        res_date = Utils.chuan_hoa_ngay(date_str)
        if not res_date: return "🛑 LỖI: Ngày không đúng định dạng (VD: 01/08/2026)."
        dt_obj, std_date = res_date
        
        nums = re.findall(r'\d{2}', str(numbers_str))
        if len(nums) < 27: return f"🛑 LỖI: Chỉ tìm thấy {len(nums)}/27 con số."
        nums = nums[:27]
        
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str) if os.path.exists(Config.DATA_FILE) else pd.DataFrame(columns=["Ngày", "Kết Quả Loto"])
            df = df[df['Ngày'] != std_date] # Xóa dòng trùng
            new_row = pd.DataFrame({"Ngày": [std_date], "Kết Quả Loto": [" ".join(nums)]})
            df = pd.concat([new_row, df], ignore_index=True)
            df.to_excel(Config.DATA_FILE, index=False)
            return f"✅ LƯU THÀNH CÔNG: Đã thêm kết quả ngày {std_date}!"
        except Exception as e:
            return f"🛑 LỖI LƯU FILE: {e}"

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
                df_old = pd.read_excel(Config.DATA_FILE, dtype=str)
                df_final = pd.concat([df_new, df_old], ignore_index=True)
            except: df_final = df_new
            df_final.to_excel(Config.DATA_FILE, index=False)
            return f"🛠️ AUTO-HEAL: Vá thành công {healed_count} phiên bị mất."
        
        if error_logs and len(db) == 0: return f"🛑 CRAWLER LỖI: {error_logs[0]}"
        return "✅ AUTO-HEAL: Không phát hiện lỗ hổng dữ liệu 15 ngày qua."

    @staticmethod
    def get_boundaries(db):
        now_vn = Utils.get_vn_time()
        today = datetime(now_vn.year, now_vn.month, now_vn.day)
        default_next = today + timedelta(days=1) if now_vn.hour >= 19 else today
        
        if not db: return None, None, default_next
        all_dates = [info["date_obj"] for info in db.values()]
        max_dt = max(all_dates)
        return min(all_dates), max_dt, max_dt + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 5: QUANT ENGINE (GIỮ NGUYÊN BẢN LÕI V36.1.1)
# ==============================================================================
class QuantEngine:
    @staticmethod
    def get_signal(target_dt, db, mode):
        t_minus_7 = target_dt - timedelta(days=7)
        str_t7 = t_minus_7.strftime("%d/%m/%Y")
        
        if str_t7 not in db: 
            return None, f"[THIẾU DỮ LIỆU T-7 ({str_t7})]"
            
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
            else: 
                rac = dan_t7 - tinh_hoa
                return sorted(list(rac)), "OK"
        else: 
            return sorted(list(dan_t7)), "OK"

# ==============================================================================
# 📊 BLOCK 6: AUDIT BÁO CÁO (ĐÃ GỘP PHÂN HỆ 5 VÀO 6)
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        crawl_msg = "ℹ️ Chế độ Offline."
        if auto_crawl: crawl_msg = DatabaseManager.auto_heal_history()
        
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        latest_str = latest_dt.strftime('%d/%m/%Y') if latest_dt else "⚠️ CHƯA CÓ DỮ LIỆU NÀO TRONG DB!"
        
        lines = [
            "📑 [PHÂN HỆ 1] BÁO CÁO: ĐỒNG BỘ CƠ SỞ DỮ LIỆU",
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
        if not date_str or not num_str: return "🛑 LỖI: Vui lòng điền đủ Ngày và Chuỗi 27 số.", ""
        save_msg = DatabaseManager.save_manual_data(date_str, num_str)
        report, title = Auditor.phan_he_1_sync(auto_crawl=False)
        return f"{save_msg}\n\n{report}", title

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
                f"🎚️ CHIẾN LƯỢC ÁP DỤNG: {mode}\n"
            ]
            if dan is None:
                lines.extend([f"🛑 CẢNH BÁO: {msg}.", "👉 LỜI KHUYÊN: Hãy Đồng bộ cào tự động hoặc Nhập tay dữ liệu để hệ thống có mốc quá khứ!"])
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
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 2: {e}"

    @staticmethod
    def phan_he_3_risk(base_pts, sim_size):
        try:
            valid1, err1 = Utils.check_valid_number(base_pts, "Khối lượng")
            valid2, err2 = Utils.check_valid_number(sim_size, "Số lượng Mã")
            if not valid1: return err1
            if not valid2: return err2
            base_pts, so_luong_lo = int(float(base_pts)), int(float(sim_size))
            von_ngay = so_luong_lo * base_pts * Config.COST_PER_POINT
            lines = [
                "📑 [PHÂN HỆ 3] BÁO CÁO: QUẢN TRỊ RỦI RO & MÔ PHỎNG",
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
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 3: {e}"

    @staticmethod
    def phan_he_4_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            if ngay_str not in db: return f"🛑 LỖI: Phiên giao dịch {ngay_str} chưa được cập nhật."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = int(float(pts_per_code_base))
            
            lo_to_27_today = db[ngay_str]["prizes_int"]
            t_minus_7 = d_obj - timedelta(days=7)
            t_minus_1 = d_obj - timedelta(days=1)
            ngay_str_t7 = t_minus_7.strftime("%d/%m/%Y")
            ngay_str_t1 = t_minus_1.strftime("%d/%m/%Y")

            report = f"📑 [PHÂN HỆ 4] BÁO CÁO: KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN\n"
            report += f"========================================================================\n\n"

            if ngay_str_t7 not in db:
                report += f"📡 THÔNG TIN PHIÊN: {ngay_str}\n"
                report += f"🔭 LỖI CHU KỲ: Thiếu dữ liệu mốc T-7 ({ngay_str_t7}). Không thể phân tích!\n"
                return report

            dan_t7 = set(db[ngay_str_t7]["prizes_int"])

            def cal_pnl(danh_sach):
                sl = len(danh_sach)
                if sl == 0: return 0, 0, 0, 0, 0, "⚫ KHÔNG GIAO DỊCH"
                chi_phi = sl * base_pts * Config.COST_PER_POINT
                nhay = sum(lo_to_27_today.count(x) for x in danh_sach)
                doanh_thu = nhay * base_pts * Config.WIN_PER_NHAY
                lai = doanh_thu - chi_phi
                status = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                return sl, chi_phi, nhay, doanh_thu, lai, status

            list_full = sorted(list(dan_t7))
            sl_f, chi_f, nhay_f, thu_f, lai_f, st_f = cal_pnl(list_full)
            lai_f_str = f"{lai_f:+,.0f}" if lai_f != 0 else "0"

            report += f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str} (Phân bổ: {base_pts}đ/mã)\n\n"
            report += f"🛑 [KỊCH BẢN 1] - GIAO DỊCH TOÀN BỘ T-7 (Tinh hoa + Khuyết nhịp)\n"
            report += f" • Danh mục {sl_f} mã: " + " ".join([f"{x:02d}" for x in list_full]) + "\n"
            report += f" • Đạt {nhay_f} lượt.  Vốn đầu tư: {chi_f:,.0f}đ  | Doanh thu: {thu_f:,.0f}đ\n"
            report += f" 👉 LỢI NHUẬN RÒNG: {lai_f_str} VNĐ ({st_f})\n\n"

            if ngay_str_t1 not in db:
                report += f"⚠️ LƯU Ý: Thiếu dữ liệu mốc T-1 ({ngay_str_t1}). Không thể phân tách Kịch bản 2 & 3.\n"
                return report

            kq_t1 = set(db[ngay_str_t1]["prizes_int"])
            tinh_hoa = set()
            for x in dan_t7:
                lon = (x % 10) * 10 + (x // 10)
                if x in kq_t1 or lon in kq_t1: tinh_hoa.add(x)
            rac = dan_t7 - tinh_hoa

            list_rac = sorted(list(rac))
            list_tinh_hoa = sorted(list(tinh_hoa))
            sl_r, chi_r, nhay_r, thu_r, lai_r, st_r = cal_pnl(list_rac)
            sl_t, chi_t, nhay_t, thu_t, lai_t, st_t = cal_pnl(list_tinh_hoa)

            lai_r_str = f"{lai_r:+,.0f}" if lai_r != 0 else "0"
            lai_t_str = f"{lai_t:+,.0f}" if lai_t != 0 else "0"

            report += f"📉 [KỊCH BẢN 2] - BÓC TÁCH: SỐ KHUYẾT NHỊP (Không Rơi/Đảo từ T-1)\n"
            if sl_r == 0: report += f" 👉 100% Danh mục duy trì động lượng tốt.\n\n"
            else:
                report += f" • Danh mục {sl_r} mã: " + " ".join([f"{x:02d}" for x in list_rac]) + "\n"
                report += f" • Đạt {nhay_r} lượt.  Vốn đầu tư: {chi_r:,.0f}đ  | Doanh thu: {thu_r:,.0f}đ\n"
                report += f" 👉 HIỆU QUẢ CỦA MÃ KHUYẾT: {lai_r_str} VNĐ ({st_r})\n\n"

            report += f"💎 [KỊCH BẢN 3] - BÓC TÁCH: SỐ TINH HOA (Động lượng Rơi/Đảo từ T-1)\n"
            if sl_t == 0: report += f" 👉 KHÔNG CÓ MÃ ĐẠT CHUẨN.\n\n"
            else:
                report += f" • Danh mục {sl_t} mã: " + " ".join([f"{x:02d}" for x in list_tinh_hoa]) + "\n"
                report += f" • Đạt {nhay_t} lượt.  Vốn đầu tư: {chi_t:,.0f}đ  | Doanh thu: {thu_t:,.0f}đ\n"
                report += f" 👉 LỢI NHUẬN RÒNG: {lai_t_str} VNĐ ({st_t})\n\n"

            return report
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 4: {e}"

    @staticmethod
    def phan_he_5_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI: Định dạng ngày không hợp lệ."
            
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            
            base_pts = int(float(pts_per_code_base))
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            
            lines = [
                "📑 [PHÂN HỆ 5] BÁO CÁO: ĐẠI KẾ TOÁN QUÉT CHU KỲ (GỘP BÁO CÁO THÁNG)",
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
                            "year": curr.year, "month_str": curr.strftime("%m/%Y"),
                            "codes": sl, "chi": von, "thu": thuong, "lai": lai,
                            "win": 1 if lai > 0 else 0, "loss": 1 if lai <= 0 else 0,
                        })
                curr += timedelta(days=1)
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO ĐẠT ĐIỀU KIỆN XUẤT LỆNH."
            
            df_rec = pd.DataFrame(daily_records)
            lines.extend([
                "", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG (GỘP PHÂN HỆ THÁNG CŨ)",
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
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 5: {traceback.format_exc()}"

    @staticmethod
    def phan_he_6_raw(ngay_raw):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI: Định dạng ngày không hợp lệ."
            _, ngay_str = res
            if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại."
            lo_to_raw = db[ngay_str]["prizes_int"]
            lines = [
                "📑 [PHÂN HỆ 6] BÁO CÁO: TRUY XUẤT RAW DB",
                "=======================================================",
                f"📅 KẾT QUẢ PHIÊN GIAO DỊCH: {ngay_str}\n🎰 Danh sách 27 giải:"
            ]
            row_str = ""
            for idx, lo in enumerate(lo_to_raw):
                row_str += f"[{lo:02d}] "
                if (idx + 1) % 9 == 0:
                    lines.append(row_str.strip())
                    row_str = ""
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI: {e}"

# ==============================================================================
# 🎮 BLOCK 7: GIAO DIỆN NGƯỜI DÙNG (UI LAYER)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    _, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title="XSMB QUANT V36.1.2 PRO", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 XSMB QUANT V36.1.2 — BẢN TÍCH HỢP BẢO MẬT & NHẬP LIỆU THỦ CÔNG")
        gr.Markdown("*(Đã hợp nhất chức năng Báo cáo Tháng vào Quét Chu Kỳ. Hỗ trợ Nhập Thủ Công để độc lập 100% với Web)*")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (TỰ ĐỘNG CÀO)", variant="primary")
            
            gr.Markdown("---")
            gr.Markdown("✍️ **HOẶC NHẬP KẾT QUẢ BẰNG TAY (DÀNH CHO NGÀY CRAWLER BỊ TRỐNG)**")
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
            with gr.Row():
                pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                sim_size = gr.Number(label="Quy mô Danh mục (Số lượng mã)", value=12)
            btn_3 = gr.Button("🧪 KHỞI CHẠY MÔ PHỎNG LỢI NHUẬN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Quản trị Rủi ro", lines=16)
            btn_3.click(Auditor.phan_he_3_risk, inputs=[pts_3, sim_size], outputs=out_3)
            
        with gr.Column(visible=False) as col_4:
            with gr.Row():
                date_4 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📡 KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Bóc tách Động lượng", lines=24)
            btn_4.click(Auditor.phan_he_4_single, inputs=[date_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            with gr.Row():
                t1_5 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
                t2_5 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_5 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_5 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_5 = gr.Button("📈 ĐẠI KẾ TOÁN QUÉT CHU KỲ TỔNG HỢP", variant="primary")
            out_5 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền & Max Drawdown", lines=22)
            btn_5.click(Auditor.phan_he_5_range, inputs=[t1_5, t2_5, pts_5, mode_5], outputs=out_5)

        with gr.Column(visible=False) as col_6:
            date_6 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_6 = gr.Button("💾 TRUY XUẤT DỮ LIỆU THÔ (RAW DATA)", variant="primary")
            out_6 = gr.Textbox(label="Log Dữ Liệu Máy Chủ", lines=10)
            btn_6.click(Auditor.phan_he_6_raw, inputs=date_6, outputs=out_6)

        # Connections
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
