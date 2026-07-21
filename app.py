import os
import sys
import time
import math
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import gradio as gr

VERSION = "V10.0 ULTRA-LEAN QUANT ENGINE"
DATA_FILE = "Ket_Qua_Loto27.xlsx"

def lay_thoi_gian_thuc_vn():
    VN_TZ = timezone(timedelta(hours=7))
    now_vn = datetime.now(VN_TZ)
    if now_vn.hour > 18 or (now_vn.hour == 18 and now_vn.minute >= 30):
        curr_date = datetime(now_vn.year, now_vn.month, now_vn.day)
    else:
        curr_date = datetime(now_vn.year, now_vn.month, now_vn.day) - timedelta(days=1)
    next_date = curr_date + timedelta(days=1)
    return curr_date, next_date

def chuan_hoa_ngay(ngay_raw):
    if not ngay_raw or pd.isna(ngay_raw) or not str(ngay_raw).strip(): return None
    try:
        s = str(ngay_raw).strip().split()[0].replace('-', '/').replace('.', '/')
        parts = [p for p in s.split('/') if p]
        if len(parts) != 3: return None
        d, m, y = parts[0], parts[1], parts[2]
        if len(d) == 4: y, m, d = d, m, y
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
    db = {}
    if not os.path.exists(DATA_FILE): return db, f"🛑 CHƯA THẤY FILE '{DATA_FILE}' TRÊN GITHUB!"
    try:
        df = pd.read_excel(DATA_FILE, dtype=str)
        col_ngay = df.columns[0]; col_loto = df.columns[1]
        for _, row in df.iterrows():
            res_date = chuan_hoa_ngay(row[col_ngay])
            if not res_date: continue
            dt_obj, ngay_str = res_date
            loto_raw = str(row[col_loto]).strip()
            loto_list = [x.strip()[-2:] for x in loto_raw.replace(',', ' ').replace(';', ' ').split() if x.strip().isdigit()]
            if len(loto_list) >= 27:
                db[ngay_str] = {
                    'date_obj': dt_obj,
                    'prizes_str': loto_list[:27],
                    'prizes_int': [int(x) for x in loto_list[:27]]
                }
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU SẠCH TỪ EXCEL!"
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

# ==============================================================================
# 🎯 LÕI DỰ ĐOÁN SIÊU RÚT GỌN (PURE MOMENTUM & FREQUENCY)
# ==============================================================================
def tinh_danh_muc_lean_quantum(target_dt, db):
    """
    Lõi V10.0: Loại bỏ 100% thuật toán nhiễu.
    Chỉ tập trung vào 2 động lực thực tế:
    1. Lô rơi từ phiên hôm qua (Momentum - Trọng số 60%)
    2. Tần suất xuất hiện dày đặc trong 3 phiên gần nhất (Hot Stream - Trọng số 40%)
    """
    hist_3_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(10):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_3_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_3_days) < 3:
        seed_val = target_dt.year * 10000 + target_dt.month * 100 + target_dt.day
        r = random.Random(seed_val)
        pool = [f"{i:02d}" for i in range(100)]
        return [r.choice(pool), r.choice(pool), r.choice(pool)]

    # 1. Điểm Lô Rơi (Phiên hôm qua)
    scores = np.zeros(100)
    for p in hist_3_days[0]:
        scores[p] += 3.0  # Ưu tiên cực cao cho lô mới nổ

    # 2. Điểm Tần Suất 3 phiên
    for r in hist_3_days[:3]:
        for p in r:
            scores[p] += 1.0

    # 3. Lọc bỏ CỨNG Lô Khan (> 5 ngày không nổ)
    for i in range(100):
        giam = 0
        for r in hist_3_days:
            if i in r: break
            giam += 1
        if giam >= 5:
            scores[i] = 0 # Đóng băng hoàn toàn lô khan

    ranking = np.argsort(scores)[::-1]
    top_3 = [f"{idx:02d}" for idx in ranking[:3]]
    return top_3

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ V10.0
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    res = f"📡 KẾT NỐI HE THỐNG V10.0 ULTRA-LEAN QUANT:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Ngày chốt kết quả VN  : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"💡 LÕI THUẬT TOÁN: Tự động loại bỏ lô khan > 5 ngày, tập trung 100% Lô Rơi & Tần Suất 3 phiên.\n"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict():
    db, _ = doc_database_tu_excel()
    _, next_date = lay_thoi_gian_thuc_vn()
    codes = tinh_danh_muc_lean_quantum(next_date, db)
    
    d_danh = [50, 40, 30]
    gia_von = 23000
    tong_von = sum(d_danh) * gia_von
    
    res = f"🎯 BÁO CÁO DỰ ĐOÁN SIÊU RÚT GỌN FOR KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
    res += f"---------------------------------------------------------------------------------\n"
    weights = ['Mũi nhọn (Lô rơi)', 'Hòa vốn (Tần suất)', 'Túi khí (Bảo hiểm)']
    for i in range(3):
        chi_phi = d_danh[i] * gia_von
        res += f"-> Lớp [{weights[i]:<20}] | Mã: {codes[i]} | Khuyến nghị: {d_danh[i]} điểm | Vốn: {chi_phi:,.0f} VND\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"💰 TỔNG VỐN ĐẦU TƯ MẮT ĐỊNH: {tong_von:,.0f} VND (Tổng {sum(d_danh)} điểm)\n"
    return res

def web_phan_he_3_risk_audit(target_date_str, capital_vnd, c_mn, c_hv, c_tk):
    db, _ = doc_database_tu_excel()
    _, next_date = lay_thoi_gian_thuc_vn()
    res_date = chuan_hoa_ngay(target_date_str)
    t_obj = res_date[0] if res_date else next_date
    pred_codes = tinh_danh_muc_lean_quantum(t_obj, db)
    
    u_codes = [
        str(c_mn).strip() if c_mn and str(c_mn).strip() else pred_codes[0],
        str(c_hv).strip() if c_hv and str(c_hv).strip() else pred_codes[1],
        str(c_tk).strip() if c_tk and str(c_tk).strip() else pred_codes[2]
    ]
    
    try: cap_val = float(capital_vnd)
    except: cap_val = 10000000.0
    gia_von = 23000
    tong_diem = int(cap_val // gia_von)
    
    d1 = int(tong_diem * 0.42)
    d2 = int(tong_diem * 0.33)
    d3 = tong_diem - d1 - d2
    vong_von = tong_diem * gia_von
    
    report = f"🔍 BẢNG QUẢN TRỊ VỐN KELLY THỰC CHI CHO NGÀY {t_obj.strftime('%d/%m/%Y')}:\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f" • Lớp Mũi nhọn [{u_codes[0]}]: {d1} điểm | Chi phí: {d1*gia_von:,.0f} VND\n"
    report += f" • Lớp Hòa vốn  [{u_codes[1]}]: {d2} điểm | Chi phí: {d2*gia_von:,.0f} VND\n"
    report += f" • Lớp Túi khí  [{u_codes[2]}]: {d3} điểm | Chi phí: {d3*gia_von:,.0f} VND\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"💵 Vốn thực chi: {vong_von:,.0f} VND (Số dư trả về tài khoản: {cap_val - vong_von:,.0f} VND)\n"
    return report

def web_phan_he_4_single_day_backtest(ngay_raw):
    db, _ = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ."
    d_obj, ngay_str = res
    if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
        
    lo_to_27 = db[ngay_str]['prizes_str']
    codes = tinh_danh_muc_lean_quantum(d_obj, db)
    
    nhay_list = [lo_to_27.count(code) for code in codes]
    d_danh = [50, 40, 30]
    phi_phien = sum(d_danh) * 23000
    rev = sum(d_danh[i] * nhay_list[i] * 80000 for i in range(3))
    net_profit = rev - phi_phien
    is_win = sum(nhay_list) > 0
    
    report = f"📡 TRÍCH XUẤT BACKTEST CHO NGÀY: {ngay_str}\n"
    report += f"🎯 Kết Quả Phiên: {'🟢 WIN (Đạt điểm rơi lợi nhuận)' if is_win else '🔴 LOSS (Trượt toàn bộ)'}\n"
    report += f"---------------------------------------------------------------------------------\n"
    weights = ['Mũi nhọn', 'Hòa vốn', 'Túi khí']
    for i in range(3):
        report += f"• Lớp [{weights[i]:<10}] | Mã: {codes[i]} | Đánh: {d_danh[i]} điểm | Về: {nhay_list[i]} nháy\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"💰 Chi phí vốn : {phi_phien:,.0f} VND\n"
    report += f"💵 Doanh thu   : {rev:,.0f} VND\n"
    report += f"📈 LỢI NHUẬN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
    return report

def web_phan_he_5_monthly_audit(month, year):
    db, _ = doc_database_tu_excel()
    try:
        thang, nam = int(month), int(year)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO TÀI CHÍNH LŨY KẾ THÁNG {thang:02d}/{nam} (LÕI LEAN QUANT V10.0):\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            traded_days += 1
            lo_to_27 = db[ngay_str]['prizes_str']
            codes = tinh_danh_muc_lean_quantum(d_obj, db)
            
            nhay_list = [lo_to_27.count(c) for c in codes]
            d_danh = [50, 40, 30]
            phi_phien = sum(d_danh) * 23000
            rev = sum(d_danh[i] * nhay_list[i] * 80000 for i in range(3))
            delta = rev - phi_phien
            luy_ke_tien += delta
            
            if sum(nhay_list) > 0:
                win_days += 1; status_str = "🟢 WIN "
            else:
                status_str = "🔴 LOSS"
                
            report += f"{ngay_str} | {status_str:<10} | Mã: {codes[0]}-{codes[1]}-{codes[2]} | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê: Tổng {traded_days} phiên | Thắng {win_days} phiên | Tỷ lệ Win-Rate: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw):
    db, _ = doc_database_tu_excel()
    res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
    if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
    t1 = res1[0]; t2 = res2[0]
    
    t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0
    report = f"📈 BÁO CÁO CHU KỲ TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
    report += f"-------------------------------------------------------------------------------------------------------\n"
    while t_curr <= t2:
        ngay_str = t_curr.strftime("%d/%m/%Y")
        if ngay_str in db:
            active_days += 1
            lo_to_27 = db[ngay_str]['prizes_str']
            codes = tinh_danh_muc_lean_quantum(t_curr, db)
            
            nhay_list = [lo_to_27.count(c) for c in codes]
            d_danh = [50, 40, 30]
            phi_phien = sum(d_danh) * 23000
            rev = sum(d_danh[i] * nhay_list[i] * 80000 for i in range(3))
            delta = rev - phi_phien
            if sum(nhay_list) > 0: win_days += 1
            tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
            status_str = "🟢 WIN " if sum(nhay_list) > 0 else "🔴 LOSS"
            report += f"{ngay_str} | {status_str} | Mã: {codes} | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
        t_curr += timedelta(days=1)
        
    net_profit = tong_thuong - tong_von
    win_rate = (win_days / active_days * 100) if active_days > 0 else 0
    
    report += f"-------------------------------------------------------------------------------------------------------\n"
    report += f"📊 Quét: {active_days} ngày | Thắng: {win_days} ngày | Tỷ lệ Win-Rate thực tế: {win_rate:.2f}%\n"
    report += f"💵 Tổng chi phí giải ngân : {tong_von:,.0f} VND\n"
    report += f"💵 Tổng doanh thu thu về  : {tong_thuong:,.0f} VND\n"
    report += f"💰 LỢI NHUẬN RÒNG CHU KỲ : {net_profit:+,.0f} VND\n"
    return report

def web_phan_he_7_raw_db_lookup(ngay_raw):
    db, _ = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res: return "🛑 [ERROR] Lỗi định dạng ngày."
    _, ngay_str = res
    if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
        
    lo_to_sorted = sorted(db[ngay_str]['prizes_str'])
    report = f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY {ngay_str} (TRÍCH XUẤT TỪ EXCEL):\n"
    report += "🎰 27 Giải ma trận phẳng thực tế mở thưởng:\n"
    for idx, lo in enumerate(lo_to_sorted): 
        report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
    return report

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V10.0", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V10.0 — PURE MOMENTUM & LEAN MODEL")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP DỮ LIỆU EXCEL REAL", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=8)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        btn_2 = gr.Button("🔍 TRÍCH XUẤT DANH MỤC V10.0", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán AI (Lô Rơi & Short-Frequency)", lines=10)
        btn_2.click(web_phan_he_2_predict, outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            date_3 = gr.Textbox(label="Ngày áp dụng (DD/MM/YYYY)", value="")
            cap_3 = gr.Number(label="Số vốn giải ngân (VND)", value=10000000)
        with gr.Row():
            c1_3 = gr.Textbox(label="Mã Mũi Nhọn", value="")
            c2_3 = gr.Textbox(label="Mã Hòa Vốn", value="")
            c3_3 = gr.Textbox(label="Mã Túi Khí", value="")
        btn_3 = gr.Button("🧪 PHÂN BỔ VỐN KELLY", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[date_3, cap_3, c1_3, c2_3, c3_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        date_4 = gr.Textbox(label="Nhập ngày cần tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=date_4, outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ LÃI LỖ", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Lũy kế Báo cáo Tài chính", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_6 = gr.Button("📈 QUÉT BÁO CÁO CHU KỲ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port)
