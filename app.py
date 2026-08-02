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
    VERSION = "V36.18 PRO ALGO"
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
        "🔍 4. KIỂM TOÁN CHUYÊN SÂU",
        "📈 5. PHÂN TÍCH CHU KỲ TỔNG HỢP",
        "🎰 6. DỮ LIỆU THÔ"
    ]

# ==============================================================================
# 🛠️ BLOCK 2: UTILITIES (XỬ LÝ THỜI GIAN)
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
# 🕸️ BLOCK 3: CRAWLER KETQUA16.NET
# ==============================================================================
class Crawler:
    @staticmethod
    def fetch_ketqua16():
        if not HAS_REQUESTS: return False, {}, "Thiếu thư viện 'requests'"
        url = "https://ketqua16.net/so-ket-qua-truyen-thong/300"
        try:
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if res.status_code != 200: return False, {}, f"HTTP {res.status_code}"
            
            html_text = res.text
            parts = re.split(r'(\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b)', html_text)
            parsed_data = {}
            
            for i in range(1, len(parts)-1, 2):
                date_str_raw = parts[i]
                chunk = parts[i+1]
                
                d_m = re.search(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', date_str_raw)
                if d_m:
                    d, m, y = d_m.groups()
                    if len(d) == 1: d = '0' + d
                    if len(m) == 1: m = '0' + m
                    std_date = f"{d}/{m}/{y}"
                    
                    clean_text = re.sub(r'<[^>]+>', ' ', html.unescape(chunk))
                    nums = re.findall(r'\b\d{2,}\b', clean_text)
                    
                    if len(nums) >= 27:
                        prizes = [x[-2:] for x in nums[:27]]
                        if std_date not in parsed_data:
                            parsed_data[std_date] = " ".join(prizes)
            
            if parsed_data: return True, parsed_data, "Truy xuất thành công 300 ngày từ ketqua16.net"
            return False, {}, "Không tìm thấy cấu trúc 27 giải"
        except Exception as e:
            return False, {}, f"Lỗi Crawler: {traceback.format_exc()}"

# ==============================================================================
# 💾 BLOCK 4: QUẢN TRỊ DỮ LIỆU & AUTO-HEAL
# ==============================================================================
class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        if not os.path.exists(Config.DATA_FILE):
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
        except Exception as e: return db, f"🛑 LỖI ĐỌC: {traceback.format_exc()}"

    @staticmethod
    def save_manual_data(date_str, numbers_str):
        res_date = Utils.chuan_hoa_ngay(date_str)
        if not res_date: return "🛑 LỖI NHẬP LIỆU: Ngày không đúng định dạng (VD: 01/08/2026)."
        dt_obj, std_date = res_date
        
        nums = re.findall(r'\d{2}', str(numbers_str))
        if len(nums) < 27: return f"🛑 LỖI NHẬP LIỆU: Chỉ tìm thấy {len(nums)}/27 con số."
        nums = nums[:27]
        
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str) if os.path.exists(Config.DATA_FILE) else pd.DataFrame(columns=["Ngày", "Kết Quả Loto"])
            df = df[df['Ngày'] != std_date]
            new_row = pd.DataFrame({"Ngày": [std_date], "Kết Quả Loto": [" ".join(nums)]})
            df = pd.concat([new_row, df], ignore_index=True)
            df['date_parse'] = pd.to_datetime(df['Ngày'], format="%d/%m/%Y", errors='coerce')
            df = df.sort_values(by='date_parse', ascending=False).drop(columns=['date_parse'])
            df.to_excel(Config.DATA_FILE, index=False)
            return f"✅ NHẬP TAY THÀNH CÔNG: Đã lưu kết quả ngày {std_date} vào Hệ thống!"
        except Exception as e:
            return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

    @staticmethod
    def auto_heal_history():
        db, _ = DatabaseManager.load_db()
        now_vn = Utils.get_vn_time()
        
        success, parsed_data, msg = Crawler.fetch_ketqua16()
        if not success:
            return f"🛑 LỖI CRAWLER:\n{msg}\n👉 Vui lòng dùng chức năng Nhập Tay bên dưới!"
            
        new_rows = []
        healed_count = 0
        for date_str, prizes_str in parsed_data.items():
            res_date = Utils.chuan_hoa_ngay(date_str)
            if res_date:
                dt_obj, std_str = res_date
                if dt_obj.date() > now_vn.date(): continue
                if dt_obj.date() == now_vn.date() and now_vn.hour < 19: continue
                
                if std_str not in db:
                    new_rows.append({"Ngày": std_str, "Kết Quả Loto": prizes_str})
                    db[std_str] = True
                    healed_count += 1

        if new_rows:
            try:
                df_new = pd.DataFrame(new_rows)
                df_old = pd.read_excel(Config.DATA_FILE, dtype=str) if os.path.exists(Config.DATA_FILE) else pd.DataFrame()
                df_final = pd.concat([df_new, df_old], ignore_index=True)
                df_final = df_final.drop_duplicates(subset=['Ngày'], keep='first')
                df_final['date_parse'] = pd.to_datetime(df_final['Ngày'], format="%d/%m/%Y", errors='coerce')
                df_final = df_final.sort_values(by='date_parse', ascending=False).drop(columns=['date_parse'])
                df_final.to_excel(Config.DATA_FILE, index=False)
                return f"✅ AUTO-HEAL: Đã cào và nạp thành công {healed_count} phiên bị mất."
            except Exception as e:
                return f"🛑 LỖI GHI FILE TRUY VẾT:\n{traceback.format_exc()}"
        
        return "✅ AUTO-HEAL: Dữ liệu đã liền mạch, không có lỗ hổng."

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
# 🧠 BLOCK 5: QUANT ENGINE
# ==============================================================================
class QuantEngine:
    @staticmethod
    def get_signal(target_dt, db, mode):
        t_minus_7 = target_dt - timedelta(days=7)
        str_t7 = t_minus_7.strftime("%d/%m/%Y")
        if str_t7 not in db: return None, f"[THIẾU DỮ LIỆU T-7 ({str_t7})] - Hãy Cập nhật/Nhập tay!"
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
        crawl_msg = "ℹ️ Chế độ Offline. Chưa kích hoạt Crawler."
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
        if not date_str or not num_str:
            return "🛑 LỖI: Vui lòng điền đủ Ngày và Chuỗi 27 số.", ""
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
                f"🎚️ CHIẾN LƯỢC ÁP DỤNG: {mode}", ""
            ]
            if dan is None:
                lines.extend([f"🛑 CẢNH BÁO: {msg}.", "👉 LỜI KHUYÊN: Hãy Đồng bộ bằng nút màu Cam hoặc Nhập tay dữ liệu để tiếp tục!"])
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
        except Exception as e: return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

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
        except Exception as e: return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_4_router(audit_type, date_raw, month_raw, mode, pts_per_code_base):
        if audit_type == "Kiểm toán 1 Ngày (Đơn Phiên)":
            return Auditor.phan_he_4_single(date_raw, pts_per_code_base)
        else:
            return Auditor.phan_he_4_monthly_detail(month_raw, mode, pts_per_code_base)

    @staticmethod
    def phan_he_4_single(ngay_raw, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            res = Utils.chuan_hoa_ngay(ngay_raw)
            if not res: return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
            d_obj, ngay_str = res
            if ngay_str not in db: return f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên {ngay_str} chưa cập nhật."
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
                    f" • Đạt {nhay} lượt. Vốn: {chi/1000:,.0f}k | Thu: {thu/1000:,.0f}k",
                    f" 👉 PnL RÒNG: {lai:+,.0f} VNĐ ({st})"
                ]

            for i, mode in enumerate(Config.MODES):
                dan, msg = QuantEngine.get_signal(d_obj, db, mode)
                mode_name = f"CHIẾN LƯỢC {i+1}"
                if dan is None: lines.append(f"🛑 [{mode_name}] {mode}: Thiếu dữ liệu {msg}")
                else: lines.extend(calc_str(dan, mode))
                lines.append("------------------------------------------------------------------------")
            return "\n".join(lines)
        except Exception as e: return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

    @staticmethod
    def phan_he_4_monthly_detail(month_raw, mode, pts_per_code_base):
        try:
            db, _ = DatabaseManager.load_db()
            m = re.match(r'^(\d{1,2})[-/.](\d{4})$', str(month_raw).strip())
            if not m: return "🛑 LỖI ĐỊNH DẠNG: Vui lòng nhập tháng dạng MM/YYYY (VD: 08/2026)."
            thang, nam = int(m.group(1)), int(m.group(2))
            
            valid, err = Utils.check_valid_number(pts_per_code_base, "Vốn")
            if not valid: return err
            base_pts = int(float(pts_per_code_base))
            
            start_dt = datetime(nam, thang, 1)
            max_day = calendar.monthrange(nam, thang)[1]
            end_dt = datetime(nam, thang, max_day)
            
            lines = [
                f"📑 BÁO CÁO CHI TIẾT TỪNG NGÀY: THÁNG {thang:02d}/{nam}",
                f"🎚️ CHIẾN LƯỢC: {mode}",
                "===================================================================================================================",
                f"{'NGÀY':<6} | {'SỐ LƯỢNG & DANH SÁCH MÃ ĐÁNH':<40} | {'VỐN (k)':<9} | {'THU (k)':<9} | {'LÃI/LỖ (k)':<12} | {'ROI':<8}",
                "-------------------------------------------------------------------------------------------------------------------"
            ]
            
            curr = start_dt
            tot_von, tot_thu, tot_lai = 0, 0, 0
            
            while curr <= end_dt:
                ngay_str = curr.strftime("%d/%m/%Y")
                short_date = curr.strftime("%d/%m")
                if ngay_str in db:
                    dan, msg = QuantEngine.get_signal(curr, db, mode)
                    if dan is not None:
                        sl = len(dan)
                        if sl > 0:
                            von = sl * base_pts * Config.COST_PER_POINT
                            nhay = sum(db[ngay_str]["prizes_int"].count(x) for x in dan)
                            thu = nhay * base_pts * Config.WIN_PER_NHAY
                            lai = thu - von
                            roi = (lai / von * 100) if von > 0 else 0
                            
                            tot_von += von
                            tot_thu += thu
                            tot_lai += lai
                            
                            dan_str = " ".join([f"{x:02d}" for x in dan])
                            if len(dan_str) > 30: dan_str = dan_str[:27] + "..."
                            
                            lines.append(f"{short_date:<6} | {sl:>2} mã: {dan_str:<31} | {von/1000:>9,.0f} | {thu/1000:>9,.0f} | {lai/1000:>+12,.0f} | {roi:>+6.1f}%")
                        else:
                            lines.append(f"{short_date:<6} | {'🚫 KHÔNG CÓ TÍN HIỆU ĐẠT CHUẨN':<40} | {'-':<9} | {'-':<9} | {'-':<12} | {'-':<8}")
                    else:
                        lines.append(f"{short_date:<6} | ⚠️ Thiếu dữ liệu T-7/T-1{'':<17} | {'-':<9} | {'-':<9} | {'-':<12} | {'-':<8}")
                else:
                    lines.append(f"{short_date:<6} | ⚪ Chưa có dữ liệu thực tế trên DB{'':<6} | {'-':<9} | {'-':<9} | {'-':<12} | {'-':<8}")
                
                curr += timedelta(days=1)
                
            tot_roi = (tot_lai / tot_von * 100) if tot_von > 0 else 0
            lines.extend([
                "===================================================================================================================",
                f"📝 TỔNG KẾT THÁNG {thang:02d}/{nam}:",
                f"💰 TỔNG VỐN ĐÃ ĐÁNH : {tot_von:,.0f} VNĐ",
                f"💵 TỔNG DOANH THU   : {tot_thu:,.0f} VNĐ",
                f"🚀 LỢI NHUẬN RÒNG   : {tot_lai:+,.0f} VNĐ",
                f"📈 TỶ SUẤT R.O.I    : {tot_roi:+.2f} %"
            ])
            return "\n".join(lines)
        except Exception as e:
            return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

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
            
            lines = [
                "📑 [PHÂN HỆ 5] BÁO CÁO: ĐẠI KẾ TOÁN QUÉT CHU KỲ TỔNG HỢP",
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
            return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

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
        except Exception as e: return f"🛑 LỖI TRUY VẾT (TRACEBACK):\n{traceback.format_exc()}"

# ==============================================================================
# 🎮 BLOCK 7: GIAO DIỆN NGƯỜI DÙNG (UI LAYER)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    _, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    with gr.Blocks(title="XSMB QUANT V36.18 PRO ALGO", theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown("# 🚀 XSMB QUANT V36.18 PRO ALGO")
        gr.Markdown("*(Hệ thống Phân tích Định lượng XSMB Chuyên sâu - Tích hợp Kiểm toán Đơn phiên & Chu kỳ)*")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=Config.MENU_OPTIONS, value=Config.MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            with gr.Row():
                btn_1_sync = gr.Button("⚡ KIỂM TOÁN LẠI DB HIỆN TẠI", variant="secondary")
                btn_1_crawl = gr.Button("🌐 CẬP NHẬT KẾT QUẢ MỚI (TỰ ĐỘNG CÀO 300 NGÀY)", variant="primary")
            
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
            with gr.Row():
                pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                sim_size = gr.Number(label="Quy mô Danh mục (Số lượng mã)", value=12)
            btn_3 = gr.Button("🧪 KHỞI CHẠY MÔ PHỎNG LỢI NHUẬN", variant="primary")
            out_3 = gr.Textbox(label="Báo cáo Quản trị Rủi ro", lines=16)
            btn_3.click(Auditor.phan_he_3_risk, inputs=[pts_3, sim_size], outputs=out_3)
            
        with gr.Column(visible=False) as col_4:
            gr.Markdown("### 🔍 MODULE KIỂM TOÁN CHUYÊN SÂU")
            audit_type = gr.Radio(choices=["Kiểm toán 1 Ngày (Đơn Phiên)", "Kiểm toán Cả Tháng (Chi tiết)"], value="Kiểm toán 1 Ngày (Đơn Phiên)", label="Loại Kiểm toán")
            
            with gr.Row(visible=True) as row_audit_day:
                date_4 = gr.Textbox(label="Ngày Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            
            with gr.Row(visible=False) as row_audit_month:
                month_4 = gr.Textbox(label="Tháng Truy xuất (MM/YYYY)", value=latest_dt_init.strftime('%m/%Y') if latest_dt_init else "")
                mode_4 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
                
            pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
            btn_4 = gr.Button("📡 THỰC THI KIỂM TOÁN", variant="primary")
            out_4 = gr.Textbox(label="Báo cáo Kiểm toán", lines=24)
            
            def toggle_audit(choice):
                return gr.update(visible=choice=="Kiểm toán 1 Ngày (Đơn Phiên)"), gr.update(visible=choice=="Kiểm toán Cả Tháng (Chi tiết)")
            
            audit_type.change(fn=toggle_audit, inputs=audit_type, outputs=[row_audit_day, row_audit_month])
            btn_4.click(Auditor.phan_he_4_router, inputs=[audit_type, date_4, month_4, mode_4, pts_4], outputs=out_4)

        with gr.Column(visible=False) as col_5:
            with gr.Row():
                t1_5 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
                t2_5 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
                pts_5 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_5 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_5 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_5 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền & Max Drawdown", lines=22)
            btn_5.click(Auditor.phan_he_5_range, inputs=[t1_5, t2_5, pts_5, mode_5], outputs=out_5)

        with gr.Column(visible=False) as col_6:
            date_6 = gr.Textbox(label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y') if latest_dt_init else "")
            btn_6 = gr.Button("💾 TRUY XUẤT DỮ LIỆU THÔ (RAW DATA)", variant="primary")
            out_6 = gr.Textbox(label="Log Dữ Liệu Máy Chủ", lines=10)
            btn_6.click(Auditor.phan_he_6_raw, inputs=date_6, outputs=out_6)

        # Kết nối các nút bấm Menu 1
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
