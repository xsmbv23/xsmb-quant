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
# 🧬 HẠ TẦNG QUANT V16.1 - MULTI-PAIR SNIPER ENGINE (3-5 CẶP LÔ)
# ==============================================================================
VERSION = "V16.1 MULTI-PAIR SNIPER ENGINE"
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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU LÔ 27 GIẢI TỪ EXCEL!"
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE EXCEL: {e}"

# ==============================================================================
# 🎯 LÕI V16.1: TÍNH TOÁN DỰ ĐOÁN TỪ 3 ĐẾN 5 CẶP LÔ (AB - BA)
# ==============================================================================
def tinh_cap_lo_v16(target_dt, db, num_pairs=3):
    num_pairs = int(num_pairs)
    if num_pairs < 3: num_pairs = 3
    if num_pairs > 5: num_pairs = 5

    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(12):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        default_pairs = [("12", "21"), ("34", "43"), ("56", "65"), ("78", "87"), ("09", "90")]
        return default_pairs[:num_pairs], False, "🛑 THIẾU DATA NỀN - ĐÓNG VAN", 0.0

    scores = np.zeros(100)
    head_counts = np.zeros(10)
    tail_counts = np.zeros(10)

    for p in hist_days[0]:
        scores[p] += 3.8
        head_counts[p // 10] += 1
        tail_counts[p % 10] += 1

    for r_p in hist_days[:3]:
        for p in r_p: scores[p] += 1.2

    for i in range(100):
        h = i // 10; t = i % 10
        if head_counts[h] >= 4: scores[i] += 1.2
        if tail_counts[t] >= 4: scores[i] += 1.2

    # Phong tỏa Lô Khan > 5 ngày
    for i in range(100):
        giam = 0
        for r_p in hist_days:
            if i in r_p: break
            giam += 1
        if giam >= 5: scores[i] = -999.0

    # Ghép cặp lộn (c1, c2)
    pair_scores = {}
    for i in range(100):
        c1 = f"{i:02d}"
        c2 = c1[1] + c1[0]
        if c1 == c2: continue
        pair_key = tuple(sorted([c1, c2]))
        if pair_key not in pair_scores:
            idx1, idx2 = int(c1), int(c2)
            pair_scores[pair_key] = scores[idx1] + scores[idx2]

    sorted_pairs = sorted(pair_scores.items(), key=lambda x: x[1], reverse=True)
    top_pairs = [p[0] for p in sorted_pairs[:num_pairs]]
    top_scores = [p[1] for p in sorted_pairs[:num_pairs]]
    anomaly_score = float(np.mean(top_scores)) if top_scores else 0.0

    # Van bóp cò rủi ro
    if anomaly_score < 6.5:
        is_trade = False
        reason = f"🛡️ ĐÓNG VAN AN TOÀN: Anomaly Score ({anomaly_score:.1f} < 6.5) -> Né nhiễu rác"
    elif anomaly_score < 8.0:
        is_trade = True
        reason = f"🌗 BÓP CÒ 50% VỐN (HALF SNIPER): Anomaly Score ({anomaly_score:.1f})"
    else:
        is_trade = True
        reason = f"🔥 BÓP CÒ 100% VỐN (FULL SNIPER): Anomaly Score ({anomaly_score:.1f})"

    return top_pairs, is_trade, reason, anomaly_score

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN V16.1
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    res = f"📡 KẾT NỐI HỆ THỐNG V16.1 MULTI-PAIR SNIPER ENGINE:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Mốc chốt kết quả VN   : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"💡 CƠ CHẾ MỚI: Dự đoán từ 3 - 5 Cặp Lô lộn, hiển thị chi tiết Cặp Lô, Tổng Tiền, Số Nháy & Số Lãi!"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(num_pairs, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        _, next_date = lay_thoi_gian_thuc_vn()
        n_pairs = int(num_pairs)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        
        pairs, is_trade, reason, sc = tinh_cap_lo_v16(next_date, db, num_pairs=n_pairs)
        pair_strs = [f"{p[0]}-{p[1]}" for p in pairs]
        
        tong_con = n_pairs * 2
        tong_diem = tong_con * pts if is_trade else 0
        tong_von = tong_diem * cost_pt
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN {n_pairs} CẶP LÔ KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"🎚️ Phán quyết Van       : {reason}\n"
        res += f"📋 CẶP LÔ DỰ ĐOÁN       : [ " + ", ".join(pair_strs) + " ]\n"
        res += f"💵 TỔNG TIỀN ĐÁNH       : {tong_von:,.0f} VND ({tong_diem} điểm - Giá {cost_pt:,.0f}đ)\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📈 KỊCH BẢN DOANH THU & SỐ LÃI KHI NỔ NHÁY:\n"
        if not is_trade:
            res += f" 🛡️ Van đóng: Bảo toàn 100% tiền mặt (Tổng tiền đánh: 0 VNĐ - Số lãi: 0 VNĐ)\n"
        else:
            for nhay in range(1, n_pairs + 3):
                rev = nhay * pts * 80000
                so_lai = rev - tong_von
                tag = "🟢 CÓ LÃI" if so_lai > 0 else ("⚖️ HÒA VỐN" if so_lai == 0 else "🔴 ÂM VỐN")
                res += f" • Nổ x{nhay} nháy : Doanh thu {rev:,.0f} VND | Số lãi: {so_lai:+12,.0f} VND [{tag}]\n"
        return res
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

def web_phan_he_3_risk_audit(capital_vnd, num_pairs, cost_per_point):
    try:
        cap_val = float(capital_vnd)
        n_pairs = int(num_pairs)
        cost_pt = float(cost_per_point)
        
        tong_con = n_pairs * 2
        tong_diem_kha_thi = int(cap_val // cost_pt)
        pts_per_code = int(tong_diem_kha_thi // tong_con)
        vong_von = pts_per_code * tong_con * cost_pt
        
        report = f"🔍 SƠ ĐỒ PHÂN BỔ VỐN CHO {n_pairs} CẶP LÔ ({tong_con} CON SỐ):\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f" • Phân bổ đều          : {pts_per_code} điểm/con ({pts_per_code * 2} điểm/cặp)\n"
        report += f" 💵 TỔNG TIỀN ĐÁNH      : {vong_von:,.0f} VND (Giá {cost_pt:,.0f}đ/điểm)\n"
        report += f" 💵 Dư trả tài khoản    : {cap_val - vong_von:,.0f} VND\n"
        report += f"---------------------------------------------------------------------------------\n"
        min_hits = math.ceil(vong_von / (pts_per_code * 80000)) if pts_per_code > 0 else 0
        report += f"📊 Mật độ an toàn: Chỉ cần nổ x{min_hits} nháy là BẮT ĐẦU CÓ SỐ LÃI DƯƠNG! 🟢\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, num_pairs, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
            
        n_pairs = int(num_pairs)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        lo_to_27 = db[ngay_str]['prizes_str']
        
        pairs, is_trade, reason, sc = tinh_cap_lo_v16(d_obj, db, num_pairs=n_pairs)
        pair_strs = [f"{p[0]}-{p[1]}" for p in pairs]
        
        all_codes = []
        for p in pairs:
            all_codes.extend([p[0], p[1]])
            
        nhay_dict = {c: lo_to_27.count(c) for c in all_codes}
        tong_nhay = sum(nhay_dict.values())
        
        tong_von = len(all_codes) * pts * cost_pt if is_trade else 0
        doanh_thu = tong_nhay * pts * 80000 if is_trade else 0
        so_lai = doanh_thu - tong_von
        
        report = f"📡 TRÍCH XUẤT BACKTEST CHO NGÀY: {ngay_str}\n"
        report += f"🎚️ Phán quyết Van     : {reason}\n"
        report += f"📋 CẶP LÔ DỰ ĐOÁN     : [ " + ", ".join(pair_strs) + " ]\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 CHI TIẾT SỐ NHÁY VỀ THỰC TẾ:\n"
        for p in pairs:
            n1 = nhay_dict[p[0]]; n2 = nhay_dict[p[1]]
            report += f" • Cặp [{p[0]}-{p[1]}] : Mã {p[0]} (x{n1}n), Mã {p[1]} (x{n2}n) -> Tổng x{n1+n2} nháy\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💥 TỔNG SỐ NHÁY TRÚNG : x{tong_nhay} nháy\n"
        report += f"💵 TỔNG TIỀN ĐÁNH     : {tong_von:,.0f} VND\n"
        report += f"💵 TỔNG DOANH THU     : {doanh_thu:,.0f} VND\n"
        report += f"📈 SỐ LÃI (LỢI NHUẬN) : {'+' if so_lai>=0 else ''}{so_lai:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

def web_phan_he_5_monthly_audit(month, year, num_pairs, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        n_pairs = int(num_pairs)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO TÀI CHÍNH LŨY KẾ {n_pairs} CẶP LÔ THÁNG {thang:02d}/{nam}:\n"
        report += f"---------------------------------------------------------------------------------------------------------------------\n"
        report += f"{'NGÀY':<10} | {'CẶP LÔ DỰ ĐOÁN':<20} | {'TIỀN ĐÁNH':<12} | {'SỐ NHÁY':<8} | {'SỐ LÃI PHIÊN':<14} | {'LŨY KẾ LÃI':<15}\n"
        report += f"---------------------------------------------------------------------------------------------------------------------\n"
        
        luy_ke_tien = 0; traded_days = 0; skip_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            pairs, is_trade, _, _ = tinh_cap_lo_v16(d_obj, db, num_pairs=n_pairs)
            pair_strs = ",".join(f"{p[0]}-{p[1]}" for p in pairs)
            lo_to_27 = db[ngay_str]['prizes_str']
            
            if not is_trade:
                skip_days += 1
                report += f"{ngay_str} | {pair_strs:<20} | {0:>12,.0f} | {0:>8} | {0:>+14,.0f} | {luy_ke_tien:>+15,.0f} VND (🛡️ SKIP)\n"
                continue
                
            traded_days += 1
            all_codes = [c for p in pairs for c in p]
            tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
            
            tong_von = len(all_codes) * pts * cost_pt
            doanh_thu = tong_nhay * pts * 80000
            so_lai = doanh_thu - tong_von
            luy_ke_tien += so_lai
            
            if so_lai >= 0: win_days += 1
            report += f"{ngay_str} | {pair_strs:<20} | {tong_von:>12,.0f} | {tong_nhay:>8} | {so_lai:>+14,.0f} | {luy_ke_tien:>+15,.0f} VND\n"
            
        report += f"---------------------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê: Bóp cò {traded_days} phiên | Đóng van bảo toàn: {skip_days} phiên | Win-Rate: {win_rate:.2f}%\n"
        report += f"💰 TỔNG SỐ LÃI LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, num_pairs, cost_per_point, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
        t1 = res1[0]; t2 = res2[0]
        n_pairs = int(num_pairs)
        cost_pt = float(cost_per_point)
        pts = int(pts_per_code)
        
        t_curr = t1; tong_von_all = 0; tong_thuong_all = 0; luy_ke_range = 0; active_days = 0; win_days = 0; skip_cnt = 0
        report = f"📈 BÁO CÁO CHU KỲ TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
        report += f"---------------------------------------------------------------------------------------------------------------------\n"
        report += f"{'NGÀY':<10} | {'CẶP LÔ DỰ ĐOÁN':<20} | {'TIỀN ĐÁNH':<12} | {'SỐ NHÁY':<8} | {'SỐ LÃI PHIÊN':<14} | {'LŨY KẾ LÃI':<15}\n"
        report += f"---------------------------------------------------------------------------------------------------------------------\n"
        
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                pairs, is_trade, _, _ = tinh_cap_lo_v16(t_curr, db, num_pairs=n_pairs)
                pair_strs = ",".join(f"{p[0]}-{p[1]}" for p in pairs)
                lo_to_27 = db[ngay_str]['prizes_str']
                
                if is_trade:
                    active_days += 1
                    all_codes = [c for p in pairs for c in p]
                    tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
                    
                    phi_phien = len(all_codes) * pts * cost_pt
                    rev = tong_nhay * pts * 80000
                    so_lai = rev - phi_phien
                    if so_lai >= 0: win_days += 1
                    
                    tong_von_all += phi_phien; tong_thuong_all += rev; luy_ke_range += so_lai
                    report += f"{ngay_str} | {pair_strs:<20} | {phi_phien:>12,.0f} | {tong_nhay:>8} | {so_lai:>+14,.0f} | {luy_ke_range:>+15,.0f} VND\n"
                else:
                    skip_cnt += 1
                    report += f"{ngay_str} | {pair_strs:<20} | {0:>12,.0f} | {0:>8} | {0:>+14,.0f} | {luy_ke_range:>+15,.0f} VND (🛡️ SKIP)\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong_all - tong_von_all
        win_rate = (win_days / active_days * 100) if active_days > 0 else 0
        
        report += f"---------------------------------------------------------------------------------------------------------------------\n"
        report += f"📊 Quét: Bóp cò {active_days} phiên | Đứng ngoài né bão: {skip_cnt} phiên\n"
        report += f"🎯 Phiên có lãi/hòa: {win_days} | Tỷ lệ An toàn: {win_rate:.2f}%\n"
        report += f"💵 TỔNG TIỀN ĐÁNH    : {tong_von_all:,.0f} VND\n"
        report += f"💵 TỔNG DOANH THU    : {tong_thuong_all:,.0f} VND\n"
        report += f"💰 TỔNG SỐ LÃI RÒNG  : {net_profit:+,.0f} VND\n"
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
# 🎨 GIAO DIỆN GRADIO V16.1
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V16.1") as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V16.1 — MULTI-PAIR SNIPER (3-5 CẶP LÔ)")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT ĐỒNG BỘ CẬP NHẬT CHẾ ĐỘ MULTI-PAIR", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=8)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        with gr.Row():
            np_2 = gr.Dropdown(label="Chọn số Cặp Lô dự đoán", choices=["3", "4", "5"], value="3")
            cost_2 = gr.Number(label="Giá vốn điểm (21700đ Web hoặc 23000đ Thường)", value=21700)
            pts_2 = gr.Number(label="Số điểm đánh mỗi con lô", value=10)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT DỰ ĐOÁN CẶP LÔ AI", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán Cặp Lô AI", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[np_2, cost_2, pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
            np_3 = gr.Dropdown(label="Số Cặp Lô chia vốn", choices=["3", "4", "5"], value="3")
            cost_3 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_3 = gr.Button("🧪 LẬP SƠ ĐỒ PHÂN BỔ VỐN CẶP LÔ", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, np_3, cost_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        with gr.Row():
            date_4 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            np_4 = gr.Dropdown(label="Số Cặp Lô", choices=["3", "4", "5"], value="3")
            cost_4 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_4 = gr.Number(label="Số điểm/con", value=10)
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST CẶP LÔ", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Cặp Lô", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, np_4, cost_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
            np_5 = gr.Dropdown(label="Số Cặp Lô", choices=["3", "4", "5"], value="3")
            cost_5 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_5 = gr.Number(label="Số điểm/con", value=10)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ CẶP LÔ THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Báo cáo Tài chính Lũy kế", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, np_5, cost_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            np_6 = gr.Dropdown(label="Số Cặp Lô", choices=["3", "4", "5"], value="3")
            cost_6 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_6 = gr.Number(label="Số điểm/con", value=10)
        btn_6 = gr.Button("📈 QUÉT CHU KỲ BÁO CÁO TÀI CHÍNH", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Cặp Lô", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, np_6, cost_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải Real", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
