import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 V29.0 REBOOT - LÔ RƠI ĐỘC BẢN (CHỈ DÙNG KẾT QUẢ HÔM TRƯỚC)
# ==============================================================================
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

def doc_database_tu_excel():
    db = {}
    if not os.path.exists(DATA_FILE): return db, f"🛑 LỖI: Chưa có file {DATA_FILE}"
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
        return db, f"🟢 ĐÃ NẠP {len(db)} NGÀY DỮ LIỆU"
    except Exception as e: return db, f"🛑 LỖI EXCEL: {e}"

# 🎯 LÕI V29: BỘ LỌC 5 LỚP TÌM ĐÚNG 3 CẶP
def loc_3_cap_lo_roi(target_dt, db):
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(10): # Chỉ cần nhìn lại 10 ngày để đo nhịp
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db: hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        return [], "🛑 CHƯA ĐỦ DỮ LIỆU EXCEL ĐỂ LỌC!"

    day_t_minus_1 = hist_days[0] # 27 kết quả của HÔM TRƯỚC
    
    # LỌC 1: Lấy số độc bản
    unique_nums = list(set(day_t_minus_1))
    counts_t1 = {x: day_t_minus_1.count(x) for x in unique_nums}
    
    # LỌC 2 & 3: Bỏ Lô Kép & Bỏ Lô Nhiều Nháy
    pool = [x for x in unique_nums if (x // 10 != x % 10) and (counts_t1[x] == 1)]
    
    # LỌC 4: Định hình cặp lộn (AB - BA)
    candidate_pairs = []
    visited = set()
    for x in pool:
        if x in visited: continue
        rev_x = (x % 10) * 10 + (x // 10)
        pair = tuple(sorted([x, rev_x]))
        candidate_pairs.append(pair)
        visited.add(x)
        visited.add(rev_x)
        
    # LỌC 5: Chấm điểm chọn Top 3 Cặp
    pair_scores = {}
    for pair in set(candidate_pairs):
        a, b = pair
        score = 0.0
        
        # Điểm Tuyệt Đối: Cả AB và BA đều nổ hôm trước (Cặp tương phùng)
        if a in pool and b in pool:
            score += 10.0
        elif a in pool or b in pool:
            score += 5.0
            
        # Kiểm tra nhịp 7 ngày (Tránh lô khan và lô quá nóng)
        freq_a = sum([1 for d in hist_days[:7] if a in d])
        freq_b = sum([1 for d in hist_days[:7] if b in d])
        
        if 1 <= freq_a <= 2: score += 2.0
        elif freq_a == 0: score -= 3.0 # Đang khan
        elif freq_a >= 4: score -= 2.0 # Đã nổ quá dày
        
        if 1 <= freq_b <= 2: score += 2.0
        elif freq_b == 0: score -= 3.0
        elif freq_b >= 4: score -= 2.0
            
        pair_scores[pair] = score

    # Sắp xếp và lấy ĐÚNG 3 CẶP cao điểm nhất
    sorted_pairs = sorted(pair_scores.items(), key=lambda k: k[1], reverse=True)
    top_3_pairs = [p[0] for p in sorted_pairs[:3]]
    
    if len(top_3_pairs) == 0:
        return [], "🛑 Lồng cầu hôm trước quá nhiễu, bộ lọc đã quét sạch không còn số nào!"
        
    return top_3_pairs, "🔥 BỘ LỌC ĐÃ CHỐT 3 CẶP XUẤT SẮC NHẤT TỪ NGÀY HÔM TRƯỚC"

# ==============================================================================
# GIAO DIỆN XỬ LÝ (GỌN GÀNG, KHÔNG RƯỜM RÀ)
# ==============================================================================
def ui_predict(ngay_raw, v_diem, c_diem):
    db, _ = doc_database_tu_excel()
    dt_obj = chuan_hoa_ngay(ngay_raw)
    if not dt_obj: return "🛑 Lỗi ngày!"
    
    pairs, msg = loc_3_cap_lo_roi(dt_obj[0], db)
    if not pairs: return msg
    
    tong_con = len(pairs) * 2
    tien_danh = tong_con * c_diem * v_diem
    
    res = f"🎯 KẾT QUẢ BỘ LỌC V29.0 CHO NGÀY: {dt_obj[1]}\n"
    res += f"=========================================================\n"
    res += f"📌 TRÍCH XUẤT ĐÚNG 3 CẶP (6 SỐ):\n"
    for i, p in enumerate(pairs):
        res += f"  • Cặp {i+1}: [{p[0]:02d} - {p[1]:02d}] (Đánh {c_diem}đ/con)\n"
    res += f"---------------------------------------------------------\n"
    res += f"💰 TỔNG TIỀN ĐÁNH: {tien_danh:,.0f} VNĐ\n"
    for n in range(1, tong_con+1):
        thuong = n * c_diem * 80000
        lai = thuong - tien_danh
        tag = "🟢 LÃI" if lai > 0 else "🔴 LỖ"
        res += f" • Nổ {n} nháy: Thu về {thuong:,.0f}đ -> {tag} {lai:+,.0f}đ\n"
    return res

def ui_backtest(ngay_raw, v_diem, c_diem):
    db, _ = doc_database_tu_excel()
    dt_obj = chuan_hoa_ngay(ngay_raw)
    if not dt_obj or dt_obj[1] not in db: return "🛑 Lỗi: Ngày không có trong Excel!"
    
    pairs, msg = loc_3_cap_lo_roi(dt_obj[0], db)
    if not pairs: return msg
    
    lo_to = db[dt_obj[1]]['prizes_int']
    all_codes = [c for p in pairs for c in p]
    nhay_dict = {c: lo_to.count(c) for c in all_codes}
    tong_nhay = sum(nhay_dict.values())
    
    tien_danh = len(all_codes) * c_diem * v_diem
    tien_thuong = tong_nhay * c_diem * 80000
    lai = tien_thuong - tien_danh
    
    res = f"📡 BACKTEST THỰC TẾ NGÀY: {dt_obj[1]}\n"
    res += f"=========================================================\n"
    for i, p in enumerate(pairs):
        n1, n2 = nhay_dict[p[0]], nhay_dict[p[1]]
        res += f"  • Cặp {i+1} [{p[0]:02d} - {p[1]:02d}]: Về {n1+n2} nháy\n"
    res += f"---------------------------------------------------------\n"
    res += f"💥 TỔNG NHÁY: {tong_nhay} nháy\n"
    res += f"💰 TIỀN ĐÁNH: {tien_danh:,.0f} VNĐ\n"
    res += f"📈 LÃI RÒNG:  {lai:+,.0f} VNĐ\n"
    return res

def ui_range(t1_raw, t2_raw, v_diem, c_diem):
    db, _ = doc_database_tu_excel()
    dt1 = chuan_hoa_ngay(t1_raw); dt2 = chuan_hoa_ngay(t2_raw)
    if not dt1 or not dt2: return "🛑 Lỗi ngày!"
    
    curr = min(dt1[0], dt2[0]); end = max(dt1[0], dt2[0])
    
    rep = f"📈 BÁO CÁO CHU KỲ (ĐÁNH 3 CẶP/NGÀY)\n"
    rep += "="*90 + "\n"
    rep += f"{'NGÀY':<12} | {'3 CẶP CHỐT':<22} | {'TIỀN ĐÁNH':<12} | {'NHÁY':<5} | {'LÃI PHIÊN':<12} | {'LŨY KẾ':<12}\n"
    rep += "="*90 + "\n"
    
    luy_ke = 0; trades = 0; tong_nhay_all = 0
    while curr <= end:
        s_str = curr.strftime("%d/%m/%Y")
        if s_str in db:
            pairs, msg = loc_3_cap_lo_roi(curr, db)
            if pairs:
                trades += 1
                lo_to = db[s_str]['prizes_int']
                all_codes = [c for p in pairs for c in p]
                nhay = sum(lo_to.count(c) for c in all_codes)
                tong_nhay_all += nhay
                
                phi = len(all_codes) * c_diem * v_diem
                thuong = nhay * c_diem * 80000
                lai = thuong - phi
                luy_ke += lai
                
                p_str = ", ".join(f"{p[0]:02d}-{p[1]:02d}" for p in pairs)
                rep += f"{s_str:<12} | {p_str:<22} | {phi:<12,.0f} | {nhay:<5} | {lai:>+12,.0f} | {luy_ke:>+12,.0f}\n"
        curr += timedelta(days=1)
        
    rep += "="*90 + "\n"
    rep += f"📊 TỔNG KẾT: Đánh {trades} phiên | Tổng nháy trúng: {tong_nhay_all} | LÃI RÒNG CHU KỲ: {luy_ke:+,.0f} VNĐ\n"
    return rep

# TẠO GIAO DIỆN
with gr.Blocks(title="V29.0 LÔ RƠI MASTER") as demo:
    gr.Markdown("# 🚀 V29.0 REBOOT — CHỈ ĐÁNH 3 CẶP LÔ RƠI TỪ HÔM TRƯỚC")
    
    with gr.Tab("1. Nạp Dữ Liệu"):
        btn1 = gr.Button("⚡ KIỂM TRA FILE EXCEL", variant="primary")
        out1 = gr.Textbox(lines=2)
        btn1.click(lambda: doc_database_tu_excel()[1], outputs=out1)
        
    with gr.Tab("2. Dự Đoán Hôm Nay"):
        with gr.Row():
            d2 = gr.Textbox(label="Ngày cần chốt số (DD/MM/YYYY)")
            v2 = gr.Number(label="Giá vốn điểm", value=21700)
            c2 = gr.Number(label="Mốc cược điểm/con", value=10)
        btn2 = gr.Button("🔍 TÌM 3 CẶP HÔM NAY", variant="primary")
        out2 = gr.Textbox(lines=10)
        btn2.click(ui_predict, inputs=[d2, v2, c2], outputs=out2)
        
    with gr.Tab("3. Backtest Đơn Ngày"):
        with gr.Row():
            d3 = gr.Textbox(label="Ngày đã quay (DD/MM/YYYY)")
            v3 = gr.Number(label="Giá vốn điểm", value=21700)
            c3 = gr.Number(label="Mốc cược điểm/con", value=10)
        btn3 = gr.Button("📡 XEM LẠI KẾT QUẢ", variant="primary")
        out3 = gr.Textbox(lines=8)
        btn3.click(ui_backtest, inputs=[d3, v3, c3], outputs=out3)
        
    with gr.Tab("4. Test Dòng Tiền Chu Kỳ"):
        with gr.Row():
            t1 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)")
            t2 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)")
            v4 = gr.Number(label="Giá vốn", value=21700)
            c4 = gr.Number(label="Cược điểm", value=10)
        btn4 = gr.Button("📈 TEST TỔNG QUAN", variant="primary")
        out4 = gr.Textbox(lines=15)
        btn4.click(ui_range, inputs=[t1, t2, v4, c4], outputs=out4)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=10000)
