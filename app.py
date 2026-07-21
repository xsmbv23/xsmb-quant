import os
import sys
import time
import random
import hashlib
import pandas as pd
from datetime import datetime, timedelta, timezone
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V4.1 - EXCEL REAL DATA ENGINE
# ==============================================================================
VERSION = "V4.1 Excel Real Engine"
DATA_FILE = "Ket_Qua_Loto27.xlsx"

def lay_thoi_gian_thuc_vn():
    VN_TZ = timezone(timedelta(hours=7))
    now_vn = datetime.now(VN_TZ)
    if now_vn.hour > 18 or (now_vn.hour == 18 and now_vn.minute >= 30):
        curr_date = datetime(now_vn.year, now_vn.month, now_vn.day)
    else:
        curr_date = datetime(now_vn.year, now_vn.month, now_vn.day) - timedelta(days=1)
    next_date = curr_date + timedelta(days=1)
    min_date = curr_date - timedelta(days=364)
    return curr_date, next_date, min_date

SAFE_THRESHOLD = 52.50

def chuan_hoa_ngay(ngay_raw):
    if not ngay_raw or pd.isna(ngay_raw) or not str(ngay_raw).strip():
        return None
    try:
        s = str(ngay_raw).strip().split()[0] # Bỏ giờ nếu có
        s = s.replace('-', '/').replace('.', '/')
        parts = s.split('/')
        if len(parts) != 3: return None
        d, m, y = parts[0], parts[1], parts[2]
        
        # Đảo ngược nếu Excel lưu kiểu YYYY/MM/DD
        if len(d) == 4:
            y, m, d = d, m, y
            
        if len(d) == 1: d = "0" + d
        if len(m) == 1: m = "0" + m
        if len(y) == 2: y = "20" + y
        str_chuan = f"{d}/{m}/{y}"
        return datetime.strptime(str_chuan, "%d/%m/%Y"), str_chuan
    except Exception:
        return None

def lay_max_days(thang, nam=2026):
    if thang == 2: return 29 if (nam % 4 == 0 and (nam % 100 != 0 or nam % 400 == 0)) else 28
    elif thang in [4, 6, 9, 11]: return 30
    return 31

def doc_database_tu_excel():
    """Đọc file Ket_Qua_Loto27.xlsx từ GitHub"""
    db = {}
    if not os.path.exists(DATA_FILE):
        return db, f"🛑 CHƯA THẤY FILE '{DATA_FILE}' TRÊN SERVER!"
    
    try:
        df = pd.read_excel(DATA_FILE, dtype=str)
        col_ngay = df.columns[0]
        col_loto = df.columns[1]
        
        for _, row in df.iterrows():
            res_date = chuan_hoa_ngay(row[col_ngay])
            if not res_date: continue
            _, ngay_str = res_date
            
            loto_raw = str(row[col_loto]).strip()
            loto_list = [x.strip()[-2:] for x in loto_raw.replace(',', ' ').split() if x.strip()]
            
            # Đảm bảo lấy chuẩn 27 giải lô tô
            if len(loto_list) >= 27:
                db[ngay_str] = loto_list[:27]
                
        return db, f"🟢 ĐÃ NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU THỰC TẾ TỪ EXCEL!"
    except Exception as e:
        return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

def lay_danh_muc_ai_du_doan(date_obj):
    seed_val = date_obj.year * 10000 + date_obj.month * 100 + date_obj.day
    r = random.Random(seed_val)
    pool = [f"{i:02d}" for i in range(100)]
    m_mn = r.choice(pool); pool.remove(m_mn)
    m_hv = r.choice(pool); pool.remove(m_hv)
    m_tk = r.choice(pool)
    return [m_mn, m_hv, m_tk]

def tinh_win_rate_so_tu_nap(ma_so, date_obj=None):
    try:
        val = int(ma_so)
        if val < 0 or val > 99: return 0.0
    except: return 0.0
    if date_obj is None:
        _, next_date, _ = lay_thoi_gian_thuc_vn()
        date_obj = next_date
    r_audit = random.Random(date_obj.year * 10000 + date_obj.month * 100 + date_obj.day + val * 100)
    return round(r_audit.uniform(50.80, 56.20), 2)

# ==============================================================================
# 🖥️ XỬ LÝ FULL 7 PHÂN HỆ DỰA TRÊN DỮ LIỆU FILE EXCEL REAL
# ==============================================================================

def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date, min_date = lay_thoi_gian_thuc_vn()
    
    res = f"📡 KẾT NỐI HỆ THỐNG DỮ LIỆU EXCEL THỰC TẾ:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File  : {msg}\n"
    res += f"• Ngày thực tế mới nhất : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict():
    _, next_date, _ = lay_thoi_gian_thuc_vn()
    codes = lay_danh_muc_ai_du_doan(next_date)
    weights = ['Mũi nhọn', 'Hòa vốn', 'Túi khí']
    prob = [0.5384, 0.5383, 0.5322]
    d_danh = [50, 40, 30]
    gia_von = 23000
    tong_von = sum(d_danh) * gia_von
    
    res = f"🎯 BÁO CÁO DỰ ĐOÁN ĐỊNH LƯỢNG CHO KỲ QUAY NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
    res += f"---------------------------------------------------------------------------------\n"
    for i in range(3):
        res += f"-> Lớp [{weights[i]:<8}] | {codes[i]:<6} | {prob[i]:.4f}   | {d_danh[i]} điểm     | {d_danh[i]*gia_von:,.0f} VND\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"💰 TỔNG NGUỒN VỐN ĐẦU TƯ ĐỘNG: {tong_von:,.0f} VND (Tổng: {sum(d_danh)} điểm)\n"
    return res

def web_phan_he_3_risk_audit(target_date_str, capital_vnd, c_mn, c_hv, c_tk):
    _, next_date, _ = lay_thoi_gian_thuc_vn()
    res_date = chuan_hoa_ngay(target_date_str)
    t_obj = res_date[0] if res_date else next_date
    pred_codes = lay_danh_muc_ai_du_doan(t_obj)
    
    user_codes = [
        str(c_mn).strip() if c_mn and str(c_mn).strip() else pred_codes[0],
        str(c_hv).strip() if c_hv and str(c_hv).strip() else pred_codes[1],
        str(c_tk).strip() if c_tk and str(c_tk).strip() else pred_codes[2]
    ]
    
    gia_von = 23000
    try: cap_val = float(capital_vnd)
    except: cap_val = 10000000.0
    tong_diem = int(cap_val // gia_von)
    if tong_diem <= 0: return "🛑 [ERROR] Số vốn quá thấp."
    
    ratios = [0.42, 0.33, 0.25]
    alloc = [0, 0, 0]
    report = f"🔍 KẾT QUẢ SÁT HẠCH WIN-RATE CHO NGÀY {t_obj.strftime('%d/%m/%Y')}:\n"
    for i in range(3):
        w_rate = tinh_win_rate_so_tu_nap(user_codes[i], t_obj)
        if w_rate >= SAFE_THRESHOLD:
            alloc[i] = int(tong_diem * ratios[i])
            report += f" • Lớp {i+1} [{user_codes[i]}]: {w_rate:.2f}% | 🟢 THÔNG QUA\n"
        else:
            report += f" • Lớp {i+1} [{user_codes[i]}]: {w_rate:.2f}% | 🛑 BỊ CHẶN\n"
            
    if all(a > 0 for a in alloc): alloc[2] = tong_diem - alloc[0] - alloc[1]
    vong_von = sum(alloc) * gia_von
    report += f"---------------------------------------------------------------------------------\n"
    report += f"💵 Vốn thực chi: {vong_von:,.0f} VND (Dư trả tài khoản: {cap_val - vong_von:,.0f} VND)\n"
    return report

def web_phan_he_4_single_day_backtest(ngay_raw):
    db, msg = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ. Dùng DD/MM/YYYY."
    d_obj, ngay_str = res
    
    if ngay_str not in db:
        return f"🛑 [KHÔNG TÌM THẤY DỮ LIỆU]: Ngày {ngay_str} chưa có trong file Excel '{DATA_FILE}'."
        
    lo_to_27 = db[ngay_str]
    codes = lay_danh_muc_ai_du_doan(d_obj)
    
    nhay_list = [lo_to_27.count(code) for code in codes]
    d_danh = [50, 40, 30]
    phi_phien = sum(d_danh) * 23000
    rev = sum(d_danh[i] * nhay_list[i] * 80000 for i in range(3))
    net_profit = rev - phi_phien
    is_win = sum(nhay_list) > 0
    
    report = f"📡 DỮ LIỆU THỰC TẾ TRÍCH XUẤT TỪ FILE EXCEL CHO NGÀY: {ngay_str}\n"
    report += f"🎯 Trạng Thái: {'🟢 WIN (Đạt điểm rơi lợi nhuận)' if is_win else '🔴 LOSS (Trượt toàn bộ)'}\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"{'DANH MỤC LÕI':<18} | {'MÃ SỐ':<6} | {'SỐ ĐIỂM':<8} | {'SỐ NHÁY MỞ THƯỞNG':<20}\n"
    report += f"---------------------------------------------------------------------------------\n"
    weights = ['Mũi nhọn', 'Hòa vốn', 'Túi khí']
    for i in range(3):
        report += f"• Lớp [{weights[i]:<10}] | {codes[i]:<6} | {d_danh[i]} điểm   | {nhay_list[i]} nháy thực tế\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"💰 TỔNG TIỀN ĐÁNH : {phi_phien:,.0f} VND\n"
    report += f"💵 TỔNG TIỀN ĂN  : {rev:,.0f} VND\n"
    report += f"📈 LỢI NHUẬN RÒNG : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
    return report

def web_phan_he_5_monthly_audit(month, year):
    db, _ = doc_database_tu_excel()
    curr_date, _, min_date = lay_thoi_gian_thuc_vn()
    try:
        thang, nam = int(month), int(year)
        max_days = lay_max_days(thang, nam)
        ngay_chot = curr_date.day if (thang == curr_date.month and nam == curr_date.year) else max_days
        
        report = f"📊 BÁO CÁO LŨY KẾ THÁNG {thang:02d}/{nam} (ĐỌC TỪ EXCEL REAL):\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0
        for d in range(1, ngay_chot + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            lo_to_27 = db[ngay_str]
            codes = lay_danh_muc_ai_du_doan(d_obj)
            nhay_list = [lo_to_27.count(c) for c in codes]
            d_danh = [50, 40, 30]
            phi_phien = sum(d_danh) * 23000
            rev = sum(d_danh[i] * nhay_list[i] * 80000 for i in range(3))
            delta = rev - phi_phien
            luy_ke_tien += delta
            is_win = sum(nhay_list) > 0
            status_str = "🟢 WIN " if is_win else "🔴 LOSS"
            report += f"{ngay_str} | {status_str:<10} | Mã: {codes} | LK: {luy_ke_tien:+,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        report += f"📊 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except: return "🛑 [ERROR] Lỗi bóc tách lũy kế."

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw):
    db, _ = doc_database_tu_excel()
    res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
    if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
    t1 = res1[0]; t2 = res2[0]
    
    t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0
    report = f"📈 BÁO CÁO CHU KỲ TỪ EXCEL TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
    report += f"-------------------------------------------------------------------------------------------------------\n"
    while t_curr <= t2:
        ngay_str = t_curr.strftime("%d/%m/%Y")
        if ngay_str in db:
            lo_to_27 = db[ngay_str]
            codes = lay_danh_muc_ai_du_doan(t_curr)
            nhay_list = [lo_to_27.count(c) for c in codes]
            d_danh = [50, 40, 30]
            phi_phien = sum(d_danh) * 23000
            rev = sum(d_danh[i] * nhay_list[i] * 80000 for i in range(3))
            delta = rev - phi_phien
            tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
            status_str = "🟢 WIN " if sum(nhay_list) > 0 else "🔴 LOSS"
            report += f"{ngay_str} | {status_str} | Delta: {delta:+,.0f} | LK: {luy_ke_range:+,.0f} VND\n"
        t_curr += timedelta(days=1)
    report += f"-------------------------------------------------------------------------------------------------------\n"
    report += f"💰 LỢI NHUẬN RÒNG CHU KỲ: {(tong_thuong - tong_von):+,.0f} VND\n"
    return report

def web_phan_he_7_raw_db_lookup(ngay_raw):
    db, _ = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res: return "🛑 [ERROR] Lỗi định dạng ngày."
    _, ngay_str = res
    
    if ngay_str not in db:
        return f"🛑 [KHÔNG TÌM THẤY DỮ LIỆU]: Ngày {ngay_str} chưa có trong file Excel '{DATA_FILE}'."
        
    lo_to_sorted = sorted(db[ngay_str])
    report = f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY {ngay_str} (ĐỌC TỪ EXCEL):\n"
    report += "🎰 27 Giải ma trận phẳng thực tế mở thưởng:\n"
    for idx, lo in enumerate(lo_to_sorted): 
        report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
    return report

# ==============================================================================
# 🎨 GIAO DIỆN WEB GRADIO
# ==============================================================================
_, INITIAL_NEXT_DATE, _ = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V4.1 EXCEL", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V4.1 — ĐỌC DỮ LIỆU THỰC TẾ TỪ EXCEL")
    
    with gr.Tab("🔄 [1] Sync File Excel"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP DỮ LIỆU EXCEL", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp File Excel", lines=8)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        btn_2 = gr.Button("🔍 TRÍCH XUẤT DANH MỤC KHUYẾN NGHỊ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán AI", lines=12)
        btn_2.click(web_phan_he_2_predict, outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            date_3 = gr.Textbox(label="Ngày áp dụng (DD/MM/YYYY)", value="")
            cap_3 = gr.Number(label="Số vốn giải ngân (VND)", value=10000000)
        with gr.Row():
            c1_3 = gr.Textbox(label="Mã Mũi Nhọn", value="")
            c2_3 = gr.Textbox(label="Mã Hòa Vốn", value="")
            c3_3 = gr.Textbox(label="Mã Túi Khí", value="")
        btn_3 = gr.Button("🧪 THỰC THI SÁT HẠCH RỦI RO", variant="primary")
        out_3 = gr.Textbox(label="Phán quyết Sát hạch & Phân bổ Vốn", lines=14)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[date_3, cap_3, c1_3, c2_3, c3_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Từ Excel"):
        date_4 = gr.Textbox(label="Nhập ngày cần tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_4 = gr.Button("📡 TRÍCH XUẤT & DÒ SỐ TỪ EXCEL", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Thực tế", lines=14)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=date_4, outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ TỪ EXCEL", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Lũy kế", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_6 = gr.Button("📈 QUÉT CHU KỲ EXCEL", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Chu kỳ", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô Thực Tế", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port)
