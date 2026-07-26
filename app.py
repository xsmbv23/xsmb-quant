import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V29.1 - 3 PAIRS REBOOT (FULL 7 MENUS)
# ==============================================================================
VERSION = "V29.1 3-PAIRS MASTER"
DATA_FILE = "Ket_Qua_Loto27.xlsx"

def chuan_hoa_ngay(ngay_raw):
    if not ngay_raw or pd.isna(ngay_raw) or not str(ngay_raw).strip(): return None
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

def lay_max_days(thang, nam=2026):
    if thang == 2: return 29 if (nam % 4 == 0 and (nam % 100 != 0 or nam % 400 == 0)) else 28
    elif thang in [4, 6, 9, 11]: return 30
    return 31

def doc_database_tu_excel():
    db = {}
    if not os.path.exists(DATA_FILE): return db, f"🛑 CHƯA THẤY FILE '{DATA_FILE}' TRÊN SERVER!"
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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU THỰC TẾ!"
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db:
        dt_fallback = datetime(2026, 7, 21)
        return dt_fallback, dt_fallback + timedelta(days=1)
    max_dt = max(info['date_obj'] for info in db.values())
    next_predict_dt = max_dt + timedelta(days=1)
    return max_dt, next_predict_dt

# ==============================================================================
# 🎯 LÕI V29.1: BỘ LỌC ĐỘC BẢN TÌM ĐÚNG 3 CẶP
# ==============================================================================
def loc_3_cap_lo_roi(target_dt, db):
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(10):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db: hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        return [], False, "🛑 CHƯA ĐỦ DỮ LIỆU EXCEL (< 3 ngày) ĐỂ LỌC!"

    day_t_minus_1 = hist_days[0]
    unique_nums = list(set(day_t_minus_1))
    counts_t1 = {x: day_t_minus_1.count(x) for x in unique_nums}
    
    # Lọc kép và nổ nhiều nháy
    pool = [x for x in unique_nums if (x // 10 != x % 10) and (counts_t1[x] == 1)]
    
    candidate_pairs = []
    visited = set()
    for x in pool:
        if x in visited: continue
        rev_x = (x % 10) * 10 + (x // 10)
        pair = tuple(sorted([x, rev_x]))
        candidate_pairs.append(pair)
        visited.add(x)
        visited.add(rev_x)
        
    pair_scores = {}
    for pair in set(candidate_pairs):
        a, b = pair
        score = 0.0
        if a in pool and b in pool: score += 10.0
        elif a in pool or b in pool: score += 5.0
            
        freq_a = sum([1 for d in hist_days[:7] if a in d])
        freq_b = sum([1 for d in hist_days[:7] if b in d])
        
        if 1 <= freq_a <= 2: score += 2.0
        elif freq_a == 0: score -= 3.0
        elif freq_a >= 4: score -= 2.0
        
        if 1 <= freq_b <= 2: score += 2.0
        elif freq_b == 0: score -= 3.0
        elif freq_b >= 4: score -= 2.0
            
        pair_scores[pair] = score

    sorted_pairs = sorted(pair_scores.items(), key=lambda k: k[1], reverse=True)
    top_3_pairs = [p[0] for p in sorted_pairs[:3]]
    
    if len(top_3_pairs) == 0:
        return [], False, "🛑 Lồng cầu hôm trước quá nhiễu, bộ lọc đã quét sạch không còn số nào!"
        
    return top_3_pairs, True, "🔥 CHỐT 3 CẶP LÔ RƠI TỐT NHẤT TỪ HÔM TRƯỚC"

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN
# ==============================================================================

# --- TAB 1 ---
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    res = f"📡 KẾT NỐI HỆ THỐNG V29.1 FULL 7 MENUS:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File Excel : {msg}\n"
    res += f"• Ngày chốt Excel gần nhất: 📅 [{latest_dt.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán MỚI  : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]\n"
    return res, f"#### Kỳ quay dự đoán tiếp theo: {next_predict_dt.strftime('%d/%m/%Y')}"

# --- TAB 2 ---
def web_phan_he_2_predict(cost_per_point, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
        cost_pt = float(cost_per_point)
        actual_pts = int(pts_per_code_base)
        
        pairs, is_trade, reason = loc_3_cap_lo_roi(next_predict_dt, db)
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN V29.1 CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"📌 Dựa trên kết quả Excel ngày: {latest_dt.strftime('%d/%m/%Y')}\n"
        res += f"=================================================================================\n"
        res += f"🎚️ TRẠNG THÁI BỘ LỌC : {reason}\n"
        res += f"=================================================================================\n"
        
        if not is_trade:
            res += f"🛑 TRẠNG THÁI: KHÔNG ĐỦ ĐIỀU KIỆN LỌC\n"
            return res

        tong_con = len(pairs) * 2
        tong_von = tong_con * actual_pts * cost_pt
        
        res += f"📋 TRÍCH XUẤT ĐÚNG {len(pairs)} CẶP ({tong_con} con số):\n"
        for idx, p in enumerate(pairs):
            res += f"   • Cặp {idx+1}: [{p[0]:02d} - {p[1]:02d}] | Cược thực tế: {actual_pts} điểm/con\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"💰 TỔNG TIỀN ĐÁNH THỰC TẾ : {tong_von:,.0f} VND\n"
        res += f"📈 KỊCH BẢN DOANH THU & LÃI RÒNG:\n"
        for nhay in range(1, tong_con + 2):
            rev = nhay * actual_pts * 80000
            so_lai = rev - tong_von
            roi = (so_lai / tong_von * 100) if tong_von > 0 else 0
            tag = "🟢 CÓ LÃI" if so_lai > 0 else "🔴 ÂM VỐN"
            res += f" • Nổ x{nhay} nháy: Doanh thu {rev:,.0f}đ | Số Lãi: {so_lai:+11,.0f}đ | ROI: {roi:+6.1f}% [{tag}]\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 2: {e}"

# --- TAB 3 ---
def web_phan_he_3_risk_audit(capital_vnd, cost_per_point):
    try:
        cap_val = float(capital_vnd)
        cost_pt = float(cost_per_point)
        pts_per_code = int((cap_val // cost_pt) // 6) # Phân bổ cho 6 con (3 cặp)
        von_tong = pts_per_code * 6 * cost_pt
        
        report = f"🔍 QUẢN TRỊ VỐN V29.1 - ĐÁNH 3 CẶP (6 SỐ) VỚI {cap_val:,.0f} VND:\n"
        report += f"=================================================================================\n"
        report += f"📊 MỨC PHÂN BỔ TỐI ƯU CHO 3 CẶP:\n"
        report += f" • Mức cược mỗi con: {pts_per_code} điểm (Tổng {pts_per_code*6} điểm)\n"
        report += f" 💵 TỔNG TIỀN ĐÁNH : {von_tong:,.0f} VND\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 KỊCH BẢN ĐIỂM HÒA VỐN & CÓ LÃI:\n"
        for n in range(1, 5):
            doanh_thu = pts_per_code * n * 80000
            lai = doanh_thu - von_tong
            tag = "🟢 CÓ LÃI" if lai > 0 else "🔴 ÂM VỐN"
            report += f" • Nổ x{n} nháy: Thu về {doanh_thu:,.0f}đ -> {tag} ({lai:+,.0f} VND)\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 3: {e}"

# --- TAB 4 ---
def web_phan_he_4_single_day_backtest(ngay_raw, cost_per_point, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} CHƯA CÓ TRONG FILE EXCEL!"
            
        cost_pt = float(cost_per_point)
        actual_pts = int(pts_per_code_base)
        lo_to_27 = db[ngay_str]['prizes_int']
        
        pairs, is_trade, reason = loc_3_cap_lo_roi(d_obj, db)
        
        report = f"📡 TRÍCH XUẤT BACKTEST KỲ NGÀY EXCEL: {ngay_str}\n"
        report += f"=================================================================================\n"
        if not is_trade:
            return report + f"🛑 TRẠNG THÁI: {reason}\n"

        all_codes = [c for p in pairs for c in p]
        nhay_dict = {c: lo_to_27.count(c) for c in all_codes}
        tong_nhay = sum(nhay_dict.values())
        tong_von = len(all_codes) * actual_pts * cost_pt
        doanh_thu = tong_nhay * actual_pts * 80000
        so_lai = doanh_thu - tong_von
        
        report += f"🎯 BÓC TÁCH KẾT QUẢ THỰC TẾ (Đánh {len(pairs)} cặp | Cược {actual_pts}đ/con):\n"
        for idx, p in enumerate(pairs):
            n1 = nhay_dict[p[0]]; n2 = nhay_dict[p[1]]
            report += f" • Cặp {idx+1} [{p[0]:02d} - {p[1]:02d}]: Về x{n1+n2} nháy\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💥 TỔNG SỐ NHÁY TRÚNG : x{tong_nhay} nháy\n"
        report += f"💵 TỔNG TIỀN ĐÁNH     : {tong_von:,.0f} VND\n"
        report += f"📈 SỐ LÃI RÒNG (NET)  : {'+' if so_lai>=0 else ''}{so_lai:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 4: {e}"

# --- TAB 5 ---
def web_phan_he_5_monthly_audit(month, year, cost_per_point, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        cost_pt = float(cost_per_point)
        actual_pts = int(pts_per_code_base)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO LŨY KẾ THÁNG {thang:02d}/{nam} (ĐÁNH 3 CẶP CỐ ĐỊNH):\n"
        report += f"===============================================================================================================\n"
        report += f"{'NGÀY':<10} | {'3 CẶP DỰ ĐOÁN':<22} | {'TIỀN ĐÁNH':<12} | {'NHÁY':<5} | {'SỐ LÃI PHIÊN':<12} | {'LŨY KẾ LÃI':<12}\n"
        report += f"===============================================================================================================\n"
        
        luy_ke_tien = 0; traded_days = 0; win_days = 0
        tong_von = 0; tong_thuong = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            pairs, is_trade, _ = loc_3_cap_lo_roi(d_obj, db)
            lo_to_27 = db[ngay_str]['prizes_int']
            
            if not is_trade:
                report += f"{ngay_str} | {'KHÔNG ĐỦ DỮ LIỆU LỌC':<22} | {0:>12,.0f} | {0:>5} | {0:>+12,.0f} | {luy_ke_tien:>+12,.0f}\n"
                continue
                
            traded_days += 1
            all_codes = [c for p in pairs for c in p]
            tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
            
            phi_phien = len(all_codes) * actual_pts * cost_pt
            doanh_thu = tong_nhay * actual_pts * 80000
            so_lai = doanh_thu - phi_phien
            
            tong_von += phi_phien; tong_thuong += doanh_thu
            luy_ke_tien += so_lai
            if so_lai >= 0: win_days += 1
                
            pair_strs = ", ".join(f"{p[0]:02d}-{p[1]:02d}" for p in pairs)
            report += f"{ngay_str} | {pair_strs:<22} | {phi_phien:>12,.0f} | {tong_nhay:>5} | {so_lai:>+12,.0f} | {luy_ke_tien:>+12,.0f}\n"
            
        report += f"===============================================================================================================\n"
        report += f"📊 TỔNG KẾT THÁNG {thang:02d}/{nam}:\n"
        report += f" • Ngày đánh: {traded_days} ngày | Ngày có lãi: {win_days} ngày\n"
        report += f" 💰 LÃI RÒNG TRONG THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 5: {e}"

# --- TAB 6 ---
def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, cost_per_point, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi định dạng ngày."
        t1, t2 = res1[0], res2[0]
        if t1 > t2: t1, t2 = t2, t1
            
        cost_pt = float(cost_per_point)
        actual_pts = int(pts_per_code_base)
        
        t_curr = t1
        tong_von = 0; tong_thuong = 0
        luy_ke_range = 0
        trades = 0; win_days = 0
        
        report = f"📈 BÁO CÁO CHU KỲ (CHIẾN THUẬT ĐÁNH 3 CẶP):\n"
        report += f"===============================================================================================================\n"
        report += f"{'NGÀY':<10} | {'3 CẶP DỰ ĐOÁN':<22} | {'TIỀN ĐÁNH':<12} | {'NHÁY':<5} | {'SỐ LÃI PHIÊN':<12} | {'LŨY KẾ LÃI':<12}\n"
        report += f"===============================================================================================================\n"
        
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                pairs, is_trade, _ = loc_3_cap_lo_roi(t_curr, db)
                lo_to_27 = db[ngay_str]['prizes_int']
                
                if not is_trade:
                    report += f"{ngay_str} | {'KHÔNG ĐỦ DỮ LIỆU LỌC':<22} | {0:>12,.0f} | {0:>5} | {0:>+12,.0f} | {luy_ke_range:>+12,.0f}\n"
                else:
                    trades += 1
                    all_codes = [c for p in pairs for c in p]
                    tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
                    phi_phien = len(all_codes) * actual_pts * cost_pt
                    rev = tong_nhay * actual_pts * 80000
                    so_lai = rev - phi_phien
                    
                    if so_lai >= 0: win_days += 1
                    tong_von += phi_phien; tong_thuong += rev; luy_ke_range += so_lai
                    
                    pair_strs = ", ".join(f"{p[0]:02d}-{p[1]:02d}" for p in pairs)
                    report += f"{ngay_str} | {pair_strs:<22} | {phi_phien:>12,.0f} | {tong_nhay:>5} | {so_lai:>+12,.0f} | {luy_ke_range:>+12,.0f}\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong - tong_von
        report += f"===============================================================================================================\n"
        report += f"📊 THỐNG KÊ CHU KỲ:\n"
        report += f" • Bóp cò khai hỏa: {trades} phiên | Thắng (Lãi): {win_days} phiên\n"
        report += f" 💰 TỔNG SỐ LÃI RÒNG CHU KỲ: {net_profit:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 6: {e}"

# --- TAB 7 ---
def web_phan_he_7_raw_db_lookup(ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        _, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} CHƯA CÓ TRONG FILE EXCEL!"
            
        lo_to_raw = db[ngay_str]['prizes_int']
        lo_to_sorted = sorted([f"{x:02d}" for x in lo_to_raw])
        report = f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY {ngay_str}:\n"
        report += "🎰 27 Giải ma trận phẳng:\n"
        for idx, lo in enumerate(lo_to_sorted): 
            report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
        return report
    except Exception as e: return f"🛑 LỖI TAB 7: {e}"

# ==============================================================================
# 🎨 DỰNG LÊN GIAO DIỆN GRADIO V29.1
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V29.1") as demo:
    gr.Markdown("# 🚀 XSMB QUANT V29.1 — 3 PAIRS REBOOT & FULL 7 MENUS")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP DỮ LIỆU", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=5)
        
    with gr.Tab("🎯 [2] Dự Đoán (3 Cặp)"):
        title_2 = gr.Markdown(f"#### Kỳ quay dự đoán tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            cost_2 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ", value=10)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT LỆNH", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V29.1", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[cost_2, pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
            cost_3 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_3 = gr.Button("🧪 PHÂN BỔ VỐN CHO 3 CẶP", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, cost_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Ngày"):
        with gr.Row():
            date_4 = gr.Textbox(label="Ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            cost_4 = gr.Number(label="Giá vốn", value=21700)
            pts_4 = gr.Number(label="Cược CƠ SỞ", value=10)
        btn_4 = gr.Button("📡 BACKTEST V29.1", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, cost_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng", value=latest_dt_init.month)
            y_5 = gr.Number(label="Năm", value=latest_dt_init.year)
            cost_5 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_5 = gr.Number(label="Mốc cược CƠ SỞ", value=10)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Bảng Nhật ký", lines=18)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, cost_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Quét Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày", value="01/01/2026")
            t2_6 = gr.Textbox(label="Đến ngày", value=latest_dt_init.strftime("%d/%m/%Y"))
            cost_6 = gr.Number(label="Giá vốn", value=21700)
            pts_6 = gr.Number(label="Mốc cược", value=10)
        btn_6 = gr.Button("📈 QUÉT CHU KỲ V29.1", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Dòng tiền", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, cost_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả", lines=8)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
