import calendar
from datetime import datetime, timedelta
import math
import os
import re
import sys
import traceback
import gradio as gr
import numpy as np
import pandas as pd

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG & BIẾN MÔI TRƯỜNG (SYSTEM CONFIG)
# ==============================================================================
class Config:
    VERSION = "V36.2 PRO ALGO (KIẾN TRÚC ĐÓNG GÓI MODULAR & KHÁNG ÂM EV)"
    DATA_FILE = "Ket_Qua_Loto27.xlsx"
    COST_PER_POINT = 21700
    WIN_PER_NHAY = 80000
    MODES = [
        "🚀 Giao Dịch T-7 ĐỘNG LƯỢNG TỐI ƯU (Cải Tiến Quant V36.2)",
        "Giao Dịch Toàn Bộ T-7 (Chuẩn Gốc)",
        "Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
        "Chỉ Giao Dịch SỐ KHUYẾT (Không Rơi/Đảo)",
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
# 💾 BLOCK 3: QUẢN TRỊ CƠ SỞ DỮ LIỆU (DATABASE MANAGER)
# ==============================================================================
class DatabaseManager:
    @staticmethod
    def load_db():
        db = {}
        if not os.path.exists(Config.DATA_FILE):
            return db, f"🛑 LỖI HỆ THỐNG: Không tìm thấy '{Config.DATA_FILE}'."
        try:
            df = pd.read_excel(Config.DATA_FILE, dtype=str)
            if df.shape[1] < 2:
                return db, "🛑 LỖI CẤU TRÚC: File dữ liệu thiếu cột."
            
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
                    }
            msg = f"🟢 ĐỒNG BỘ THÀNH CÔNG {len(db)} PHIÊN GIAO DỊCH."
            if dup_count > 0: msg += f" (Phát hiện {dup_count} dòng ghi đè)."
            return db, msg
        except Exception as e:
            return db, f"🛑 LỖI TRUY XUẤT DỮ LIỆU: {e}"

    @staticmethod
    def get_boundaries(db):
        if not db:
            today = datetime.now()
            return today, today, today + timedelta(days=1)
        all_dates = [info["date_obj"] for info in db.values()]
        return min(all_dates), max(all_dates), max(all_dates) + timedelta(days=1)

# ==============================================================================
# 🧠 BLOCK 4: LÕI THUẬT TOÁN QUANT (ALGORITHM ENGINE)
# ==============================================================================
class QuantEngine:
    @staticmethod
    def get_signal(target_dt, db, mode):
        t_minus_7 = target_dt - timedelta(days=7)
        str_t7 = t_minus_7.strftime("%d/%m/%Y")
        
        if str_t7 not in db: return None, f"[THIẾU DỮ LIỆU T-7 ({str_t7})]"
        
        prizes_t7 = db[str_t7]["prizes_int"]
        dan_t7 = set(prizes_t7)

        # ⚙️ Tách biệt thuật toán để không chạm vào phần gốc
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
# 📊 BLOCK 5: PHÂN HỆ KIỂM TOÁN TÀI CHÍNH (AUDIT & REPORTING)
# ==============================================================================
class Auditor:
    @staticmethod
    def phan_he_1_sync():
        db, msg = DatabaseManager.load_db()
        _, latest_dt, next_predict_dt = DatabaseManager.get_boundaries(db)
        lines = [
            "📑 [PHÂN HỆ 1] BÁO CÁO: ĐỒNG BỘ CƠ SỞ DỮ LIỆU",
            "=================================================================================",
            f"• Phiên bản hệ thống : {Config.VERSION}",
            f"• Trạng thái Dữ liệu : {msg}",
            f"• Phiên cập nhật cuối: 📅 [{latest_dt.strftime('%d/%m/%Y')}]",
            f"• Lịch phân tích tới : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
        ]
        return "\n".join(lines), f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ: {next_predict_dt.strftime('%d/%m/%Y')}"

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
    def phan_he_6_range(tu_ngay_raw, den_ngay_raw, pts_per_code_base, mode):
        try:
            db, _ = DatabaseManager.load_db()
            res1, res2 = Utils.chuan_hoa_ngay(tu_ngay_raw), Utils.chuan_hoa_ngay(den_ngay_raw)
            if not res1 or not res2: return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
            
            start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
            valid, err = Utils.check_valid_number(pts_per_code_base, "Khối lượng vốn")
            if not valid: return err
            
            base_pts = Utils.safe_int(pts_per_code_base)
            min_dt, max_dt, _ = DatabaseManager.get_boundaries(db)
            if start_dt < min_dt: start_dt = min_dt
            if end_dt > max_dt: end_dt = max_dt
            if start_dt > end_dt: return "🛑 LỖI: Khoảng thời gian tra cứu nằm ngoài Phạm vi Dữ liệu."
            
            lines = [
                "📑 [PHÂN HỆ 6] BÁO CÁO: ĐẠI KẾ TOÁN QUÉT CHU KỲ",
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
                
            if not daily_records: return "\n".join(lines) + "\n🛑 KHÔNG CÓ PHIÊN NÀO ĐẠT ĐIỀU KIỆN XUẤT LỆNH."
            
            df_rec = pd.DataFrame(daily_records)
            
            # CẤP ĐỘ KIỂM TOÁN 1: THEO NĂM
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
                
            # CẤP ĐỘ KIỂM TOÁN 2: THEO THÁNG
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
            
            # CẤP ĐỘ KIỂM TOÁN 3: MINH BẠCH RỦI RO MAX DRAWDOWN (Tuyệt đối không tô hồng)
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
            return "\n".join(lines)
        except Exception as e:
            return f"🛑 LỖI PHÂN HỆ 6: {traceback.format_exc()}"

# ==============================================================================
# 🎮 BLOCK 6: GIAO DIỆN NGƯỜI DÙNG (UI LAYER)
# ==============================================================================
def create_ui():
    db_init, _ = DatabaseManager.load_db()
    _, latest_dt_init, next_predict_dt_init = DatabaseManager.get_boundaries(db_init)

    MENU_OPTIONS = ["🔄 1. ĐỒNG BỘ DỮ LIỆU", "🎯 2. KHUYẾN NGHỊ LỆNH", "📈 3. PHÂN TÍCH CHU KỲ (FULL)"]

    with gr.Blocks(title="XSMB QUANT V36.2 PRO") as demo:
        gr.Markdown("# 🚀 XSMB QUANT V36.2 — KIẾN TRÚC ĐÓNG GÓI MODULAR")
        gr.Markdown("*(Đã cấu trúc hóa theo phương pháp Hướng đối tượng OOP. Chống sập ứng dụng 100%.)*")
        
        with gr.Row():
            nav_menu = gr.Radio(choices=MENU_OPTIONS, value=MENU_OPTIONS[0], label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH")
            
        with gr.Column(visible=True) as col_1:
            btn_1 = gr.Button("⚡ KHỞI CHẠY KIỂM TOÁN VÀ ĐỒNG BỘ DỮ LIỆU", variant="primary")
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
                t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
                t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime('%d/%m/%Y'))
                pts_6 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
                mode_6 = gr.Radio(choices=Config.MODES, value=Config.MODES[0], label="Chiến lược Áp dụng")
            btn_6 = gr.Button("📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary")
            out_6 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền", lines=22)
            btn_6.click(Auditor.phan_he_6_range, inputs=[t1_6, t2_6, pts_6, mode_6], outputs=out_6)

        btn_1.click(Auditor.phan_he_1_sync, outputs=[out_1, title_2])

        def update_visibility(choice):
            return [
                gr.update(visible=(choice == MENU_OPTIONS[0])),
                gr.update(visible=(choice == MENU_OPTIONS[1])),
                gr.update(visible=(choice == MENU_OPTIONS[2])),
            ]
        nav_menu.change(fn=update_visibility, inputs=[nav_menu], outputs=[col_1, col_2, col_3])
    return demo

if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False, theme=gr.themes.Soft())
