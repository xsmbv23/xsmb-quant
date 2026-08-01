import os
import sys
import pandas as pd
import numpy as np
import math
import calendar
import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
import traceback
import gradio as gr

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG & BIẾN MÔI TRƯỜNG (SYSTEM CONFIG)
# ==============================================================================
class Config:
    VERSION = "V36.3 PRO ALGO (TÍCH HỢP AUTO-CRAWLER & BIỂU ĐỒ QUANT)"
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
        "📊 5. BÁO CÁO THÁNG",
        "📈 6. PHÂN TÍCH CHU KỲ & BIỂU ĐỒ",
        "🎰 7. DỮ LIỆU THÔ"
    ]

# ==============================================================================
# 🛠️ BLOCK 2: CÔNG CỤ XỬ LÝ LÕI (UTILITIES & VALIDATORS)
# ==============================================================================
class Utils:
    @staticmethod
    def chuan_hoa_ngay(ngay_raw):
        if pd.isna(ngay_raw) or not str(ngay_raw).strip():
            return None
        try:
            s = str(ngay_raw).strip().split()[0].replace("-", "/").replace(".", "/")
            parts = [p for p in s.split("/") if p]
            if len(parts) < 3:
                return None
            d, m, y = parts[0], parts[1], parts[2]
            if len(d) == 4:
                y, m, d = d, m, y
            if len(d) == 1: d = "0" + d
            if len(m) == 1: m = "0" + m
            if len(y) == 2: y = "20" + y
            str_chuan = f"{d}/{m}/{y}"
            return datetime.strptime(str_chuan, "%d/%m/%Y"), str_chuan
        except Exception:
            return None

    @staticmethod
    def lay_max_days(thang, nam):
        return calendar.monthrange(nam, thang)[1]

    @staticmethod
    def safe_int(val, default=0):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def check_valid_number(val, name):
        if val is None or str(val).strip() == "":
            return False, f"🛑 LỖI THÔNG SỐ: Vui lòng nhập thông tin cho '{name}'."
        try:
            f_val = float(val)
            if f_val <= 0:
                return False, f"🛑 LỖI THÔNG SỐ: Giá trị '{name}' phải lớn hơn 0."
            return True, ""
        except (ValueError, TypeError):
            return False, f"🛑 LỖI THÔNG SỐ: '{name}' không đúng định dạng số."

# ==============================================================================
# 🕸️ BLOCK 3: AUTO-CRAWLER (LẤY DỮ LIỆU TỰ ĐỘNG)
# ==============================================================================
class Crawler:
    @staticmethod
    def fetch_latest_xsmb():
        # Cào dữ liệu từ xoso.me (hoặc nguồn tương đương) - Có try-except bảo vệ 100%
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            url = "https://xoso.com.vn/xsmb.html"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return False, f"Lỗi kết nối Server KQXS (HTTP {response.status_code})"
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Tìm ngày
            date_elem = soup.find('span', id='mb_date')
            if not date_elem:
                return False, "Không trích xuất được ngày mở thưởng."
            date_str = date_elem.text.strip()
            
            # Lấy list số trúng giải
            numbers = []
            prizes = soup.find_all('span', class_='v-giai')
            for p in prizes:
                txt = p.text.strip()
                if txt.isdigit():
                    numbers.append(txt[-2:])
            
            if len(numbers) >= 27:
                kq_27 = " ".join(numbers[:27])
                return True, (date_str, kq_27)
            else:
                return False, f"Cấu trúc web thay đổi, chỉ cào được {len(numbers)} giải."
        except Exception as e:
            return False, f"Lỗi ngoại lệ Crawler: {str(e)}"

# ==============================================================================
# 💾 BLOCK 4: QUẢN TRỊ CƠ SỞ DỮ LIỆU (DATABASE MANAGER)
# ==============================================================================
class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        if not os.path.exists(Config.DATA_FILE):
            df_empty = pd.DataFrame(columns=["Ngày", "Kết Quả Loto"])
            df_empty.to_excel(Config.DATA_FILE, index=False)
            return db, f"⚠️ CẢNH BÁO: Không tìm thấy '{Config.DATA_FILE}'. Đã tạo tệp trống tự động."
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str)
            if df.shape[1] < 2: return db, "🛑 LỖI CẤU TRÚC: File dữ liệu thiếu cột."
            col_ngay, col_loto = df.columns[0], df.columns[1]
            dup_count = 0
            for _, row in df.iterrows():
                res_date = Utils.chuan_hoa_ngay(row[col_ngay])
                if not res_date: continue
                dt_obj, ngay_str = res_date
                
                loto_raw = re.sub(r"[^\d\s]", " ", str(row[col_loto]))
                loto_list = [int(x.strip()[-2:]) for x in loto_raw.split() if x.strip().isdigit()]
                
                if len(loto_list) >= 27:
                    if ngay_str in db: dup_count += 1
                    db[ngay_str] = {
                        "date_obj": dt_obj,
                        "date_str": ngay_str,
                        "prizes_int": loto_list[:27],
                        "raw_str": " ".join([f"{x:02d}" for x in loto_list[:27]])
                    }
            msg = f"🟢 ĐỒNG BỘ THÀNH CÔNG {len(db)} PHIÊN GIAO DỊCH."
            if dup_count > 0: msg += f" (Phát hiện {dup_count} dòng ghi đè)."
            return db, msg
        except Exception as e:
            return db, f"🛑 LỖI TRUY XUẤT DỮ LIỆU: {e}"

    @staticmethod
    def update_excel_from_crawler():
        db, msg = DatabaseManager.load_db()
        success, crawler_res = Crawler.fetch_latest_xsmb()
        if not success:
            return f"🛑 CẬP NHẬT TỰ ĐỘNG THẤT BẠI: {crawler_res}\nTrạng thái DB cũ: {msg}"
            
        date_str_crawled, loto_27_str = crawler_res
        res_date = Utils.chuan_hoa_ngay(date_str_crawled)
        if not res_date:
            return f"🛑 CẬP NHẬT TỰ ĐỘNG THẤT BẠI: Lỗi chuẩn hóa ngày '{date_str_crawled}'."
            
        _, std_date_str = res_date
        if std_date_str in db:
            return f"✅ DỮ LIỆU ĐÃ MỚI NHẤT: Phiên {std_date_str} đã tồn tại trong Hệ thống.\nTrạng thái DB: {msg}"
            
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str)
            new_row = pd.DataFrame({df.columns[0]: [std_date_str], df.columns[1]: [loto_27_str]})
            df = pd.concat([new_row, df], ignore_index=True)
            df.to_excel(Config.DATA_FILE, index=False)
            return f"🚀 CẬP NHẬT THÀNH CÔNG: Đã cào và lưu phiên {std_date_str} vào DB!\nGiải mã: [ {loto_27_str} ]"
        except Exception as e:
            return f"🛑 LỖI GHI FILE KHI CRAWL: {e}"

    @staticmethod
    def get_boundaries(db):
        if not db:
            today = datetime.now()
            return today, today, today + timedelta(days=1)
        all_dates = [info["date_obj"] for info in db.values()]
        return min(all_dates), max(all_dates), max(all_dates) + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 5: LÕI THUẬT TOÁN QUANT (ALGORITHM ENGINE)
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
            
        else:
            return sorted(list(dan_t7)), "OK"

# ==============================================================================
# 📊 BLOCK 6: PHÂN HỆ KIỂM TOÁN TÀI CHÍNH (AUDIT & REPORTING)
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync(auto_crawl=False):
        if auto_crawl:
            crawl_msg = DatabaseManager.update_excel_from_crawler()
        else:
            crawl_msg = "ℹ️ Đã bỏ qua cập nhật tự động. Chỉ tải dữ liệu hiện tại."
            
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        
        lines = [
            "📑 [PHÂN HỆ 1] BÁO CÁO: ĐỒNG BỘ CƠ SỞ DỮ LIỆU",
            "=================================================================================",
            f"• Phiên bản hệ thống : {Config.VERSION}",
            f"• Trạng thái Dữ liệu : {msg}",
            f"• Trình thu thập Web  : {crawl_msg}",
            f"• Phiên cập nhật cuối: 📅 [{latest_dt.strftime('%d/%m/%Y')}]",
            f"• Lịch phân tích tới : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
        ]
        return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ TỚI: {next_predict_dt.strftime('%d/%m/%Y')}"

    @staticmethod
    def phan_he_2_predict(pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            _, _, next_dt = DatabaseManager.get_boundaries(db)
            is_valid, err_msg = Utils.check_valid_number(pts_per_code_base, "Khối lượng vốn")
            if not is_valid: return err_msg
            
            base_pts = Utils.safe_int(pts_per_code_base)
            dan, msg = QuantEngine.get_signal(next_dt, db, mode)
            
            lines = [
                "📑 [PHÂN HỆ 2] BÁO CÁO: KHUYẾN NGHỊ GIAO DỊCH KẾ TIẾP",
                "=======================================================",
                f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_dt.strftime('%d/%m/%Y')}",
                f"🎚️ CHIẾN LƯỢC ÁP DỤNG: {mode}",
                ""
            ]
            if dan is None:
                lines.extend([f"🛑 CẢNH BÁO: Dữ liệu tham chiếu {msg}.", "HỆ THỐNG TẠM NGỪNG CẤP TÍN HIỆU ĐỂ BẢO TOÀN VỐN."])
                return "\n".join(lines)
                
            so_luong_lo = len(dan)
            von_ngay = so_luong_lo * base_pts * Config.COST_PER_POINT
            if so_luong_lo > 0:
                dan_str = " ".join([f"{x:02d}" for x in dan])
                lines.extend([
                    f"📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN ({so_luong_lo} MÃ):",
                    f" [ {dan_str} ]",
                    "-------------------------------------------------------",
                    f" • Khối lượng phân bổ : {base_pts} điểm / 1 mã",
                    f"💰 TỔNG VỐN YÊU CẦU   : {von_ngay:,.0f} VND"
                ])
                diem_hoa_von = math.ceil(von_ngay / (base_pts * Config.WIN_PER_NHAY)) if base_pts > 0 else 0
                lines.append(f"💡 MỤC TIÊU HÒA VỐN   : Cần tối thiểu {diem_hoa_von} lượt trúng.")
            else:
                lines.extend([
                    "📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN:",
                    " 👉 🚫 [KHÔNG CÓ TÍN HIỆU KHẢ THI]",
                    "-------------------------------------------------------",
                    "💰 TỔNG VỐN YÊU CẦU: 0 VND",
                    "💡 HỆ THỐNG KHUYẾN NGHỊ ĐỨNG NGOÀI THỊ TRƯỜNG PHIÊN NÀY."
                ])
            return "\n".join(lines)
        except Exception as e:
            return f"🛑 LỖI PHÂN HỆ 2: {e}"

    @staticmethod
    def phan_he_3_risk(base_pts, sim_size):
        try:
            valid1, err1 = Utils.check_valid_number(base_pts, "Khối lượng vốn")
            valid2, err2 = Utils.check_valid_number(sim_size, "Số lượng Mã")
            if not valid1: return err1
            if not valid2: return err2
            
            base_pts = Utils.safe_int(base_pts)
            so_luong_lo = Utils.safe_int(sim_size)
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
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 3: {e}"

    @staticmethod
    def phan_he_4_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            if ngay_str not in db: return f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên giao dịch {ngay_str} chưa được cập nhật."
            valid, err = Utils.check_valid_number(pts_per_code_base, "Khối lượng vốn")
            if not valid: return err
            base_pts = Utils.safe_int(pts_per_code_base)
            
            lines = [
                "📑 [PHÂN HỆ 4] BÁO CÁO: KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN CHUYÊN SÂU",
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
                lai_s = f"{lai:+,.0f}" if lai != 0 else "0"
                return [
                    f"📌 [{name}]",
                    f" • Danh mục {sl} mã: " + " ".join([f"{x:02d}" for x in danh_sach]),
                    f" • Đạt {nhay} lượt. Vốn: {chi:,.0f}đ | Thu: {thu:,.0f}đ",
                    f" 👉 PnL RÒNG: {lai_s} VNĐ ({st})"
                ]

            for i, mode in enumerate(Config.MODES):
                dan, msg = QuantEngine.get_signal(d_obj, db, mode)
                mode_name = f"CHIẾN LƯỢC {i+1}"
                if dan is None:
                    lines.append(f"🛑 [{mode_name}] {mode}: Thiếu dữ liệu {msg}")
                else:
                    lines.extend(calc_str(dan, mode))
                lines.append("------------------------------------------------------------------------")
            
            lines.append("💡 KẾT LUẬN: Đánh giá sức mạnh các bộ lọc động lượng đã thực thi độc lập.")
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 4: {e}"

    @staticmethod
    def phan_he_5_monthly(month, year, pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            valid_m, err_m = Utils.check_valid_number(month, "Tháng")
            valid_y, err_y = Utils.check_valid_number(year, "Năm")
            valid_p, err_p = Utils.check_valid_number(pts_per_code_base, "Khối lượng vốn")
            if not valid_m: return err_m
            if not valid_y: return err_y
            if not valid_p: return err_p
            thang, nam, base_pts = Utils.safe_int(month), Utils.safe_int(year), Utils.safe_int(pts_per_code_base)
            if not (1 <= thang <= 12): return "🛑 LỖI THÔNG SỐ: Giá trị 'Tháng' phải nằm trong khoảng từ 1 đến 12."
            
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            start_dt = datetime(nam, thang, 1)
            end_dt = datetime(nam, thang, Utils.lay_max_days(thang, nam))
            if start_dt < min_dt: start_dt = min_dt
            if end_dt > max_dt: end_dt = max_dt
            if start_dt > end_dt: return f"🛑 BÁO CÁO: Kỳ kế toán {thang:02d}/{nam} hoàn toàn trống dữ liệu."
            
            lines = [
                "📑 [PHÂN HỆ 5] BÁO CÁO: TỔNG HỢP HIỆU SUẤT THEO THÁNG",
                "===================================================================================================================",
                f"📊 KỲ BÁO CÁO: {thang:02d}/{nam} - CHIẾN LƯỢC ĐẦU TƯ: {mode}",
                "-------------------------------------------------------------------------------------------------------------------",
                f"{'NGÀY G.DỊCH':<12} | {'TRẠNG THÁI':<15} | {'SỐ MÃ':<7} | {'VỐN ĐẦU TƯ':<14} | {'LƯỢT':<5} | {'DOANH THU':<14} | {'LỢI NHUẬN':<15} | {'LŨY KẾ':<12}",
                "-------------------------------------------------------------------------------------------------------------------"
            ]
            luy_ke_thang = cash_thu = cash_chi = total_phien_danh = 0
            curr = start_dt
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                if ngay_str not in db:
                    lines.append(f"{ngay_str:<12} | {'⚠️ THIẾU DATA':<15} | {'-':<7} | {'-':<14} | {'-':<5} | {'-':<14} | {'-':<15} | {luy_ke_thang:>+12,.0f}")
                    curr += timedelta(days=1); continue
                dan, msg = QuantEngine.get_signal(curr, db, mode)
                if dan is None:
                    lines.append(f"{ngay_str:<12} | {'🔭 THEO DÕI':<15} | {'0':<7} | {'-':<14} | {'-':<5} | {'-':<14} | {msg:<15} | {luy_ke_thang:>+12,.0f}")
                    curr += timedelta(days=1); continue
                if len(dan) == 0:
                    lines.append(f"{ngay_str:<12} | {'🔭 THEO DÕI':<15} | {'0':<7} | {'-':<14} | {'-':<5} | {'-':<14} | {'[KHÔNG TÍN HIỆU]':<15} | {luy_ke_thang:>+12,.0f}")
                    curr += timedelta(days=1); continue
                    
                total_phien_danh += 1
                sl = len(dan)
                von = sl * base_pts * Config.COST_PER_POINT
                nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in dan)
                thuong = nhay * base_pts * Config.WIN_PER_NHAY
                lai = thuong - von
                luy_ke_thang += lai
                cash_chi += von
                cash_thu += thuong
                status_str = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                lines.append(f"{ngay_str:<12} | {status_str:<15} | {sl:<7} | {von:<14,.0f} | {nhay:<5} | {thuong:<14,.0f} | {lai:>+15,.0f} | {luy_ke_thang:>+12,.0f}")
                curr += timedelta(days=1)
                
            roi = (luy_ke_thang / cash_chi * 100) if cash_chi > 0 else 0
            lines.extend([
                "===================================================================================================================",
                f"📝 ĐỐI SOÁT KẾ TOÁN: {total_phien_danh} PHIÊN CÓ XUẤT LỆNH",
                f"• TỔNG DÒNG TIỀN: Giải ngân {cash_chi:,.0f} đ | Thu về {cash_thu:,.0f} đ",
                f"• LỢI NHUẬN RÒNG & BIÊN R.O.I: {luy_ke_thang:+,.0f} VND ({roi:+.2f} %)"
            ])
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 5: {e}"

    @staticmethod
    def phan_he_6_range_chart(tu_ngay_raw, den_ngay_raw, pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ.", None
            
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            valid, err = Utils.check_valid_number(pts_per_code_base, "Khối lượng vốn")
            if not valid: return err, None
            
            base_pts = Utils.safe_int(pts_per_code_base)
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if start_dt < min_dt: start_dt = min_dt
            if end_dt > max_dt: end_dt = max_dt
            if start_dt > end_dt: return "🛑 LỖI: Khoảng thời gian tra cứu nằm ngoài Phạm vi Dữ liệu.", None
            
            lines = [
                "📑 [PHÂN HỆ 6] BÁO CÁO: ĐẠI KẾ TOÁN QUÉT CHU KỲ & BIỂU ĐỒ",
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
                            "codes": sl, "chi": von, "nhay": nhay, "thu": thuong, "lai": lai,
                            "win": 1 if lai > 0 else 0, "loss": 1 if lai <= 0 else 0,
                        })
                curr += timedelta(days=1)
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO ĐẠT ĐIỀU KIỆN XUẤT LỆNH.", None
            
            df_rec = pd.DataFrame(daily_records)
            
            # --- 1. Tạo báo cáo Text ---
            lines.extend([
                "", "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO NĂM",
                "-------------------------------------------------------------------------------------------------------------------",
                f"{'NĂM':<10} | {'PHIÊN':<7} | {'SỐ MÃ':<8} | {'VỐN ĐẦU TƯ':<14} | {'DOANH THU':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}",
                "-------------------------------------------------------------------------------------------------------------------"
            ])
            for year, g_y in df_rec.groupby("year"):
                p_chi, p_thu, p_lai = g_y["chi"].sum(), g_y["thu"].sum(), g_y["lai"].sum()
                p_roi = (p_lai / p_chi * 100) if p_chi > 0 else 0
                lines.append(f"Năm {year:<6} | {len(g_y):<7} | {g_y['codes'].sum():<8} | {p_chi:<14,.0f} | {p_thu:<14,.0f} | {p_lai:>+16,.0f} | {p_roi:>+7.2f}%")
                
            lines.extend([
                "", "📊 2. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG",
                "-------------------------------------------------------------------------------------------------------------------",
                f"{'THÁNG/NĂM':<10} | {'PHIÊN':<7} | {'WIN/LOSS':<10} | {'VỐN ĐẦU TƯ':<14} | {'DOANH THU':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}",
                "-------------------------------------------------------------------------------------------------------------------"
            ])
            for m_str, g_m in df_rec.groupby("month_str", sort=False):
                m_chi, m_thu, m_lai = g_m["chi"].sum(), g_m["thu"].sum(), g_m["lai"].sum()
                m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
                wl_str = f"{g_m['win'].sum()}W/{g_m['loss'].sum()}L"
                lines.append(f"Tháng {m_str:<5} | {len(g_m):<7} | {wl_str:<10} | {m_chi:<14,.0f} | {m_thu:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%")
                
            tot_chi, tot_thu, tot_lai = df_rec["chi"].sum(), df_rec["thu"].sum(), df_rec["lai"].sum()
            tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
            
            # --- 2. Tính Lợi Nhuận Tích Lũy & Max Drawdown ---
            df_rec['cum_pnl'] = df_rec['lai'].cumsum()
            df_rec['peak'] = df_rec['cum_pnl'].cummax()
            df_rec['drawdown'] = df_rec['cum_pnl'] - df_rec['peak']
            max_dd = df_rec['drawdown'].min()
            
            lines.extend([
                "===================================================================================================================",
                f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN | Win: {df_rec['win'].sum()} - Loss: {df_rec['loss'].sum()}):",
                f"• TỔNG VỐN ĐẦU TƯ   : {tot_chi:,.0f} VNĐ",
                f"• TỔNG DOANH THU     : {tot_thu:,.0f} VNĐ",
                f"• LỢI NHUẬN RÒNG     : {tot_lai:+,.0f} VNĐ",
                f"• TỶ LỆ ROI TOÀN KHUNG : {tot_roi:+.2f} %",
                f"• SỤT GIẢM TỐI ĐA (MaxDD): {max_dd:,.0f} VNĐ",
                "==================================================================================================================="
            ])
            
            # --- 3. TẠO BIỂU ĐỒ BẰNG PLOTLY ---
            fig = go.Figure()
            
            # Drawdown Area
            fig.add_trace(go.Scatter(
                x=df_rec['dt'], y=df_rec['peak'],
                mode='lines',
                line=dict(color='rgba(0,0,0,0)'),
                showlegend=False,
                hoverinfo='skip'
            ))
            fig.add_trace(go.Scatter(
                x=df_rec['dt'], y=df_rec['cum_pnl'],
                mode='lines',
                fill='tonexty',
                fillcolor='rgba(255, 0, 0, 0.2)',
                line=dict(color='rgba(0,0,0,0)'),
                name='Vùng Sụt Giảm (Drawdown)'
            ))
            # Equity Curve Line
            fig.add_trace(go.Scatter(
                x=df_rec['dt'], y=df_rec['cum_pnl'], 
                mode='lines', 
                name='Lợi Nhuận Tích Lũy',
                line=dict(color='blue', width=2)
            ))
            
            fig.update_layout(
                title=f"📈 BIỂU ĐỒ LỢI NHUẬN (EQUITY CURVE) <br><sup>PnL: {tot_lai:+,.0f} VNĐ | Max Drawdown: {max_dd:,.0f} VNĐ</sup>",
                xaxis_title="Thời Gian (Phiên Giao Dịch)",
                yaxis_title="Lợi Nhuận (VNĐ)",
                template="plotly_white",
                hovermode="x unified",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
            )
            
            return "\n".join(lines), fig
        except Exception as e:
            return f"🛑 LỖI PHÂN HỆ 6: {traceback.format_exc()}", None

    @staticmethod
    def phan_he_7_raw(ngay_raw):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            _, ngay_str = res
            if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại trên hệ thống."
            lo_to_raw = db[ngay_str]["prizes_int"]
            lines = [
                "📑 [PHÂN HỆ 7] BÁO CÁO: TRUY XUẤT RAW DB (DỮ LIỆU THÔ)",
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
        except Exception as e: return f"🛑 LỖI PHÂN HỆ 7: {e}"

# ==============================================================================
# 🎮 BLOCK 7: GIAO DIỆN NGƯỜI DÙNG (UI LAYER)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    _, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title="XSMB QUANT V36.3 PRO") as demo:
        gr.Markdown("# 🚀 XSMB QUANT V36.3 PRO — TÍCH HỢP AUTO-CRAWLER & BIỂU ĐỒ QUANT")
        gr.Markdown("*(Hệ thống Hướng Đối Tượng Modular. Đảm bảo tính toán minh bạch 100%, không Lookahead Bias.)*")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI TỪ XOSO.COM.VN", variant="primary")
            out_1 = gr.Textbox(label="Biên bản Hệ thống", lines=7)
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
                m_5 = gr.Number(label="Kỳ Báo cáo (Tháng 1-12)", value=latest_dt_init.month)
                y_5 = gr.Number(label="Năm Tài chính", value=latest_dt_init.year)
                pts_5 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_5 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_5 = gr.Button("📊 TRUY XUẤT BÁO CÁO TÀI CHÍNH THÁNG", variant="primary")
            out_5 = gr.Textbox(label="Sổ Cái Kế Toán", lines=22)
            btn_5.click(Auditor.phan_he_5_monthly, inputs=[m_5, y_5, pts_5, mode_5], outputs=out_5)

        with gr.Column(visible=False) as col_6:
            with gr.Row():
                t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
                t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y'))
                pts_6 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_6 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_6 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN & VẼ BIỂU ĐỒ", variant="primary")
            
            with gr.Row():
                out_6_text = gr.Textbox(label="Báo cáo Tổng Dòng Tiền", lines=20, scale=1)
                out_6_plot = gr.Plot(label="Biểu Đồ Lợi Nhuận", scale=2)
                
            btn_6.click(Auditor.phan_he_6_range_chart, inputs=[t1_6, t2_6, pts_6, mode_6], outputs=[out_6_text, out_6_plot])

        with gr.Column(visible=False) as col_7:
            date_7 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y'))
            btn_7 = gr.Button("💾 TRUY XUẤT DỮ LIỆU THÔ (RAW DATA)", variant="primary")
            out_7 = gr.Textbox(label="Log Dữ Liệu Máy Chủ", lines=10)
            btn_7.click(Auditor.phan_he_7_raw, inputs=date_7, outputs=out_7)

        btn_1_sync.click(lambda: Auditor.phan_he_1_sync(auto_crawl=False), outputs=[out_1, title_2])
        btn_1_crawl.click(lambda: Auditor.phan_he_1_sync(auto_crawl=True), outputs=[out_1, title_2])

        def update_visibility(choice):
            return [
                gr.update(visible=(choice == Config.MENU_OPTIONS[0])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[1])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[2])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[3])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[4])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[5])),
                gr.update(visible=(choice == Config.MENU_OPTIONS[6])),
            ]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3, col_4, col_5, col_6, col_7])
    return demo

if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
