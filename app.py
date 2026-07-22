import os
import sys
import time
import math
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V15.0 - MATRIX COVERAGE ENGINE (27 LÔ PHẲNG THỰC TẾ)
# ==============================================================================
VERSION = "V15.0 DÀN LÔ BAO PHỦ MA TRẬN (27 LÔ PHẲNG)"
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
    """Đọc chuẩn xác ma trận 27 giải lô phẳng từ file Excel"""
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
                    'date_str': ngay_str,
                    'prizes_str': loto_list[:27],
                    'prizes_int': [int(x) for x in loto_list[:27]]
                }
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU LÔ 27 GIẢI PHẲNG TỪ EXCEL!"
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

# ==============================================================================
# 🎯 LÕI TÍNH TOÁN DÀN LÔ BAO PHỦ 10 - 20 - 30 SỐ (HEATMAP & MOMENTUM)
# ==============================================================================
def tinh_dan_lo_matrix(target_dt, db, top_n=30):
    """
    Trích xuất Dàn Lô N-số (10, 20, hoặc 30 số) tối ưu bao phủ 27 giải:
    1. Điểm Lô Rơi phiên trước (Weight: 3.5)
    2. Tần suất nổ 3 phiên gần nhất (Weight: 1.2)
    3. Thưởng điểm cho Đầu/Đuôi đang vào phom (Head/Tail Heatmap)
    4. Phong tỏa CỨNG các con Lô Khan (> 5 ngày)
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
        return sorted(r.sample(pool, top_n))

    scores = np.zeros(100)
    head_counts = np.zeros(10)
    tail_counts = np.zeros(10)

    # 1. Lô rơi phiên trước
    for p in hist_days[0]:
        scores[p] += 3.5
        head_counts[p // 10] += 1
        tail_counts[p % 10] += 1

    # 2. Tần suất 3 phiên gần nhất
    for r_p in hist_days[:3]:
        for p in r_p:
            scores[p] += 1.2

    # 3. Cộng điểm Heatmap cho Đầu/Đuôi hot
    for i in range(100):
        h = i // 10
        t = i % 10
        if head_counts[h] >= 4: scores[i] += 1.0 # Đầu nổ dày
        if tail_counts[t] >= 4: scores[i] += 1.0 # Đuôi nổ dày

    # 4. Lọc CỨNG Lô Khan (> 5 ngày giam)
    for i in range(100):
        giam = 0
        for r_p in hist_days:
            if i in r_p: break
            giam += 1
        if giam >= 5:
            scores[i] = -999.0 # Triệt hạ lô khan

    ranking = np.argsort(scores)[::-1]
    top_codes = sorted([f"{idx:02d}" for idx in ranking[:top_n]])
    return top_codes

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN GRADIO V15.0
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    res = f"📡 ĐỒNG BỘ DỮ LIỆU & KÍCH HOẠT LÕI V15.0 DÀN LÔ BAO PHỦ MA TRẬN:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Quy mô dữ liệu Real   : {len(db)} ngày 27 lô phẳng từ Excel\n"
    res += f"• Mốc chốt kết quả VN   : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"💡 LÕI MỚI: Loại bỏ 100% giả định về Đề. Chỉ tập trung bao phủ Dàn Lô 10-20-30 số!"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(size_input, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        _, next_date = lay_thoi_gian_thuc_vn()
        n_size = int(size_input)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        
        codes = tinh_dan_lo_matrix(next_date, db, top_n=n_size)
        tong_diem = n_size * pts
        tong_von = tong_diem * cost_pt
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN DÀN LÔ {n_size} SỐ CHO KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📋 DANH MỤC DÀN LÔ BAO PHỦ ({n_size} mã):\n"
        for idx in range(0, len(codes), 10):
            res += " ".join(f"[{c}]" for c in codes[idx:idx+10]) + "\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"⚙️ CẤU HÌNH VỐN GIẢI NGÂN (Giá vốn: {cost_pt:,.0f}đ/điểm):\n"
        res += f" • Đánh mỗi con : {pts} điểm ({pts * cost_pt:,.0f} VND/con)\n"
        res += f" • Tổng số điểm : {tong_diem} điểm\n"
        res += f" 💵 TỔNG VỐN ĐẦU TƯ : {tong_von:,.0f} VND\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📈 MA TRẬN ĐIỂM HÒA VỐN & LÃI RÒNG:\n"
        min_hits_break_even = math.ceil(tong_von / (pts * 80000))
        res += f" 👉 Điểm hòa vốn: Cần tối thiểu x{min_hits_break_even} nháy lô nổ.\n"
        for nhay in range(min_hits_break_even - 1, min_hits_break_even + 4):
            if nhay < 1: continue
            rev = nhay * pts * 80000
            net = rev - tong_von
            tag = "🟢 CÓ LÃI RÒNG" if net > 0 else ("⚖️ HÒA VỐN" if net == 0 else "🔴 ÂM VỐN")
            res += f" • Nổ x{nhay} nháy : Doanh thu {rev:,.0f} VND | Delta: {net:+12,.0f} VND [{tag}]\n"
        return res
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

def web_phan_he_3_risk_audit(capital_vnd, size_input, cost_per_point):
    try:
        cap_val = float(capital_vnd)
        n_size = int(size_input)
        cost_pt = float(cost_per_point)
        
        tong_diem_kha_thi = int(cap_val // cost_pt)
        pts_per_code = int(tong_diem_kha_thi // n_size)
        vong_von = pts_per_code * n_size * cost_pt
        
        report = f"🔍 QUẢN TRỊ VỐN BAO PHỦ CHO DÀN LÔ {n_size} SỐ:\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f" • Tổng vốn khả thi : {tong_diem_kha_thi} điểm ({cap_val:,.0f} VND)\n"
        report += f" • Phân bổ đều cho {n_size} con: {pts_per_code} điểm/mã\n"
        report += f" 💵 Vốn thực chi     : {vong_von:,.0f} VND (Giá {cost_pt:,.0f}đ/điểm)\n"
        report += f" 💵 Dư trả tài khoản : {cap_val - vong_von:,.0f} VND\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"📊 MẬT ĐỘ HÒA VỐN:\n"
        min_hits = math.ceil(vong_von / (pts_per_code * 80000)) if pts_per_code > 0 else 0
        report += f" • Chỉ cần nổ từ {min_hits} nháy trở lên là BẮT ĐẦU CÓ LÃI RÒNG! 🟢\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, size_input, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
            
        n_size = int(size_input)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        
        lo_to_27 = db[ngay_str]['prizes_str']
        codes = tinh_dan_lo_matrix(d_obj, db, top_n=n_size)
        
        nhay_list = [lo_to_27.count(code) for code in codes]
        tong_nhay = sum(nhay_list)
        phi_phien = n_size * pts * cost_pt
        rev = tong_nhay * pts * 80000
        net_profit = rev - phi_phien
        
        report = f"📡 TRÍCH XUẤT BACKTEST DÀN LÔ {n_size} SỐ CHO NGÀY: {ngay_str}\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 KẾT QUẢ MỞ THƯỞNG 27 GIẢI: Nổ tổng cộng x{tong_nhay} nháy thực tế!\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💰 Chi phí vốn giải ngân : {phi_phien:,.0f} VND ({n_size * pts} điểm giá {cost_pt:,.0f}đ)\n"
        report += f"💵 Doanh thu thu về      : {rev:,.0f} VND\n"
        report += f"📈 LỢI NHUẬN RÒNG PHIÊN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

def web_phan_he_5_monthly_audit(month, year, size_input, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        n_size = int(size_input)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO TÀI CHÍNH LŨY KẾ DÀN LÔ {n_size} SỐ THÁNG {thang:02d}/{nam}:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            traded_days += 1
            lo_to_27 = db[ngay_str]['prizes_str']
            codes = tinh_dan_lo_matrix(d_obj, db, top_n=n_size)
            
            tong_nhay = sum(lo_to_27.count(c) for c in codes)
            phi_phien = n_size * pts * cost_pt
            rev = tong_nhay * pts * 80000
            delta = rev - phi_phien
            luy_ke_tien += delta
            
            if delta >= 0: win_days += 1
            status_tag = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else (f"⚖️ HÒA x{tong_nhay}n" if delta == 0 else f"🔴 LỖ x{tong_nhay}n")
            
            report += f"{ngay_str} | {status_tag:<12} | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê Dàn Lô {n_size} số: Tổng {traded_days} phiên | Phiên có lãi/hòa: {win_days} | Win-Rate: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, size_input, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
        t1 = res1[0]; t2 = res2[0]
        n_size = int(size_input)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        
        t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0
        report = f"📈 BÁO CÁO CHU KỲ DÀN LÔ {n_size} SỐ TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                active_days += 1
                lo_to_27 = db[ngay_str]['prizes_str']
                codes = tinh_dan_lo_matrix(t_curr, db, top_n=n_size)
                
                tong_nhay = sum(lo_to_27.count(c) for c in codes)
                phi_phien = n_size * pts * cost_pt
                rev = tong_nhay * pts * 80000
                delta = rev - phi_phien
                if delta >= 0: win_days += 1
                tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
                status_tag = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else (f"⚖️ HÒA x{tong_nhay}n" if delta == 0 else f"🔴 LỖ x{tong_nhay}n")
                report += f"{ngay_str} | {status_tag:<12} | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong - tong_von
        win_rate = (win_days / active_days * 100) if active_days > 0 else 0
        
        report += f"-------------------------------------------------------------------------------------------------------\n"
        report += f"📊 Quét: {active_days} ngày | Thắng/Hòa: {win_days} ngày | Tỷ lệ An toàn: {win_rate:.2f}%\n"
        report += f"💵 Tổng vốn giải ngân  : {tong_von:,.0f} VND\n"
        report += f"💵 Tổng doanh thu hoàn : {tong_thuong:,.0f} VND\n"
        report += f"💰 LỢI NHUẬN RÒNG     : {net_profit:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 6]: {e}"

def web_phan_he_7_raw_db_lookup(ngay_raw):
    try:
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
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 7]: {e}"

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO V15.0 DÀN LÔ MATRIX
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V15.0") as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V15.0 — DÀN LÔ BAO PHỦ MA TRẬN (27 GIẢI EXCEL)")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT ĐỒNG BỘ DỮ LIỆU EXCEL REAL", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=8)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        with gr.Row():
            size_2 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["10", "20", "30"], value="30")
            cost_2 = gr.Number(label="Giá vốn điểm (21700đ Web hoặc 23000đ Thường)", value=21700)
            pts_2 = gr.Number(label="Số điểm đánh mỗi con lô", value=1)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT DÀN LÔ MATRIX KHUYẾN NGHỊ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán Dàn Lô AI", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[size_2, cost_2, pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
            size_3 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["10", "20", "30"], value="30")
            cost_3 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_3 = gr.Button("🧪 PHÂN BỔ VỐN BAO PHỦ MA TRẬN", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, size_3, cost_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        with gr.Row():
            date_4 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            size_4 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["10", "20", "30"], value="30")
            cost_4 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_4 = gr.Number(label="Số điểm/mã", value=1)
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST DÀN LÔ", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Dàn Lô", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, size_4, cost_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
            size_5 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["10", "20", "30"], value="30")
            cost_5 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_5 = gr.Number(label="Số điểm/mã", value=1)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ DÀN LÔ THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Báo cáo Tài chính Lũy kế Dàn Lô", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, size_5, cost_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            size_6 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["10", "20", "30"], value="30")
            cost_6 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_6 = gr.Number(label="Số điểm/mã", value=1)
        btn_6 = gr.Button("📈 QUÉT CHU KỲ BÁO CÁO DÀN LÔ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Dàn Lô", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, size_6, cost_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải Real", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
