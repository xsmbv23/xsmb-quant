import os
import sys
import time
import math
import random
import hashlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, List
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V12.3 - FRAME QUANT MASTER (CHIẾN THUẬT KHUNG 2-3 NGÀY)
# ==============================================================================
VERSION = "V12.3 FRAME QUANT MASTER (KHUNG 2-3 NGÀY)"
DATA_FILE = "Ket_Qua_Loto27.xlsx"

GLOBAL_PRED_CACHE = {}

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
                    'date_str': ngay_str,
                    'prizes_str': loto_list[:27],
                    'prizes_int': [int(x) for x in loto_list[:27]]
                }
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU SẠCH TỪ EXCEL!"
    except Exception as e:
        return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

# ==============================================================================
# 🎯 LÕI TÍNH TOÁN KHUNG 2-3 NGÀY (FRAME QUANT ENGINE)
# ==============================================================================
def tinh_khung_23_ngay(target_dt, db):
    """
    Thuật toán soi mã A+ cho Khung 2-3 ngày:
    - Bắt cặp Bạch Thủ / Song Thủ có gia tốc Lô Rơi cực mạnh
    - Tính toán vị trí Ngày trong Khung (Ngày 1, Ngày 2 hay Ngày 3)
    """
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(15):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        seed_val = target_dt.year * 10000 + target_dt.month * 100 + target_dt.day
        r = random.Random(seed_val)
        pool = [f"{i:02d}" for i in range(100)]
        return [r.choice(pool), r.choice(pool)], True, "KỲ 1 KHUNG 2 NGÀY", 10, 0.85

    scores = np.zeros(100)
    # Lô rơi phiên gần nhất
    for p in hist_days[0]: scores[p] += 4.0
    # Tần suất 3 phiên
    for r_p in hist_days[:3]:
        for p in r_p: scores[p] += 1.5
    # Khóa lô khan > 5 ngày
    for i in range(100):
        giam = 0
        for r_p in hist_days:
            if i in r_p: break
            giam += 1
        if giam >= 5: scores[i] = -999.0

    ranking = np.argsort(scores)[::-1]
    top_2 = [f"{idx:02d}" for idx in ranking[:2]]
    max_score = np.max(scores)

    # Kiểm tra trạng thái khung từ 2 ngày trước
    prev_1 = target_dt - timedelta(days=1)
    prev_2 = target_dt - timedelta(days=2)
    s_prev1 = prev_1.strftime("%d/%m/%Y")
    s_prev2 = prev_2.strftime("%d/%m/%Y")

    hit_prev1 = False
    hit_prev2 = False

    if s_prev1 in db:
        hit_prev1 = any(int(c) in db[s_prev1]['prizes_int'] for c in top_2)
    if s_prev2 in db:
        hit_prev2 = any(int(c) in db[s_prev2]['prizes_int'] for c in top_2)

    # Xác định Ngày trong Khung
    if not hit_prev1 and hit_prev2:
        frame_day = 2
        pts_per_code = 25  # Gấp thếp Ngày 2
        status_msg = "🔥 KHUNG NGÀY 2/3 (TĂNG VỐN 2.5X)"
    elif not hit_prev1 and not hit_prev2:
        frame_day = 3
        pts_per_code = 60  # Gấp thếp Ngày 3 (Chốt Khung)
        status_msg = "🚨 KHUNG NGÀY 3/3 (CHỐT KHUNG CỰC ĐẠI 6X)"
    else:
        frame_day = 1
        pts_per_code = 10  # Mở Khung Mới Ngày 1
        status_msg = "🟢 MỞ KHUNG MỚI - NGÀY 1/3 (VỐN CƠ SỞ)"

    is_trade_day = max_score >= 5.0  # Ngưỡng bộ lọc rủi ro an toàn
    if not is_trade_day:
        status_msg = "🛡️ ĐÓNG VAN AN TOÀN: Dữ liệu chưa đủ độ lệch Anomaly"

    return top_2, is_trade_day, status_msg, pts_per_code, frame_day

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GRADIO TRẠNG THÁI V12.3
# ==============================================================================
def web_phan_he_1_sync():
    try:
        global GLOBAL_PRED_CACHE
        GLOBAL_PRED_CACHE.clear()
        db, msg = doc_database_tu_excel()
        curr_date, next_date = lay_thoi_gian_thuc_vn()
        
        res = f"📡 KẾT NỐI HỆ THỐNG QUANT V12.3 - TRẠNG THÁI KHUNG 2-3 NGÀY:\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"• Trạng thái File       : {msg}\n"
        res += f"• Quy mô dữ liệu Real   : {len(db)} ngày (Excel Time-Series)\n"
        res += f"• Mốc chốt kết quả VN   : [{curr_date.strftime('%d/%m/%Y')}]\n"
        res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"⚙️ TRẠNG THÁI MỚI: Đã chuyển đổi sang Chiến thuật Nuôi Khung 2-3 ngày & Martingale Kiềm Chế!"
        return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"
    except Exception as e:
        return f"🛑 LỖI THỰC THI TAB 1: {e}", "#### Kỳ quay ngày: --/--/----"

def web_phan_he_2_predict():
    try:
        db, _ = doc_database_tu_excel()
        _, next_date = lay_thoi_gian_thuc_vn()
        codes, is_trade, status_msg, pts, frame_day = tinh_khung_23_ngay(next_date, db)
        
        gia_von = 23000
        tong_diem = len(codes) * pts
        tong_von = tong_diem * gia_von if is_trade else 0
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN KHUNG 2-3 NGÀY CHO KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"🎚️ Trạng Thái Khung : {status_msg}\n"
        res += f"📋 CẶP MÃ A+ KHUYẾN NGHỊ : [ " + " - ".join(codes) + " ]\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"⚙️ KẾ HOẠCH PHÂN BỔ VỐN MARTINGALE:\n"
        res += f" • Mức giải ngân mỗi con : {pts if is_trade else 0} điểm\n"
        res += f" • Tổng điểm cặp lô khung : {tong_diem if is_trade else 0} điểm\n"
        res += f" 💵 TỔNG VỐN ĐẦU TƯ KỲ NÀY : {tong_von:,.0f} VND\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📈 KỊCH BẢN LỢI NHUẬN RÒNG KHI NỔ LÔ:\n"
        if is_trade:
            rev1 = pts * 80000
            rev2 = pts * 2 * 80000
            res += f" • Nổ x1 nháy : Doanh thu {rev1:,.0f} VND | Delta: {rev1 - tong_von:+12,.0f} VND 🟢\n"
            res += f" • Nổ x2 nháy : Doanh thu {rev2:,.0f} VND | Delta: {rev2 - tong_von:+12,.0f} VND 🟢\n"
        else:
            res += f" 🛡️ Van an toàn đóng: Đứng ngoài bảo toàn 100% tiền mặt mặt (Lợi nhuận: 0 VND).\n"
        return res
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

def web_phan_he_3_risk_audit(capital_vnd):
    try:
        try: cap_val = float(capital_vnd)
        except: cap_val = 10000000.0
        
        report = f"🔍 QUẢN TRỊ VỐN KHUNG 3 NGÀY TỶ LỆ MARTINGALE (1 : 2.5 : 6):\n"
        report += f"---------------------------------------------------------------------------------\n"
        v1 = int((cap_val * 0.10) // 23000)
        v2 = int((cap_val * 0.25) // 23000)
        v3 = int((cap_val * 0.60) // 23000)
        
        report += f" • Ngày 1 (Cơ sở)  : Đánh {v1} điểm/mã | Vốn chi: {v1*2*23000:,.0f} VND\n"
        report += f" • Ngày 2 (Gấp 2.5): Đánh {v2} điểm/mã | Vốn chi: {v2*2*23000:,.0f} VND\n"
        report += f" • Ngày 3 (Chốt 6x): Đánh {v3} điểm/mã | Vốn chi: {v3*2*23000:,.0f} VND\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💵 Tổng quỹ dự phòng an toàn cho Khung: {(v1+v2+v3)*2*23000:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ. Dùng DD/MM/YYYY."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
            
        codes, is_trade, status_msg, pts, _ = tinh_khung_23_ngay(d_obj, db)
        lo_to_27 = db[ngay_str]['prizes_str']
        
        nhay_list = [lo_to_27.count(code) for code in codes]
        tong_nhay = sum(nhay_list)
        phi_phien = len(codes) * pts * 23000 if is_trade else 0
        rev = tong_nhay * pts * 80000 if is_trade else 0
        net_profit = rev - phi_phien
        
        report = f"📡 TRÍCH XUẤT BACKTEST KHUNG CHO NGÀY: {ngay_str}\n"
        report += f"🎚️ Trạng Thái : {status_msg}\n"
        report += f"📋 Cặp mã soi : [ " + " - ".join(codes) + " ]\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 KẾT QUẢ MỞ THƯỞNG: Nổ x{tong_nhay} nháy thực tế!\n"
        for i in range(len(codes)):
            report += f" • Mã [{codes[i]}]: {nhay_list[i]} nháy\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💰 Chi phí vốn : {phi_phien:,.0f} VND\n"
        report += f"💵 Doanh thu   : {rev:,.0f} VND\n"
        report += f"📈 LỢI NHUẬN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

def web_phan_he_5_monthly_audit(month, year):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO TÀI CHÍNH LŨY KẾ KHUNG THÁNG {thang:02d}/{nam}:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            codes, is_trade, status_msg, pts, _ = tinh_khung_23_ngay(d_obj, db)
            lo_to_27 = db[ngay_str]['prizes_str']
            
            if not is_trade:
                report += f"{ngay_str} | 🛡️ ĐÓNG VAN  | {'[VAN AN TOÀN ĐÓNG BẢO TOÀN VỐN]':<35} | {luy_ke_tien:+12,.0f} VND\n"
                continue
                
            traded_days += 1
            tong_nhay = sum(lo_to_27.count(c) for c in codes)
            phi_phien = len(codes) * pts * 23000
            rev = tong_nhay * pts * 80000
            delta = rev - phi_phien
            luy_ke_tien += delta
            
            status_tag = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else f"🔴 TRƯỢT"
            if delta > 0: win_days += 1
            
            report += f"{ngay_str} | {status_tag:<12} | Mã: {codes[0]}-{codes[1]} ({pts}đ) | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê Khung: Khai hỏa {traded_days} phiên | Thắng {win_days} phiên | Win-Rate: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
        t1 = res1[0]; t2 = res2[0]
        
        t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0
        report = f"📈 BÁO CÁO CHU KỲ KHUNG TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                codes, is_trade, _, pts, _ = tinh_khung_23_ngay(t_curr, db)
                lo_to_27 = db[ngay_str]['prizes_str']
                
                if is_trade:
                    active_days += 1
                    tong_nhay = sum(lo_to_27.count(c) for c in codes)
                    phi_phien = len(codes) * pts * 23000
                    rev = tong_nhay * pts * 80000
                    delta = rev - phi_phien
                    if delta > 0: win_days += 1
                    tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
                    status_tag = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else f"🔴 TRƯỢT"
                    report += f"{ngay_str} | {status_tag:<12} | Mã: {codes[0]}-{codes[1]} ({pts}đ) | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
                else:
                    report += f"{ngay_str} | 🛡️ SKIP     | [ĐÓNG VAN BẢO TOÀN VỐN]             | LK: {luy_ke_range:+12,.0f} VND\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong - tong_von
        win_rate = (win_days / active_days * 100) if active_days > 0 else 0
        
        report += f"-------------------------------------------------------------------------------------------------------\n"
        report += f"📊 Quét: {active_days} phiên bóp cò | Thắng: {win_days} phiên | Tỷ lệ Win-Rate: {win_rate:.2f}%\n"
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
# 🎨 GIAO DIỆN GRADIO V12.3 FRAME QUANT MASTER
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V12.3") as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V12.3 — KHUNG 2-3 NGÀY & MARTINGALE SHIELD")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT ĐỒNG BỘ CẬP NHẬT CHẾ ĐỘ KHUNG", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu & Khung", lines=10)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới (Khung 2-3 Ngày)"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        btn_2 = gr.Button("🔍 TRÍCH XUẤT CẶP MÃ & TRẠNG THÁI KHUNG AI", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Khung 2-3 Ngày AI", lines=12)
        btn_2.click(web_phan_he_2_predict, outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn Martingale"):
        cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
        btn_3 = gr.Button("🧪 LẬP KẾ HOẠCH PHÂN BỔ VỐN KHUNG", variant="primary")
        out_3 = gr.Textbox(label="Sơ Đồ Tỷ Lệ Martingale 1:2.5:6", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        date_4 = gr.Textbox(label="Nhập ngày cần tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST KHUNG", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Khung", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ KHUNG THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Lũy kế Báo cáo Tài chính Khung", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_6 = gr.Button("📈 QUÉT CHU KỲ KHUNG TÀI CHÍNH", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Khung", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
