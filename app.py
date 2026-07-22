import os
import sys
import time
import math
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import gradio as gr

VERSION = "V13.0 PAIR HEDGING & EXTREME ANOMALY ENGINE"
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
                    'date_str': ngay_str,
                    'prizes_str': loto_list[:27],
                    'prizes_int': [int(x) for x in loto_list[:27]]
                }
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU SẠCH TỪ EXCEL!"
    except Exception as e:
        return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

# ==============================================================================
# 🎯 LÕI THUẬT TOÁN PAIR HEDGING (BẮT LÔ CẶP CHỐNG TRƯỢT LỘN)
# ==============================================================================
def tinh_lo_cap_anomaly(target_dt, db):
    """
    Thuật toán Lô Cặp V13.0:
    1. Tìm cặp số lộn (A-B và B-A) có tổng điểm Lô rơi + Tần suất cao nhất.
    2. Áp dụng bộ lọc Siêu Bắn Tỉa: Nếu Anomaly Score không đạt đỉnh -> SKIP.
    """
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(12):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        return ["23", "32"], False, "🛑 DỮ LIỆU CHƯA ĐỦ ĐỂ SOI CẶP", 0.0

    scores = np.zeros(100)
    for p in hist_days[0]: scores[p] += 3.5
    for r_p in hist_days[:3]:
        for p in r_p: scores[p] += 1.2

    # Lọc CỨNG Lô Khan (> 5 ngày giam)
    for i in range(100):
        giam = 0
        for r_p in hist_days:
            if i in r_p: break
            giam += 1
        if giam >= 5: scores[i] = -999.0

    # Tính điểm tổng cho từng Cặp Lộn (AB + BA)
    pair_scores = {}
    for i in range(100):
        c1 = f"{i:02d}"
        c2 = c1[1] + c1[0]
        if c1 == c2: continue # Bỏ qua lô kép
        idx1, idx2 = int(c1), int(c2)
        pair_key = tuple(sorted([c1, c2]))
        if pair_key not in pair_scores:
            pair_scores[pair_key] = scores[idx1] + scores[idx2]

    # Sắp xếp cặp điểm cao nhất
    sorted_pairs = sorted(pair_scores.items(), key=lambda x: x[1], reverse=True)
    top_pair = sorted_pairs[0][0]
    best_score = sorted_pairs[0][1]

    # Bộ lọc Siêu Bắn Tỉa (Ngưỡng điểm dị biệt >= 7.5)
    is_trade_day = best_score >= 7.5
    status_msg = f"🟢 XUẤT HIỆN ĐIỂM LỆCH CẶP (Score: {best_score:.1f})" if is_trade_day else f"🛡️ ĐÓNG VAN AN TOÀN (Score {best_score:.1f} < 7.5)"

    return list(top_pair), is_trade_day, status_msg, best_score

# ==============================================================================
# 🖥️ XỬ LÝ 7 PHÂN HỆ GIAO DIỆN
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    res = f"📡 ĐỒNG BỘ DỮ LIỆU & KÍCH HOẠT LÕI V13.0 PAIR HEDGING:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Quy mô dữ liệu Real   : {len(db)} ngày từ Excel\n"
    res += f"• Mốc chốt kết quả VN   : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"💡 CHIẾN THUẬT MỚI: Đánh Lô Cặp Lộn + Siêu Bắn Tỉa (Chỉ bóp cò khi Anomaly >= 7.5)."
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        _, next_date = lay_thoi_gian_thuc_vn()
        pts = int(pts_per_code)
        codes, is_trade, status_msg, score = tinh_lo_cap_anomaly(next_date, db)
        
        gia_von = 23000
        tong_diem = 2 * pts if is_trade else 0
        tong_von = tong_diem * gia_von
        
        res = f"🎯 BÁO CÁO SOI CẶP LÔ LỘN CHO KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"🎚️ Phán quyết Van   : {status_msg}\n"
        res += f"📋 CẶP LÔ CÂN BẰNG : [ {codes[0]} - {codes[1]} ]\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"⚙️ KHUYẾN NGHỊ PHÂN BỔ VỐN:\n"
        res += f" • Đánh đều mỗi con : {pts if is_trade else 0} điểm\n"
        res += f" 💵 TỔNG VỐN GIẢI NGÂN : {tong_von:,.0f} VND\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📈 KỊCH BẢN KHI MỞ THƯỞNG:\n"
        if is_trade:
            rev1 = pts * 80000; net1 = rev1 - tong_von
            rev2 = pts * 2 * 80000; net2 = rev2 - tong_von
            res += f" • Nổ 1 con (1 nháy) : Doanh thu {rev1:,.0f} VND | Lãi ròng: {net1:+10,.0f} VND 🟢\n"
            res += f" • Nổ cả Cặp (2 nháy): Doanh thu {rev2:,.0f} VND | Lãi ròng: {net2:+10,.0f} VND 🟢🟢\n"
        else:
            res += f" 🛡️ Đứng ngoài quan sát, bảo toàn 100% dòng tiền.\n"
        return res
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

def web_phan_he_3_risk_audit(capital_vnd):
    try:
        try: cap_val = float(capital_vnd)
        except: cap_val = 10000000.0
        
        gia_von = 23000
        tong_diem = int(cap_val // gia_von)
        diem_moi_con = int(tong_diem // 2)
        vong_von = diem_moi_con * 2 * gia_von
        
        report = f"🔍 BẢNG QUẢN TRỊ VỐN CÂN BẰNG CHO CẶP LÔ LỘN (1:1):\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f" • Vốn quy đổi tối đa : {tong_diem} điểm\n"
        report += f" • Chia đều cho Cặp   : {diem_moi_con} điểm/con\n"
        report += f" 💵 Vốn thực chi      : {vong_von:,.0f} VND\n"
        report += f" 💵 Dư trả tài khoản  : {cap_val - vong_von:,.0f} VND\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"📊 MẬT ĐỘ LÃI RÒNG:\n"
        report += f" • Nổ 1 con : Lãi ròng +{diem_moi_con * 80000 - vong_von:,.0f} VND 🟢\n"
        report += f" • Nổ cả cặp: Lãi ròng +{diem_moi_con * 2 * 80000 - vong_von:,.0f} VND 🟢🟢\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ. Hãy dùng DD/MM/YYYY."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
            
        pts = int(pts_per_code)
        codes, is_trade, status_msg, _ = tinh_lo_cap_anomaly(d_obj, db)
        lo_to_27 = db[ngay_str]['prizes_str']
        
        nhay_list = [lo_to_27.count(c) for c in codes]
        tong_nhay = sum(nhay_list)
        phi_phien = 2 * pts * 23000 if is_trade else 0
        rev = tong_nhay * pts * 80000 if is_trade else 0
        net_profit = rev - phi_phien
        
        report = f"📡 TRÍCH XUẤT BACKTEST CẶP LỘN CHO NGÀY: {ngay_str}\n"
        report += f"🎚️ Phán quyết Van : {status_msg}\n"
        report += f"📋 Cặp mã soi     : [ {codes[0]} - {codes[1]} ]\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 KẾT QUẢ MỞ THƯỞNG: Nổ x{tong_nhay} nháy thực tế!\n"
        for i in range(2):
            report += f" • Mã [{codes[i]}]: {nhay_list[i]} nháy\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💰 Chi phí vốn : {phi_phien:,.0f} VND\n"
        report += f"💵 Doanh thu   : {rev:,.0f} VND\n"
        report += f"📈 LỢI NHUẬN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

def web_phan_he_5_monthly_audit(month, year, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        pts = int(pts_per_code)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO NHẬT KÝ CẶP LÔ LỘN THÁNG {thang:02d}/{nam}:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; win_days = 0; skip_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            codes, is_trade, _, _ = tinh_lo_cap_anomaly(d_obj, db)
            lo_to_27 = db[ngay_str]['prizes_str']
            
            if not is_trade:
                skip_days += 1
                report += f"{ngay_str} | 🛡️ ĐÓNG VAN  | [ĐÓNG VAN AN TOÀN BẢO TOÀN VỐN]     | {luy_ke_tien:+12,.0f} VND\n"
                continue
                
            traded_days += 1
            tong_nhay = sum(lo_to_27.count(c) for c in codes)
            phi_phien = 2 * pts * 23000
            rev = tong_nhay * pts * 80000
            delta = rev - phi_phien
            luy_ke_tien += delta
            
            status_tag = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else f"🔴 TRƯỢT"
            if delta > 0: win_days += 1
            
            report += f"{ngay_str} | {status_tag:<12} | Cặp: {codes[0]}-{codes[1]} ({pts}đ) | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê Cặp Lộn: Bóp cò {traded_days} phiên | Đứng ngoài né bão {skip_days} phiên\n"
        report += f"🎯 Thắng: {win_days} phiên | Win-Rate thực tế: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
        t1 = res1[0]; t2 = res2[0]
        pts = int(pts_per_code)
        
        t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0; skip_cnt = 0
        report = f"📈 BÁO CÁO CHU KỲ CẶP LÔ TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                codes, is_trade, _, _ = tinh_lo_cap_anomaly(t_curr, db)
                lo_to_27 = db[ngay_str]['prizes_str']
                
                if is_trade:
                    active_days += 1
                    tong_nhay = sum(lo_to_27.count(c) for c in codes)
                    phi_phien = 2 * pts * 23000
                    rev = tong_nhay * pts * 80000
                    delta = rev - phi_phien
                    if delta > 0: win_days += 1
                    tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
                    status_tag = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else f"🔴 TRƯỢT"
                    report += f"{ngay_str} | {status_tag:<12} | Cặp: {codes[0]}-{codes[1]} ({pts}đ) | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
                else:
                    skip_cnt += 1
                    report += f"{ngay_str} | 🛡️ SKIP     | [ĐÓNG VAN AN TOÀN BẢO TOÀN VỐN]    | LK: {luy_ke_range:+12,.0f} VND\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong - tong_von
        win_rate = (win_days / active_days * 100) if active_days > 0 else 0
        
        report += f"-------------------------------------------------------------------------------------------------------\n"
        report += f"📊 Bóp cò: {active_days} phiên | Đứng ngoài né bão: {skip_cnt} phiên\n"
        report += f"🎯 Thắng: {win_days} phiên | Tỷ lệ Win-Rate: {win_rate:.2f}%\n"
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
# 🎨 GIAO DIỆN GRADIO V13.0
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V13.0") as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V13.0 — LÔ CẶP LỘN & SIÊU BẮN TỈA")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT ĐỒNG BỘ CẬP NHẬT CHẾ ĐỘ LÔ CẶP", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Tiến trình Nạp Dữ Liệu", lines=10)
        
    with gr.Tab("🎯 [2] Dự Đoán Cặp Lô Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        pts_2 = gr.Number(label="Số điểm đánh mỗi con lô trong cặp", value=20)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT CẶP LỘN AI KHUYẾN NGHỊ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lô Cặp AI", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn Cân Bằng"):
        cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
        btn_3 = gr.Button("🧪 LẬP KẾ HOẠCH PHÂN BỔ VỐN CẶP LỘN", variant="primary")
        out_3 = gr.Textbox(label="Sơ Đồ Phân Bổ Vốn Cặp Lộn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Cặp Lộn"):
        with gr.Row():
            date_4 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            pts_4 = gr.Number(label="Số điểm/con", value=20)
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST CẶP LỘN", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Cặp Lộn", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
            pts_5 = gr.Number(label="Số điểm/con", value=20)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ CẶP LÔ THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Báo cáo Tài chính Cặp Lô", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            pts_6 = gr.Number(label="Số điểm/con", value=20)
        btn_6 = gr.Button("📈 QUÉT CHU KỲ BÁO CÁO CẶP LÔ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Cặp Lô", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
