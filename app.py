import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V31.0 - DÀN 24 LÔ FLAT BETTING (STRICT AUDIT)
# ==============================================================================
VERSION = "V31.0 DÀN 24 SỐ (KẾ TOÁN MINH BẠCH)"
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

# Đánh đều tiền (Flat Betting), không gấp thếp
SO_LUONG_LO = 24

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
        return db, f"🛑 CRITICAL ERROR: Hệ thống không tìm thấy file '{DATA_FILE}'."
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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY. DỮ LIỆU ĐÃ ĐƯỢC TOÀN VẸN HÓA."
    except Exception as e: return db, f"🛑 CRITICAL ERROR KHI ĐỌC FILE: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db: return datetime(2026, 7, 21), datetime(2026, 7, 22)
    max_dt = max(info['date_obj'] for info in db.values())
    return max_dt, max_dt + timedelta(days=1)

# ==============================================================================
# 🎯 LÕI THUẬT TOÁN: TÌM 24 SỐ CÓ XÁC SUẤT ĐIỂM CAO NHẤT
# ==============================================================================
def tim_24_con_lo(target_dt, db):
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    
    # Ép buộc lùi 30 ngày quá khứ để chống Look-ahead Bias
    for _ in range(30):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db: hist_days.append(db[s_str]['prizes_int'])
        else: hist_days.append([]) 
        curr_t -= timedelta(days=1)

    # Từ chối bốc số mù nếu ngày T-1 bị thiếu dữ liệu
    if not hist_days[0]: return []

    scores = {i: 0 for i in range(100)}
    
    # 1. Tần suất nhịp nổ 30 ngày
    for day_res in hist_days:
        for num in day_res:
            scores[num] += 1
            
    # 2. Cấp thêm điểm cho Lô Rơi (nổ hôm trước)
    for num in hist_days[0]:
        scores[num] += 3
        
    # 3. Trảm Quyết Lô Gan (Chặn đánh lô tịt ngòi quá 10 ngày)
    for num in range(100):
        is_gan = True
        for i in range(10):
            if i < len(hist_days) and num in hist_days[i]:
                is_gan = False
                break
        if is_gan:
            scores[num] -= 20
            
    # Sắp xếp và trích xuất đúng 24 số độc bản
    sorted_nums = sorted(scores.items(), key=lambda x: (x[1], x[0]), reverse=True)
    top_24 = [x[0] for x in sorted_nums[:SO_LUONG_LO]]
    return sorted(top_24)

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN (KIỂM TOÁN CHUẨN)
# ==============================================================================

def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    res = f"📡 HỆ THỐNG V31.0 (DÀN {SO_LUONG_LO} SỐ - KHÔNG GẤP THẾP):\n"
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
        
        dan_24 = tim_24_con_lo(next_predict_dt, db)
        if not dan_24:
            return f"🎯 LỆNH KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n=======================================================\n🛑 CẢNH BÁO: Không có dữ liệu lịch sử chuẩn để đo nhịp. CẤM GIAO DỊCH."
            
        von_ngay = SO_LUONG_LO * base_pts * COST_PER_POINT
        dan_str = " ".join([f"{x:02d}" for x in dan_24])
        
        res = f"🎯 XUẤT LỆNH V31.0 CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"=======================================================\n"
        res += f"📋 DÀN {SO_LUONG_LO} SỐ TỐI ƯU:\n"
        res += f" [ {dan_str} ]\n"
        res += f"=======================================================\n"
        res += f" • Kỷ luật vốn    : Flat Betting (Đánh bằng tiền)\n"
        res += f" • Khối lượng Cược: {base_pts} điểm / 1 con lô\n"
        res += f"-------------------------------------------------------\n"
        res += f"💰 TỔNG TIỀN PHẢI XUẤT: {von_ngay:,.0f} VND\n"
        res += f"💡 KỊCH BẢN ĐIỂM HÒA VỐN: 7 Nháy (Thu về {7 * base_pts * WIN_PER_NHAY:,.0f} VND)\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 2: {e}"

def web_phan_he_3_risk_audit(base_pts):
    try:
        base_pts = int(base_pts)
        von_ngay = SO_LUONG_LO * base_pts * COST_PER_POINT
        
        res = f"📊 BẢNG TÍNH LÃI LỖ THEO NHÁY (DÀN {SO_LUONG_LO} SỐ)\n"
        res += f"TỔNG CHI PHÍ 1 NGÀY: {von_ngay:,.0f} VNĐ (Mức cược: {base_pts}đ/con)\n"
        res += f"====================================================================\n"
        res += f" KẾT QUẢ NHÁY | DOANH THU THU VỀ | LÃI / LỖ RÒNG | TRẠNG THÁI\n"
        res += f"====================================================================\n"
        
        for nhay in range(3, 13):
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_ngay
            if lai > 0: status = "🟢 LÃI RÒNG"
            elif lai == 0: status = "🟡 HÒA VỐN"
            else: status = "🔴 LỖ"
            res += f" Về {nhay:>2} nháy  | {thuong:>16,.0f} | {lai:>+13,.0f} | {status}\n"
            
        res += f"====================================================================\n"
        res += f"⚠️ LÝ THUYẾT: Xác suất lồng cầu trung bình nhả ~6.48 nháy cho 24 số.\nSếp cần 7 nháy để bắt đầu có lãi.\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 3: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày (DD/MM/YYYY)."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Ngày {ngay_str} không tồn tại trong Excel."
            
        base_pts = int(pts_per_code_base)
        lo_to_27 = db[ngay_str]['prizes_int']
        
        dan_24 = tim_24_con_lo(d_obj, db)
        if not dan_24: return f"📡 KIỂM TOÁN NGÀY {ngay_str}\n=======================================================\n🔭 LỊCH SỬ CHƯA ĐỦ. GHI NHẬN ĐỨNG NGOÀI."
            
        von_ngay = SO_LUONG_LO * base_pts * COST_PER_POINT
        nhay = sum(lo_to_27.count(x) for x in dan_24)
        thuong = nhay * base_pts * WIN_PER_NHAY
        lai = thuong - von_ngay
        
        status = "🟢 WIN (CÓ LÃI)" if lai > 0 else "🔴 LOSS (LỖ PHIÊN)"
        
        report = f"📡 BÁO CÁO KIỂM TOÁN NGÀY: {ngay_str}\n"
        report += f"=======================================================\n"
        report += f"📋 DÀN 24 SỐ ĐÃ ĐÁNH: " + " ".join([f"{x:02d}" for x in dan_24]) + "\n"
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
        von_1_phien = SO_LUONG_LO * base_pts * COST_PER_POINT
        
        start_dt = datetime(nam, thang, 1)
        end_dt = datetime(nam, thang, lay_max_days(thang, nam))
        
        report = f"📊 AUDIT TÀI CHÍNH THÁNG {thang:02d}/{nam} (ĐÁNH THEO NGÀY KHÔNG GỒNG):\n"
        report += f"========================================================================================================\n"
        report += f"{'NGÀY':<10} | {'TRẠNG THÁI':<15} | {'CHI PHÍ':<12} | {'SỐ NHÁY':<7} | {'DOANH THU':<12} | {'LÃI / LỖ PHIÊN':<15} | {'LŨY KẾ':<12}\n"
        report += f"========================================================================================================\n"
        
        luy_ke_thang = 0
        cash_thu = 0; cash_chi = 0
        curr = start_dt
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            dan_24 = tim_24_con_lo(curr, db)
            
            if not dan_24:
                report += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<15} | {0:<12} | {'-':<7} | {0:<12} | {0:<15} | {luy_ke_thang:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                    
            if ngay_str in db:
                lo_to_27 = db[ngay_str]['prizes_int']
                nhay = sum(lo_to_27.count(x) for x in dan_24)
                thuong = nhay * base_pts * WIN_PER_NHAY
                lai = thuong - von_1_phien
                
                luy_ke_thang += lai
                cash_chi += von_1_phien
                cash_thu += thuong
                
                status_str = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                report += f"{ngay_str:<10} | {status_str:<15} | {von_1_phien:<12,.0f} | {nhay:<7} | {thuong:<12,.0f} | {lai:>+15,.0f} | {luy_ke_thang:>+12,.0f}\n"
                
            curr += timedelta(days=1)
            
        report += f"========================================================================================================\n"
        report += f"📝 ĐỐI SOÁT KẾ TOÁN (FLAT BETTING):\n"
        report += f"• Vì đánh dứt điểm hằng ngày, không có vốn gồng, nên Lợi Nhuận Chốt Sổ và Dòng Tiền là ĐỒNG NHẤT 100%.\n"
        report += f"• TỔNG DÒNG TIỀN XUẤT NHẬP: Chi {cash_chi:,.0f} đ | Thu {cash_thu:,.0f} đ\n"
        report += f"• TỔNG LỢI NHUẬN RÒNG    : {luy_ke_thang:+,.0f} VND\n"
        
        return report
    except Exception as e: return f"🛑 LỖI TAB 5: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi định dạng ngày nhập liệu."
        start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
        
        base_pts = int(pts_per_code_base)
        von_1_phien = SO_LUONG_LO * base_pts * COST_PER_POINT
        
        rep = f"📈 BÁO CÁO KIỂM TOÁN CHU KỲ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')}\n"
        rep += "="*110 + "\n"
        rep += f"{'NGÀY':<10} | {'TRẠNG THÁI':<15} | {'CHI PHÍ HÔM NAY':<16} | {'SỐ NHÁY':<7} | {'LÃI / LỖ PHIÊN':<15} | {'LŨY KẾ':<12}\n"
        rep += "="*110 + "\n"
        
        curr = start_dt
        total_lai = 0; trades = 0; k_thang = 0; k_thua = 0
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            dan_24 = tim_24_con_lo(curr, db)
            
            if not dan_24:
                rep += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<15} | {0:<16} | {'-':<7} | {0:<15} | {total_lai:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                    
            if ngay_str in db:
                trades += 1
                lo_to_27 = db[ngay_str]['prizes_int']
                nhay = sum(lo_to_27.count(x) for x in dan_24)
                thuong = nhay * base_pts * WIN_PER_NHAY
                lai = thuong - von_1_phien
                total_lai += lai
                
                if lai > 0: k_thang += 1
                else: k_thua += 1
                
                status_str = "🟢 WIN" if lai > 0 else "🔴 LOSS"
                rep += f"{ngay_str:<10} | {status_str:<15} | {von_1_phien:<16,.0f} | {nhay:<7} | {lai:>+15,.0f} | {total_lai:>+12,.0f}\n"
                
            curr += timedelta(days=1)
            
        rep += "="*110 + "\n"
        rep += f"📊 HIỆU SUẤT ĐÁNH DÀN: Tổng số phiên đánh: {trades} | Ngày có lãi: {k_thang} | Ngày lỗ: {k_thua}\n"
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
# 🎨 GIAO DIỆN GRADIO V31.0 (KHÓA SLIDER AN TOÀN)
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V31.0") as demo:
    gr.Markdown("# 🚀 XSMB QUANT V31.0 — ĐÁNH DÀN 24 SỐ (FLAT BETTING & STRICT AUDIT)")
    
    with gr.Tab("🔄 [1] Cập Nhật Dữ Liệu"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP & KIỂM TOÁN DB", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=5)
        
    with gr.Tab("🎯 [2] Lệnh Chốt Kế Tiếp"):
        title_2 = gr.Markdown(f"#### Lệnh cho kỳ quay tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ (Điểm/1 con lô)", value=10)
        btn_2 = gr.Button("🔍 KIẾT XUẤT LỆNH DÀN 24 SỐ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V31.0", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Bảng Vốn Khung Nháy"):
        with gr.Row():
            pts_3 = gr.Number(label="Mức cược (Điểm/1 con lô)", value=10)
        btn_3 = gr.Button("🧪 MÔ PHỎNG LỢI NHUẬN THEO NHÁY", variant="primary")
        out_3 = gr.Textbox(label="Phân Tích Hòa Vốn & Có Lãi", lines=16)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[pts_3], outputs=out_3)

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
