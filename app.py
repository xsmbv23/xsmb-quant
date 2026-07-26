import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V30.0 - NUÔI KHUNG 5 NGÀY MASTER
# ==============================================================================
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

# Tỷ lệ vào tiền 5 ngày (Gấp thếp an toàn: 1, 2, 4, 8, 16)
TY_LE_VAO_TIEN = [1, 2, 4, 8, 16] 

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
    if not os.path.exists(DATA_FILE): return db, f"🛑 CHƯA THẤY FILE '{DATA_FILE}'"
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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY"
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db: return datetime(2026, 7, 21), datetime(2026, 7, 22)
    max_dt = max(info['date_obj'] for info in db.values())
    return max_dt, max_dt + timedelta(days=1)

# 🎯 BỘ LỌC TÌM CẶP SONG THỦ ĐỂ NUÔI (LÒ XO NÉN)
def tim_cap_nuoi(target_dt, db):
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    # Lấy 30 ngày để phân tích
    for _ in range(30):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db: hist_days.append(db[s_str]['prizes_int'])
        else: hist_days.append([]) # Điền rỗng nếu thiếu
        curr_t -= timedelta(days=1)

    if not hist_days[0]: return [] # Ngày gần nhất không có dữ liệu

    pair_scores = {}
    for i in range(10, 100):
        if i % 10 == i // 10: continue # Bỏ lô kép
        c1 = i; c2 = (i % 10)*10 + (i // 10)
        pair = tuple(sorted([c1, c2]))
        if pair in pair_scores: continue
        
        # Đếm số ngày chưa ra (Độ nén lò xo)
        days_missed = 0
        for day_res in hist_days:
            if c1 in day_res or c2 in day_res: break
            days_missed += 1
            
        # Tìm cặp đang gan đúng 4-6 ngày (Chuẩn bị điểm nổ)
        if 4 <= days_missed <= 6:
            # Tần suất trong 30 ngày qua (Phải là cặp hay về, không bị khan dài hạn)
            freq_30 = sum(1 for day_res in hist_days if c1 in day_res or c2 in day_res)
            if freq_30 >= 6: # Ít nhất 6 lần ra trong 30 ngày
                pair_scores[pair] = freq_30

    # Lấy cặp có điểm tần suất cao nhất
    if not pair_scores: return []
    sorted_pairs = sorted(pair_scores.items(), key=lambda k: k[1], reverse=True)
    return sorted_pairs[0][0]

# ==============================================================================
# 🖥️ GIAO DIỆN GRADIO
# ==============================================================================

def ui_lap_bang_von(base_pts):
    base_pts = int(base_pts)
    res = f"📊 BẢNG KẾ HOẠCH DÒNG TIỀN (VỐN CƠ SỞ: {base_pts} ĐIỂM/CON)\n"
    res += f"======================================================================================\n"
    res += f"NGÀY NUÔI | HỆ SỐ | MỨC CƯỢC/CON | TỔNG VỐN NGÀY | LŨY KẾ VỐN | NỔ 1 NHÁY (THU VỀ) | LÃI RÒNG\n"
    res += f"======================================================================================\n"
    
    luy_ke_von = 0
    for i, he_so in enumerate(TY_LE_VAO_TIEN):
        pts_con = base_pts * he_so
        von_ngay = pts_con * 2 * COST_PER_POINT
        luy_ke_von += von_ngay
        thuong_1_nhay = pts_con * WIN_PER_NHAY
        lai = thuong_1_nhay - luy_ke_von
        
        res += f" Ngày {i+1}    |  x{he_so:<2} | {pts_con:>12} | {von_ngay:>13,.0f} | {luy_ke_von:>10,.0f} | {thuong_1_nhay:>18,.0f} | {lai:>+10,.0f}\n"
    
    res += f"======================================================================================\n"
    res += f"💡 NGUYÊN TẮC: Chạm mốc ngày nào nổ là DỪNG KHUNG. Nếu hết 5 ngày không nổ -> CHẤP NHẬN CẮT LỖ KHUNG.\n"
    return res

def ui_backtest_chu_ky(t1_raw, t2_raw, base_pts):
    db, _ = doc_database_tu_excel()
    dt1 = chuan_hoa_ngay(t1_raw)
    dt2 = chuan_hoa_ngay(t2_raw)
    if not dt1 or not dt2: return "🛑 Lỗi định dạng ngày."
    
    start_dt = min(dt1[0], dt2[0]); end_dt = max(dt1[0], dt2[0])
    base_pts = int(base_pts)
    
    khung_active = False
    current_pair = []
    day_in_khung = 0
    
    total_lai = 0
    khung_thang = 0
    khung_thua = 0
    
    rep = f"📈 BÁO CÁO BACKTEST KHUNG 5 NGÀY TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')}\n"
    rep += "="*110 + "\n"
    rep += f"{'NGÀY':<12} | {'TRẠNG THÁI':<15} | {'CẶP NUÔI':<10} | {'NGÀY THỨ':<8} | {'TIỀN ĐÁNH':<12} | {'KQ NHÁY':<8} | {'LÃI PHIÊN/KHUNG':<15} | {'LŨY KẾ':<12}\n"
    rep += "="*110 + "\n"
    
    curr = start_dt
    von_khung_hien_tai = 0
    
    while curr <= end_dt:
        ngay_str = curr.strftime("%d/%m/%Y")
        
        # Nếu chưa có khung, tìm cặp để vào
        if not khung_active:
            cap_moi = tim_cap_nuoi(curr, db)
            if cap_moi:
                khung_active = True
                current_pair = cap_moi
                day_in_khung = 1
                von_khung_hien_tai = 0
            else:
                rep += f"{ngay_str:<12} | {'🔭 QUAN SÁT':<15} | {'N/A':<10} | {'-':<8} | {0:<12} | {'-':<8} | {0:<15} | {total_lai:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
        # Tiến hành đánh khung hiện tại
        if ngay_str in db:
            pts_con = base_pts * TY_LE_VAO_TIEN[day_in_khung - 1]
            von_ngay = pts_con * 2 * COST_PER_POINT
            von_khung_hien_tai += von_ngay
            
            lo_to = db[ngay_str]['prizes_int']
            nhay = lo_to.count(current_pair[0]) + lo_to.count(current_pair[1])
            
            thuong = nhay * pts_con * WIN_PER_NHAY
            
            # Nếu NỔ -> Thắng khung -> Reset
            if nhay > 0:
                lai_khung = thuong - von_khung_hien_tai
                total_lai += lai_khung
                khung_thang += 1
                p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                rep += f"{ngay_str:<12} | {'🟢 NỔ (WIN)':<15} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {nhay:<8} | {lai_khung:>+15,.0f} | {total_lai:>+12,.0f}\n"
                khung_active = False # Reset săn khung mới
            else:
                # Không nổ
                if day_in_khung == 5:
                    # Gãy khung (Cắt lỗ)
                    lai_khung = -von_khung_hien_tai
                    total_lai += lai_khung
                    khung_thua += 1
                    p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                    rep += f"{ngay_str:<12} | {'🔴 GÃY (CẮT LỖ)':<15} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {0:<8} | {lai_khung:>+15,.0f} | {total_lai:>+12,.0f}\n"
                    khung_active = False # Chấp nhận đau thương, tìm khung khác
                else:
                    # Chờ ngày tiếp theo
                    p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                    rep += f"{ngay_str:<12} | {'⏳ NUÔI TIẾP':<15} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {0:<8} | {'...':<15} | {total_lai:>+12,.0f}\n"
                    day_in_khung += 1
                    
        curr += timedelta(days=1)
        
    rep += "="*110 + "\n"
    rep += f"📊 TỔNG KẾT: Hoàn thành {khung_thang + khung_thua} Khung | ✅ Khung Thắng: {khung_thang} | ❌ Khung Gãy: {khung_thua}\n"
    rep += f"💰 TỔNG LÃI RÒNG CHU KỲ: {total_lai:+,.0f} VNĐ\n"
    return rep

# ==============================================================================
# 🎨 GIAO DIỆN V30.0
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB V30.0 KHUNG") as demo:
    gr.Markdown("# 🚀 V30.0 — CHIẾN THUẬT NUÔI LÔ KHUNG 5 NGÀY (GẤP THẾP KIỂM SOÁT)")
    
    with gr.Tab("1. Đồng Bộ & Kế Hoạch Vốn"):
        btn1 = gr.Button("⚡ KIỂM TRA DỮ LIỆU EXCEL", variant="primary")
        out1 = gr.Textbox(lines=2)
        btn1.click(lambda: doc_database_tu_excel()[1], outputs=out1)
        
        gr.Markdown("### LẬP BẢNG PHÂN BỔ DÒNG TIỀN 5 NGÀY")
        pts_base = gr.Number(label="Mức cược cơ sở Ngày 1 (điểm/con)", value=10)
        btn_bang = gr.Button("📊 LẬP BẢNG GẤP THẾP", variant="secondary")
        out_bang = gr.Textbox(lines=10)
        btn_bang.click(ui_lap_bang_von, inputs=[pts_base], outputs=out_bang)
        
    with gr.Tab("2. Lệnh Theo Dõi Khung Chuẩn"):
        gr.Markdown("*(Tab này dành riêng cho Backtest Chu Kỳ vì đánh Khung phải theo dõi xuyên suốt nhiều ngày)*")
        with gr.Row():
            t1 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
            t2 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_4 = gr.Number(label="Mốc cược Ngày 1 (Điểm/con)", value=10)
        btn4 = gr.Button("📈 KIỂM ĐỊNH CHIẾN THUẬT KHUNG 5 NGÀY", variant="primary")
        out4 = gr.Textbox(lines=25)
        btn4.click(ui_backtest_chu_ky, inputs=[t1, t2, pts_4], outputs=out4)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=10000)
