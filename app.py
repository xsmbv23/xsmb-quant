import os
import sys
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V33.1 - DÀN ĐỘNG CHU KỲ T-7 (DEEP AUDITED)
# ==============================================================================
VERSION = "V33.1 DÀN T-7 NHỊP TUẦN (KIỂM TOÁN TỐI CAO)"
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

def chuan_hoa_ngay(ngay_raw):
    if pd.isna(ngay_raw) or not str(ngay_raw).strip(): return None
    try:
        s = str(ngay_raw).strip().split()[0].replace('-', '/').replace('.', '/')
        parts = [p for p in s.split('/') if p]
        d, m, y = parts[0], parts[1], parts[2]
        if len(d) == 4: y, m, d = d, m, y
        if len(d) == 1: d = "0" + d
        if len(m) == 1: m = "0" + m
        if len(y) == 2: y = "20" + y
        str_chuan = f"{d}/{m}/{y}"
        return datetime.strptime(str_chuan, "%d/%m/%Y"), str_chuan
    except: return None

def lay_max_days(thang, nam):
    if thang == 2: return 29 if (nam % 4 == 0 and (nam % 100 != 0 or nam % 400 == 0)) else 28
    elif thang in [4, 6, 9, 11]: return 30
    return 31

def doc_database_tu_excel():
    db = {}
    if not os.path.exists(DATA_FILE): 
        return db, f"🛑 CRITICAL ERROR: File '{DATA_FILE}' không tồn tại."
    try:
        df = pd.read_excel(DATA_FILE, dtype=str)
        col_ngay = df.columns[0]; col_loto = df.columns[1]
        for _, row in df.iterrows():
            res_date = chuan_hoa_ngay(row[col_ngay])
            if not res_date: continue
            dt_obj, ngay_str = res_date
            loto_raw = str(row[col_loto]).strip()
            loto_list = [int(x.strip()[-2:]) for x in loto_raw.replace(',', ' ').replace(';', ' ').split() if x.strip().isdigit()]
            if len(loto_list) >= 27:
                db[ngay_str] = {
                    'date_obj': dt_obj,
                    'date_str': ngay_str,
                    'prizes_int': loto_list[:27]
                }
        return db, f"🟢 KIỂM TOÁN DB: Nạp thành công {len(db)} ngày hợp lệ."
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db: return datetime(2026, 7, 21), datetime(2026, 7, 22)
    max_dt = max(info['date_obj'] for info in db.values())
    return max_dt, max_dt + timedelta(days=1)

# ==============================================================================
# 🎯 LÕI THUẬT TOÁN ĐỘNG: BẮT NHỊP T-7 (ĐÃ LỌC TRÙNG SỐ)
# ==============================================================================
def tim_dan_t7(target_dt, db):
    t_minus_7 = target_dt - timedelta(days=7)
    ngay_str_t7 = t_minus_7.strftime("%d/%m/%Y")
    
    if ngay_str_t7 not in db: 
        return []

    loto_27_tuantruoc = db[ngay_str_t7]['prizes_int']
    # Ép kiểu set() để triệt tiêu các số về 2, 3 nháy thành 1 số duy nhất
    dan_du_doan = sorted(list(set(loto_27_tuantruoc)))
    
    return dan_du_doan

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN (ĐÃ VÁ LỖI ZERO-DIVISION VÀ RÁC TƯƠNG LAI)
# ==============================================================================

def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    res = f"📡 HỆ THỐNG V33.1 (BẮT NHỊP T-7 TUẦN TRƯỚC - FINAL AUDIT):\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Tình trạng DB : {msg}\n"
    res += f"• Cập nhật cuối : 📅 [{latest_dt.strftime('%d/%m/%Y')}]\n"
    res += f"• Lịch tính toán: 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]\n"
    return res, f"#### CẤP LỆNH KỲ TIẾP THEO: {next_predict_dt.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
        base_pts = int(pts_per_code_base)
        
        # FIX LỖI CRASH: Bắt lỗi nhập mức cược <= 0
        if base_pts <= 0:
            return "🛑 LỖI KẾ TOÁN: Mức cược phải lớn hơn 0."
        
        dan = tim_dan_t7(next_predict_dt, db)
        if not dan:
            ngay_t7 = (next_predict_dt - timedelta(days=7)).strftime('%d/%m/%Y')
            return f"🎯 LỆNH KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n=======================================================\n🛑 CẢNH BÁO: Dữ liệu tham chiếu của tuần trước ({ngay_t7}) bị khuyết. HỆ THỐNG KHÓA LỆNH ĐỂ BẢO TOÀN VỐN."
            
        so_luong_lo = len(dan)
        von_ngay = so_luong_lo * base_pts * COST_PER_POINT
        dan_str = " ".join([f"{x:02d}" for x in dan])
        
        doanh_thu_1_nhay = base_pts * WIN_PER_NHAY
        diem_hoa_von_nhay = math.ceil(von_ngay / doanh_thu_1_nhay)
        
        res = f"🎯 XUẤT LỆNH V33.1 CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"=======================================================\n"
        res += f"📋 DÀN T-7 ({so_luong_lo} SỐ ĐỘC BẢN TỪ KẾT QUẢ TUẦN TRƯỚC):\n"
        res += f" [ {dan_str} ]\n"
        res += f"=======================================================\n"
        res += f" • Khối lượng Cược: {base_pts} điểm / 1 con lô\n"
        res += f"-------------------------------------------------------\n"
        res += f"💰 TỔNG TIỀN PHẢI XUẤT: {von_ngay:,.0f} VND\n"
        res += f"💡 KỊCH BẢN BẢO TOÀN: Cần trúng ÍT NHẤT {diem_hoa_von_nhay} Nháy để có Lãi Ròng.\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 2: {e}"

def web_phan_he_3_risk_audit(base_pts, sim_size):
    try:
        base_pts = int(base_pts)
        so_luong_lo = int(sim_size)
        if base_pts <= 0 or so_luong_lo <= 0: return "🛑 LỖI: Vui lòng nhập số liệu lớn hơn 0."
        
        von_ngay = so_luong_lo * base_pts * COST_PER_POINT
        
        res = f"📊 BẢNG MÔ PHỎNG LÃI LỖ GIẢ ĐỊNH (KHI DÀN T-7 CÓ KHOẢNG {so_luong_lo} SỐ ĐỘC BẢN)\n"
        res += f"TỔNG CHI PHÍ 1 NGÀY: {von_ngay:,.0f} VNĐ (Cược: {base_pts}đ/con)\n"
        res += f"====================================================================\n"
        res += f" KẾT QUẢ NHÁY | DOANH THU THU VỀ | LÃI / LỖ RÒNG | TRẠNG THÁI\n"
        res += f"====================================================================\n"
        
        for nhay in range(max(1, int(so_luong_lo * 0.1)), int(so_luong_lo * 0.7) + 2):
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_ngay
            if lai > 0: status = "🟢 LÃI RÒNG"
            elif lai == 0: status = "🟡 HÒA VỐN"
            else: status = "🔴 LỖ"
            res += f" Về {nhay:>2} nháy  | {thuong:>16,.0f} | {lai:>+13,.0f} | {status}\n"
            
        res += f"====================================================================\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 3: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày (DD/MM/YYYY)."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Ngày {ngay_str} không có trong Excel."
            
        base_pts = int(pts_per_code_base)
        lo_to_27 = db[ngay_str]['prizes_int']
        
        dan = tim_dan_t7(d_obj, db)
        if not dan: 
            ngay_t7 = (d_obj - timedelta(days=7)).strftime('%d/%m/%Y')
            return f"📡 KIỂM TOÁN NGÀY {ngay_str}\n=======================================================\n🔭 LỖI DỮ LIỆU T-7 ({ngay_t7} bị khuyết). KHÔNG THỂ BẮT NHỊP TUẦN. BỎ QUA GIAO DỊCH."
            
        so_luong_lo = len(dan)
        von_ngay = so_luong_lo * base_pts * COST_PER_POINT
        nhay = sum(lo_to_27.count(x) for x in dan)
        thuong = nhay * base_pts * WIN_PER_NHAY
        lai = thuong - von_ngay
        
        if lai > 0: status = "🟢 WIN (CÓ LÃI)"
        elif lai == 0: status = "🟡 DRAW (HÒA VỐN)"
        else: status = "🔴 LOSS (LỖ PHIÊN)"
        
        report = f"📡 BÁO CÁO KIỂM TOÁN NGÀY: {ngay_str}\n"
        report += f"=======================================================\n"
        report += f"📋 DÀN T-7 ({so_luong_lo} SỐ) ĐÃ ĐÁNH: " + " ".join([f"{x:02d}" for x in dan]) + "\n"
        report += f" • Điểm Cược/con: {base_pts} điểm\n"
        report += f" • KẾT QUẢ      : x{nhay} nháy -> {status}\n"
        report += f"-------------------------------------------------------\n"
        report += f"💰 CHI PHÍ      : {von_ngay:,.0f} VND\n"
        report += f"📈 DOANH THU    : {thuong:,.0f} VND\n"
        report += f"💵 LÃI/LỖ RÒNG  : {lai:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 4: {e}"

def web_phan_he_5_monthly_audit(month, year, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        base_pts = int(pts_per_code_base)
        max_dt, _ = lay_ngay_chot_tu_excel(db) # Lấy ngày cuối cùng có dữ liệu
        
        start_dt = datetime(nam, thang, 1)
        end_dt = datetime(nam, thang, lay_max_days(thang, nam))
        
        # FIX LỖI RÁC TƯƠNG LAI: Không quét các ngày chưa có dữ liệu
        if end_dt > max_dt: end_dt = max_dt
        if start_dt > end_dt: return f"🛑 BÁO CÁO: Tháng {thang:02d}/{nam} hoàn toàn chưa có dữ liệu."
        
        report = f"📊 AUDIT TÀI CHÍNH THÁNG {thang:02d}/{nam} (CHIẾN THUẬT BẮT NHỊP T-7):\n"
        report += f"===================================================================================================================\n"
        report += f"{'NGÀY':<10} | {'TRẠNG THÁI':<15} | {'SỐ LÔ':<6} | {'CHI PHÍ':<12} | {'NHÁY':<5} | {'DOANH THU':<12} | {'LÃI / LỖ':<15} | {'LŨY KẾ':<12}\n"
        report += f"===================================================================================================================\n"
        
        luy_ke_thang = 0
        cash_thu = 0; cash_chi = 0; total_phien_danh = 0
        curr = start_dt
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            
            if ngay_str not in db:
                report += f"{ngay_str:<10} | {'⚠️ MISSING DATA':<15} | {'-':<6} | {'-':<12} | {'-':<5} | {'-':<12} | {'-':<15} | {luy_ke_thang:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
            dan = tim_dan_t7(curr, db)
            if not dan:
                report += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<15} | {'0':<6} | {'-':<12} | {'-':<5} | {'-':<12} | {'[KHUYẾT T-7]':<15} | {luy_ke_thang:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
            total_phien_danh += 1
            so_luong_lo = len(dan)
            von_1_phien = so_luong_lo * base_pts * COST_PER_POINT
            
            lo_to_27 = db[ngay_str]['prizes_int']
            nhay = sum(lo_to_27.count(x) for x in dan)
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_1_phien
            
            luy_ke_thang += lai
            cash_chi += von_1_phien
            cash_thu += thuong
            
            if lai > 0: status_str = "🟢 WIN"
            elif lai == 0: status_str = "🟡 HÒA"
            else: status_str = "🔴 LOSS"
            
            report += f"{ngay_str:<10} | {status_str:<15} | {so_luong_lo:<6} | {von_1_phien:<12,.0f} | {nhay:<5} | {thuong:<12,.0f} | {lai:>+15,.0f} | {luy_ke_thang:>+12,.0f}\n"
            
            curr += timedelta(days=1)
            
        report += f"===================================================================================================================\n"
        report += f"📝 ĐỐI SOÁT KẾ TOÁN (BẮT NHỊP T-7):\n"
        report += f"• TỔNG SỐ NGÀY ĐỦ ĐIỀU KIỆN ĐÁNH : {total_phien_danh} ngày.\n"
        report += f"• TỔNG DÒNG TIỀN XUẤT NHẬP       : Chi {cash_chi:,.0f} đ | Thu {cash_thu:,.0f} đ\n"
        report += f"• TỔNG LỢI NHUẬN RÒNG CHỐT SỔ    : {luy_ke_thang:+,.0f} VND\n"
        
        return report
    except Exception as e: return f"🛑 LỖI TAB 5: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi định dạng ngày nhập liệu."
        start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
        
        base_pts = int(pts_per_code_base)
        max_dt, _ = lay_ngay_chot_tu_excel(db)
        
        # FIX LỖI RÁC TƯƠNG LAI
        if end_dt > max_dt: end_dt = max_dt
        if start_dt > end_dt: return "🛑 LỖI: Khoảng thời gian tra cứu hoàn toàn không có dữ liệu."
        
        rep = f"📈 BÁO CÁO KIỂM TOÁN CHU KỲ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')}\n"
        rep += "="*110 + "\n"
        rep += f"{'NGÀY':<10} | {'TRẠNG THÁI':<15} | {'SỐ LÔ':<6} | {'CHI PHÍ HÔM NAY':<16} | {'NHÁY':<5} | {'LÃI / LỖ PHIÊN':<15} | {'LŨY KẾ':<12}\n"
        rep += "="*110 + "\n"
        
        curr = start_dt
        total_lai = 0; trades = 0; k_thang = 0; k_thua = 0; k_hoa = 0
        cash_thu = 0; cash_chi = 0  
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            
            if ngay_str not in db:
                rep += f"{ngay_str:<10} | {'⚠️ MISSING DATA':<15} | {'-':<6} | {'-':<16} | {'-':<5} | {'-':<15} | {total_lai:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
            dan = tim_dan_t7(curr, db)
            
            if not dan:
                rep += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<15} | {'0':<6} | {'-':<16} | {'-':<5} | {'[KHUYẾT T-7]':<15} | {total_lai:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                    
            trades += 1
            so_luong_lo = len(dan)
            von_1_phien = so_luong_lo * base_pts * COST_PER_POINT
            
            lo_to_27 = db[ngay_str]['prizes_int']
            nhay = sum(lo_to_27.count(x) for x in dan)
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_1_phien
            
            total_lai += lai
            cash_chi += von_1_phien
            cash_thu += thuong
            
            if lai > 0: 
                k_thang += 1
                status_str = "🟢 WIN"
            elif lai == 0:
                k_hoa += 1
                status_str = "🟡 HÒA"
            else: 
                k_thua += 1
                status_str = "🔴 LOSS"
                
            rep += f"{ngay_str:<10} | {status_str:<15} | {so_luong_lo:<6} | {von_1_phien:<16,.0f} | {nhay:<5} | {lai:>+15,.0f} | {total_lai:>+12,.0f}\n"
            
            curr += timedelta(days=1)
            
        rep += "="*110 + "\n"
        rep += f"📊 HIỆU SUẤT BẮT NHỊP T-7: Tổng số ngày xuất lệnh: {trades} | Số ngày Lãi: {k_thang} | Lỗ: {k_thua} | Hòa: {k_hoa}\n"
        rep += f"📝 ĐỐI SOÁT DÒNG TIỀN (CASH FLOW): TỔNG CHI = {cash_chi:,.0f} đ | TỔNG THU = {cash_thu:,.0f} đ\n"
        rep += f"💰 TỔNG LỢI NHUẬN RÒNG CHU KỲ TÍNH TOÁN: {total_lai:+,.0f} VNĐ\n"
        return rep
    except Exception as e: return f"🛑 LỖI TAB 6: {e}"

def web_phan_he_7_raw_db_lookup(ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        _, ngay_str = res
        if ngay_str not in db: return f"🛑 NO DATA: Ngày {ngay_str} chưa được ghi nhận trong Excel."
            
        lo_to_raw = db[ngay_str]['prizes_int']
        lo_to_sorted = sorted([f"{x:02d}" for x in lo_to_raw])
        report = f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY {ngay_str}:\n"
        report += "🎰 27 Giải ma trận phẳng:\n"
        for idx, lo in enumerate(lo_to_sorted): 
            report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
        return report
    except Exception as e: return f"🛑 LỖI TAB 7: {e}"

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO V33.1 
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V33.1") as demo:
    gr.Markdown("# 🚀 XSMB QUANT V33.1 — CHIẾN THUẬT BẮT NHỊP TUẦN T-7 (DEEP AUDITED)")
    gr.Markdown("*(Sao chép toàn bộ kết quả của đúng ngày này tuần trước để làm số dự đoán. Số trùng gộp làm 1)*")
    
    with gr.Tab("🔄 [1] Cập Nhật Dữ Liệu"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP & KIỂM TOÁN DB", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=5)
        
    with gr.Tab("🎯 [2] Lệnh Chốt Kế Tiếp"):
        title_2 = gr.Markdown(f"#### Lệnh cho kỳ quay tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ (Điểm/1 con lô)", value=10)
        btn_2 = gr.Button("🔍 KIẾT XUẤT LỆNH DÀN T-7", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V33.1", lines=14)
        btn_2.click(web_phan_he_2_predict, inputs=[pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Bảng Vốn Khung Nháy"):
        with gr.Row():
            pts_3 = gr.Number(label="Mức cược (Điểm/1 con lô)", value=10)
            sim_size = gr.Number(label="Số lượng Lô giả định (Trung bình tuần là 21-24 số)", value=22)
        btn_3 = gr.Button("🧪 MÔ PHỎNG LỢI NHUẬN TÙY BIẾN", variant="primary")
        out_3 = gr.Textbox(label="Phân Tích Hòa Vốn & Có Lãi", lines=16)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[pts_3, sim_size], outputs=out_3)

    with gr.Tab("🔍 [4] Kiểm Toán Đơn Ngày"):
        with gr.Row():
            date_4 = gr.Textbox(label="Ngày Truy Xuất (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_4 = gr.Number(label="Mức cược (Điểm/con)", value=10)
        btn_4 = gr.Button("📡 KIỂM TOÁN TỨC THỜI", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Lãi/Lỗ Trong Ngày", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Kiểm Toán Theo Tháng"):
        with gr.Row():
            m_5 = gr.Slider(minimum=1, maximum=12, step=1, label="Chọn Tháng", value=latest_dt_init.month)
            y_5 = gr.Number(label="Năm", value=latest_dt_init.year)
            pts_5 = gr.Number(label="Mức cược (Điểm/con)", value=10)
        btn_5 = gr.Button("📊 KIỂM TOÁN DÒNG TIỀN THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Audit", lines=20)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Kiểm Toán Tổng Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_6 = gr.Number(label="Mức cược (Điểm/con)", value=10)
        btn_6 = gr.Button("📈 KIỂM TOÁN TOÀN BỘ LỊCH SỬ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền", lines=20)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Khớp Lệnh Lô Tô Gốc"):
        date_7 = gr.Textbox(label="Nhập ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRUY XUẤT RAW DATA EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Thô", lines=8)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
