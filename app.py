import os
import sys
import time
import math
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import gradio as gr

VERSION = "V11.0 MULTI-BASKET QUANT ENGINE"
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
# 🎯 LÕI DỰ ĐOÁN DÀN LÔ ĐỘNG N-SỐ (MOMENTUM + HOT STREAM + ANTI-COLD)
# ==============================================================================
def tinh_dan_lo_quantum(target_dt, db, top_n=6):
    """
    Trích xuất Dàn Lô Top N (3, 6, 8, hoặc 10 số) theo trọng số động
    """
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(10):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        seed_val = target_dt.year * 10000 + target_dt.month * 100 + target_dt.day
        r = random.Random(seed_val)
        pool = [f"{i:02d}" for i in range(100)]
        return r.sample(pool, top_n)

    scores = np.zeros(100)
    
    # 1. Trọng số Lô Rơi phiên trước (Momentum)
    for p in hist_days[0]:
        scores[p] += 3.5

    # 2. Tần suất 3 phiên gần nhất
    for r in hist_days[:3]:
        for p in r:
            scores[p] += 1.2

    # 3. Lọc CỨNG Lô Khan (> 5 ngày giam)
    for i in range(100):
        giam = 0
        for r in hist_days:
            if i in r: break
            giam += 1
        if giam >= 5:
            scores[i] = -999.0 # Phong tỏa lô khan

    ranking = np.argsort(scores)[::-1]
    top_codes = [f"{idx:02d}" for idx in ranking[:top_n]]
    return top_codes

# ==============================================================================
# 🖥️ XỬ LÝ FULL 7 PHÂN HỆ V11.0 GRADIO
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    res = f"📡 KẾT NỐI HỆ THỐNG V11.0 MULTI-BASKET QUANT ENGINE:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Ngày chốt kết quả VN  : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"💡 LÕI DÀN LÔ: Hỗ trợ linh hoạt Dàn 3 số, 6 số, 8 số và 10 số phủ rộng.\n"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(basket_size, points_per_code):
    db, _ = doc_database_tu_excel()
    _, next_date = lay_thoi_gian_thuc_vn()
    n_size = int(basket_size)
    pts = int(points_per_code)
    codes = tinh_dan_lo_quantum(next_date, db, top_n=n_size)
    
    gia_von = 23000
    tong_diem = n_size * pts
    tong_von = tong_diem * gia_von
    
    res = f"🎯 BÁO CÁO DỰ ĐOÁN DÀN LÔ {n_size} SỐ CHO KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"📋 DANH MỤC DÀN {n_size} SỐ ĐỰỢC LỌC:\n"
    res += f"👉 [ " + " - ".join(codes) + " ]\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"⚙️ CẤU HÌNH VỐN GIẢI NGÂN:\n"
    res += f" • Đánh đều mỗi mã : {pts} điểm\n"
    res += f" • Tổng số điểm dàn : {tong_diem} điểm\n"
    res += f" 💵 TỔNG VỐN ĐẦU TƯ : {tong_von:,.0f} VND\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"📈 MA TRẬN ĐIỂM HÒA VỐN & LỢI NHUẬN RÒNG DỰ KIẾN:\n"
    for nhay in range(1, 5):
        rev = nhay * pts * 80000
        net = rev - tong_von
        tag = "🟢 CÓ LÃI" if net > 0 else ("⚖️ HÒA VỐN" if net == 0 else "🔴 ÂM VỐN")
        res += f" • Nổ x{nhay} nháy : Doanh thu {rev:,.0f} VND | Delta: {net:+12,.0f} VND [{tag}]\n"
    return res

def web_phan_he_3_risk_audit(capital_vnd, basket_size):
    try: cap_val = float(capital_vnd)
    except: cap_val = 10000000.0
    n_size = int(basket_size)
    
    gia_von = 23000
    tong_diem = int(cap_val // gia_von)
    diem_moi_con = int(tong_diem // n_size)
    vong_von = diem_moi_con * n_size * gia_von
    
    report = f"🔍 CHƯƠNG TRÌNH PHÂN BỔ VỐN ĐỀU CHO DÀN {n_size} SỐ:\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f" • Vốn khả thi quy đổi : {tong_diem} điểm\n"
    report += f" • Đánh đều cho {n_size} con : {diem_moi_con} điểm/mã\n"
    report += f" 💵 Vốn thực chi       : {vong_von:,.0f} VND\n"
    report += f" 💵 Dư trả tài khoản   : {cap_val - vong_von:,.0f} VND\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"📊 MẬT ĐỘ ĂN THƯỞNG DỰ KIẾN:\n"
    report += f" • Nổ 1 nháy : {diem_moi_con * 80000:,.0f} VND\n"
    report += f" • Nổ 2 nháy : {diem_moi_con * 2 * 80000:,.0f} VND\n"
    report += f" • Nổ 3 nháy : {diem_moi_con * 3 * 80000:,.0f} VND\n"
    return report

def web_phan_he_4_single_day_backtest(ngay_raw, basket_size, pts_per_code):
    db, _ = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ."
    d_obj, ngay_str = res
    if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
        
    n_size = int(basket_size)
    pts = int(pts_per_code)
    lo_to_27 = db[ngay_str]['prizes_str']
    codes = tinh_dan_lo_quantum(d_obj, db, top_n=n_size)
    
    nhay_list = [lo_to_27.count(code) for code in codes]
    tong_nhay = sum(nhay_list)
    phi_phien = n_size * pts * 23000
    rev = tong_nhay * pts * 80000
    net_profit = rev - phi_phien
    
    report = f"📡 TRÍCH XUẤT BACKTEST DÀN {n_size} SỐ CHO NGÀY: {ngay_str}\n"
    report += f"📋 Dàn số AI chọn: [ " + " - ".join(codes) + " ]\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"🎯 KẾT QUẢ MỞ THƯỞNG: Nổ tổng cộng x{tong_nhay} nháy thực tế!\n"
    for i in range(n_size):
        report += f" • Mã [{codes[i]}]: {nhay_list[i]} nháy\n"
    report += f"---------------------------------------------------------------------------------\n"
    report += f"💰 Chi phí vốn : {phi_phien:,.0f} VND ({n_size * pts} điểm)\n"
    report += f"💵 Doanh thu   : {rev:,.0f} VND\n"
    report += f"📈 LỢI NHUẬN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
    return report

def web_phan_he_5_monthly_audit(month, year, basket_size, pts_per_code):
    db, _ = doc_database_tu_excel()
    try:
        thang, nam = int(month), int(year)
        n_size = int(basket_size)
        pts = int(pts_per_code)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO NHẬT KÝ DÀN {n_size} SỐ THÁNG {thang:02d}/{nam}:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            traded_days += 1
            lo_to_27 = db[ngay_str]['prizes_str']
            codes = tinh_dan_lo_quantum(d_obj, db, top_n=n_size)
            
            tong_nhay = sum(lo_to_27.count(c) for c in codes)
            phi_phien = n_size * pts * 23000
            rev = tong_nhay * pts * 80000
            delta = rev - phi_phien
            luy_ke_tien += delta
            
            status_str = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else (f"⚖️ HÒA x{tong_nhay}n" if delta == 0 else f"🔴 LỖ x{tong_nhay}n")
            if delta >= 0: win_days += 1
            
            report += f"{ngay_str} | {status_str:<12} | Mã: {','.join(codes[:3])}... | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê Dàn {n_size} số: Tổng {traded_days} phiên | Phiên có lãi/hòa: {win_days} | Win-Rate: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, basket_size, pts_per_code):
    db, _ = doc_database_tu_excel()
    res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
    if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
    t1 = res1[0]; t2 = res2[0]
    n_size = int(basket_size)
    pts = int(pts_per_code)
    
    t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0
    report = f"📈 BÁO CÁO CHU KỲ DÀN {n_size} SỐ TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
    report += f"-------------------------------------------------------------------------------------------------------\n"
    while t_curr <= t2:
        ngay_str = t_curr.strftime("%d/%m/%Y")
        if ngay_str in db:
            active_days += 1
            lo_to_27 = db[ngay_str]['prizes_str']
            codes = tinh_dan_lo_quantum(t_curr, db, top_n=n_size)
            
            tong_nhay = sum(lo_to_27.count(c) for c in codes)
            phi_phien = n_size * pts * 23000
            rev = tong_nhay * pts * 80000
            delta = rev - phi_phien
            if delta >= 0: win_days += 1
            tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
            status_str = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else (f"⚖️ HÒA x{tong_nhay}n" if delta == 0 else f"🔴 LỖ x{tong_nhay}n")
            report += f"{ngay_str} | {status_str:<12} | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
        t_curr += timedelta(days=1)
        
    net_profit = tong_thuong - tong_von
    win_rate = (win_days / active_days * 100) if active_days > 0 else 0
    
    report += f"-------------------------------------------------------------------------------------------------------\n"
    report += f"📊 Quét: {active_days} ngày | Thắng/Hòa: {win_days} ngày | Tỷ lệ An toàn: {win_rate:.2f}%\n"
    report += f"💵 Tổng vốn giải ngân  : {tong_von:,.0f} VND\n"
    report += f"💵 Tổng doanh thu hoàn : {tong_thuong:,.0f} VND\n"
    report += f"💰 LỢI NHUẬN RÒNG     : {net_profit:+,.0f} VND\n"
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
# 🎨 GIAO DIỆN GRADIO V11.0
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V11.0", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V11.0 — DÀN LÔ ĐỘNG 6 - 10 SỐ")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP DỮ LIỆU EXCEL REAL", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=8)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        with gr.Row():
            b_size_2 = gr.Dropdown(label="Chọn kích thước Dàn Lô", choices=["3", "6", "8", "10"], value="6")
            pts_2 = gr.Number(label="Số điểm đánh mỗi con", value=10)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT DÀN LÔ KHUYẾN NGHỊ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán Dàn Lô AI", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[b_size_2, pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân (VND)", value=10000000)
            b_size_3 = gr.Dropdown(label="Chia đều cho Dàn", choices=["3", "6", "8", "10"], value="6")
        btn_3 = gr.Button("🧪 THỰC THI PHÂN BỔ VỐN DÀN LÔ", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn Dàn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, b_size_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        with gr.Row():
            date_4 = gr.Textbox(label="Nhập ngày cần tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            b_size_4 = gr.Dropdown(label="Kích thước Dàn", choices=["3", "6", "8", "10"], value="6")
            pts_4 = gr.Number(label="Số điểm/mã", value=10)
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST DÀN", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Dàn", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, b_size_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
            b_size_5 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["3", "6", "8", "10"], value="6")
            pts_5 = gr.Number(label="Số điểm/mã", value=10)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ LÃI LỖ DÀN LÔ", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Lũy kế Báo cáo Tài chính Dàn", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, b_size_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            b_size_6 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["3", "6", "8", "10"], value="6")
            pts_6 = gr.Number(label="Số điểm/mã", value=10)
        btn_6 = gr.Button("📈 QUÉT BÁO CÁO CHU KỲ DÀN LÔ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Dàn", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, b_size_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port)
