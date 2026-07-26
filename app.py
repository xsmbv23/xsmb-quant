import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V30.2 - KHUNG 5 NGÀY (CROSS-VALIDATED MASTER)
# ==============================================================================
VERSION = "V30.2 CROSS-VALIDATED MASTER"
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

# Tỷ lệ vào tiền 5 ngày (Gấp thếp 1, 2, 4, 8, 16)
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

def lay_max_days(thang, nam=2026):
    if thang == 2: return 29 if (nam % 4 == 0 and (nam % 100 != 0 or nam % 400 == 0)) else 28
    elif thang in [4, 6, 9, 11]: return 30
    return 31

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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY DỮ LIỆU"
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db: return datetime(2026, 7, 21), datetime(2026, 7, 22)
    max_dt = max(info['date_obj'] for info in db.values())
    return max_dt, max_dt + timedelta(days=1)

# ==============================================================================
# 🎯 LÕI THUẬT TOÁN NUÔI KHUNG 5 NGÀY
# ==============================================================================
def tim_cap_nuoi(target_dt, db):
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(30):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db: hist_days.append(db[s_str]['prizes_int'])
        else: hist_days.append([]) 
        curr_t -= timedelta(days=1)

    if not hist_days[0]: return [] 

    pair_scores = {}
    for i in range(10, 100):
        if i % 10 == i // 10: continue 
        c1 = i; c2 = (i % 10)*10 + (i // 10)
        pair = tuple(sorted([c1, c2]))
        if pair in pair_scores: continue
        
        days_missed = 0
        for day_res in hist_days:
            if not day_res: continue
            if c1 in day_res or c2 in day_res: break
            days_missed += 1
            
        if 4 <= days_missed <= 6:
            freq_30 = sum(1 for day_res in hist_days if day_res and (c1 in day_res or c2 in day_res))
            if freq_30 >= 6: 
                pair_scores[pair] = freq_30

    if not pair_scores: return []
    sorted_pairs = sorted(pair_scores.items(), key=lambda k: k[1], reverse=True)
    return sorted_pairs[0][0]

def truy_xuat_trang_thai_khung(db, target_dt):
    all_dates = sorted([info['date_obj'] for info in db.values()])
    if not all_dates: return False, [], 0
    start_dt = all_dates[0]
    
    curr = start_dt
    khung_active = False
    current_pair = []
    day_in_khung = 0
    
    while curr < target_dt:
        ngay_str = curr.strftime("%d/%m/%Y")
        if not khung_active:
            cap = tim_cap_nuoi(curr, db)
            if cap:
                khung_active = True
                current_pair = cap
                day_in_khung = 1
        
        if khung_active and ngay_str in db:
            lo_to = db[ngay_str]['prizes_int']
            nhay = lo_to.count(current_pair[0]) + lo_to.count(current_pair[1])
            if nhay > 0:
                khung_active = False
            else:
                if day_in_khung == 5: khung_active = False # Khung 5 ngày
                else: day_in_khung += 1
        curr += timedelta(days=1)
        
    return khung_active, current_pair, day_in_khung

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN
# ==============================================================================

def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    res = f"📡 KẾT NỐI HỆ THỐNG V30.2 KHUNG 5 NGÀY (CROSS-VALIDATED):\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File Excel : {msg}\n"
    res += f"• Ngày chốt Excel gần nhất: 📅 [{latest_dt.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán MỚI  : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]\n"
    return res, f"#### Kỳ quay dự đoán tiếp theo: {next_predict_dt.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
        base_pts = int(pts_per_code_base)
        
        active, pair, day_idx = truy_xuat_trang_thai_khung(db, next_predict_dt)
        status_msg = ""
        if not active:
            pair = tim_cap_nuoi(next_predict_dt, db)
            if not pair:
                return f"🎯 BÁO CÁO KỲ TƯƠNG LAI: {next_predict_dt.strftime('%d/%m/%Y')}\n=================================================================================\n🛑 QUAN SÁT: Không có tín hiệu. HỆ THỐNG ĐỨNG NGOÀI."
            day_idx = 1
            status_msg = "🔥 BẮT ĐẦU VÀO KHUNG MỚI (Ngày 1/5)"
        else:
            status_msg = f"⏳ NUÔI TIẾP: NGÀY THỨ {day_idx}/5 CỦA KHUNG"
            
        pts_con = base_pts * TY_LE_VAO_TIEN[day_idx - 1]
        von_ngay = pts_con * 2 * COST_PER_POINT
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN V30.2 CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"=================================================================================\n"
        res += f"🎚️ TRẠNG THÁI KHUNG : {status_msg}\n"
        res += f"=================================================================================\n"
        res += f"📋 CẶP NUÔI ĐỘC BẢN: [{pair[0]:02d} - {pair[1]:02d}]\n"
        res += f" • Lệnh đi tiền: Ngày {day_idx} (Hệ số x{TY_LE_VAO_TIEN[day_idx - 1]})\n"
        res += f" • Mức cược   : {pts_con} điểm/con\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"💰 TỔNG TIỀN ĐÁNH HÔM NAY : {von_ngay:,.0f} VND\n"
        for nhay in range(1, 4):
            rev = nhay * pts_con * 80000
            res += f" • Nổ {nhay} nháy: Thu về {rev:,.0f}đ\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 2: {e}"

def web_phan_he_3_risk_audit(base_pts):
    try:
        base_pts = int(base_pts)
        res = f"📊 BẢNG KẾ HOẠCH DÒNG TIỀN NUÔI 5 NGÀY (VỐN CƠ SỞ: {base_pts} ĐIỂM/CON)\n"
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
        res += f"💡 NGUYÊN TẮC: Chạm mốc ngày nào nổ là DỪNG KHUNG. Hết 5 ngày không nổ -> CẮT LỖ KHUNG.\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 3: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} CHƯA CÓ TRONG FILE EXCEL!"
            
        base_pts = int(pts_per_code_base)
        lo_to_27 = db[ngay_str]['prizes_int']
        
        active, pair, day_idx = truy_xuat_trang_thai_khung(db, d_obj)
        if not active:
            pair = tim_cap_nuoi(d_obj, db)
            if not pair: return f"📡 BACKTEST NGÀY: {ngay_str}\n=================================================================================\n🛑 QUAN SÁT: Không có tín hiệu."
            day_idx = 1
            
        pts_con = base_pts * TY_LE_VAO_TIEN[day_idx - 1]
        von_ngay = pts_con * 2 * COST_PER_POINT
        nhay = lo_to_27.count(pair[0]) + lo_to_27.count(pair[1])
        thuong = nhay * pts_con * WIN_PER_NHAY
        lai = thuong - von_ngay
        
        status = "🟢 NỔ (WIN & CHỐT KHUNG)" if nhay > 0 else ("🔴 GÃY (CẮT LỖ KHUNG)" if day_idx == 5 else "⏳ TRƯỢT (NUÔI TIẾP)")
        
        report = f"📡 TRÍCH XUẤT BACKTEST KỲ NGÀY EXCEL: {ngay_str}\n"
        report += f"=================================================================================\n"
        report += f"📋 CẶP ĐÁNH: [{pair[0]:02d} - {pair[1]:02d}] (Ngày thứ {day_idx}/5)\n"
        report += f" • Mức cược: {pts_con} điểm/con\n"
        report += f" • Kết quả : Về {nhay} nháy -> {status}\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💰 TIỀN ĐÁNH : {von_ngay:,.0f} VND\n"
        report += f"📈 DOANH THU : {thuong:,.0f} VND\n"
        report += f"💵 LÃI PHIÊN : {lai:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 4: {e}"

def web_phan_he_5_monthly_audit(month, year, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        base_pts = int(pts_per_code_base)
        max_days = lay_max_days(thang, nam)
        
        start_dt = datetime(nam, thang, 1)
        end_dt = datetime(nam, thang, max_days)
        
        khung_active, current_pair, day_in_khung = truy_xuat_trang_thai_khung(db, start_dt)
        von_khung_hien_tai = sum([base_pts * TY_LE_VAO_TIEN[i] * 2 * COST_PER_POINT for i in range(day_in_khung-1)]) if khung_active else 0
        
        report = f"📊 BÁO CÁO LŨY KẾ THÁNG {thang:02d}/{nam} (NUÔI 5 NGÀY):\n"
        report += f"=================================================================================================================\n"
        report += f"{'NGÀY':<10} | {'TRẠNG THÁI':<16} | {'CẶP NUÔI':<10} | {'NGÀY THỨ':<8} | {'TIỀN ĐÁNH':<12} | {'KQ':<5} | {'LÃI PHIÊN/KHUNG':<15}\n"
        report += f"=================================================================================================================\n"
        
        luy_ke_thang = 0
        curr = start_dt
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            if not khung_active:
                cap = tim_cap_nuoi(curr, db)
                if cap:
                    khung_active = True
                    current_pair = cap
                    day_in_khung = 1
                    von_khung_hien_tai = 0
                else:
                    report += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<16} | {'-':<10} | {'-':<8} | {0:<12} | {'-':<5} | {0:<15}\n"
                    curr += timedelta(days=1)
                    continue
                    
            if ngay_str in db:
                pts_con = base_pts * TY_LE_VAO_TIEN[day_in_khung - 1]
                von_ngay = pts_con * 2 * COST_PER_POINT
                von_khung_hien_tai += von_ngay
                
                lo_to = db[ngay_str]['prizes_int']
                nhay = lo_to.count(current_pair[0]) + lo_to.count(current_pair[1])
                thuong = nhay * pts_con * WIN_PER_NHAY
                p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                
                if nhay > 0:
                    lai_khung = thuong - von_khung_hien_tai
                    luy_ke_thang += lai_khung
                    report += f"{ngay_str:<10} | {'🟢 NỔ (WIN)':<16} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {nhay:<5} | {lai_khung:>+15,.0f}\n"
                    khung_active = False
                else:
                    if day_in_khung == 5:
                        lai_khung = -von_khung_hien_tai
                        luy_ke_thang += lai_khung
                        report += f"{ngay_str:<10} | {'🔴 GÃY (CẮT LỖ)':<16} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {0:<5} | {lai_khung:>+15,.0f}\n"
                        khung_active = False
                    else:
                        report += f"{ngay_str:<10} | {'⏳ NUÔI TIẾP':<16} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {0:<5} | {'...':<15}\n"
                        day_in_khung += 1
            curr += timedelta(days=1)
            
        report += f"=================================================================================================================\n"
        report += f"💰 TỔNG LÃI RÒNG CHỐT TRONG THÁNG (Bao gồm vốn bảo lưu): {luy_ke_thang:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 5: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi ngày."
        start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
        base_pts = int(pts_per_code_base)
        
        khung_active, current_pair, day_in_khung = truy_xuat_trang_thai_khung(db, start_dt)
        von_khung_hien_tai = sum([base_pts * TY_LE_VAO_TIEN[i] * 2 * COST_PER_POINT for i in range(day_in_khung-1)]) if khung_active else 0
        
        rep = f"📈 BÁO CÁO CHU KỲ (KHUNG 5 NGÀY) TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')}\n"
        rep += "="*115 + "\n"
        rep += f"{'NGÀY':<10} | {'TRẠNG THÁI':<16} | {'CẶP NUÔI':<10} | {'NGÀY THỨ':<8} | {'TIỀN ĐÁNH':<12} | {'KQ':<5} | {'LÃI PHIÊN/KHUNG':<15} | {'LŨY KẾ':<12}\n"
        rep += "="*115 + "\n"
        
        curr = start_dt
        total_lai = 0
        k_thang = 0; k_thua = 0
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            if not khung_active:
                cap = tim_cap_nuoi(curr, db)
                if cap:
                    khung_active = True
                    current_pair = cap
                    day_in_khung = 1
                    von_khung_hien_tai = 0
                else:
                    rep += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<16} | {'-':<10} | {'-':<8} | {0:<12} | {'-':<5} | {0:<15} | {total_lai:>+12,.0f}\n"
                    curr += timedelta(days=1)
                    continue
                    
            if ngay_str in db:
                pts_con = base_pts * TY_LE_VAO_TIEN[day_in_khung - 1]
                von_ngay = pts_con * 2 * COST_PER_POINT
                von_khung_hien_tai += von_ngay
                
                lo_to = db[ngay_str]['prizes_int']
                nhay = lo_to.count(current_pair[0]) + lo_to.count(current_pair[1])
                thuong = nhay * pts_con * WIN_PER_NHAY
                p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                
                if nhay > 0:
                    lai_khung = thuong - von_khung_hien_tai
                    total_lai += lai_khung
                    k_thang += 1
                    rep += f"{ngay_str:<10} | {'🟢 NỔ (WIN)':<16} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {nhay:<5} | {lai_khung:>+15,.0f} | {total_lai:>+12,.0f}\n"
                    khung_active = False 
                else:
                    if day_in_khung == 5:
                        lai_khung = -von_khung_hien_tai
                        total_lai += lai_khung
                        k_thua += 1
                        rep += f"{ngay_str:<10} | {'🔴 GÃY (CẮT LỖ)':<16} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {0:<5} | {lai_khung:>+15,.0f} | {total_lai:>+12,.0f}\n"
                        khung_active = False 
                    else:
                        rep += f"{ngay_str:<10} | {'⏳ NUÔI TIẾP':<16} | {p_str:<10} | {day_in_khung:<8} | {von_ngay:<12,.0f} | {0:<5} | {'...':<15} | {total_lai:>+12,.0f}\n"
                        day_in_khung += 1
            curr += timedelta(days=1)
            
        rep += "="*115 + "\n"
        rep += f"📊 TỔNG KẾT CHU KỲ: Hoàn thành {k_thang + k_thua} Khung | ✅ Khung Thắng: {k_thang} | ❌ Khung Gãy: {k_thua}\n"
        rep += f"💰 TỔNG LÃI RÒNG TOÀN CHU KỲ: {total_lai:+,.0f} VNĐ\n"
        return rep
    except Exception as e: return f"🛑 LỖI TAB 6: {e}"

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
# 🎨 GIAO DIỆN GRADIO V30.2
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V30.2") as demo:
    gr.Markdown("# 🚀 XSMB QUANT V30.2 — KHUNG 5 NGÀY (CROSS-VALIDATED MASTER)")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP DỮ LIỆU", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=5)
        
    with gr.Tab("🎯 [2] Dự Đoán Lệnh Khung"):
        title_2 = gr.Markdown(f"#### Lệnh cho kỳ quay tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ (Điểm/con cho Ngày 1)", value=10)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT LỆNH HÔM NAY", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V30.2", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Bảng Vốn Khung 5 Ngày"):
        with gr.Row():
            pts_3 = gr.Number(label="Mốc cược cơ sở Ngày 1 (Điểm/con)", value=10)
        btn_3 = gr.Button("🧪 LẬP BẢNG VÀO TIỀN GẤP THẾP", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn Từng Ngày", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[pts_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Ngày"):
        with gr.Row():
            date_4 = gr.Textbox(label="Ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_4 = gr.Number(label="Mốc cược CƠ SỞ Ngày 1", value=10)
        btn_4 = gr.Button("📡 KIỂM TRA LẠI NGÀY NÀY", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            # [FIX LỖI UI]: KHÓA CỨNG BẰNG SLIDER TỪ 1 ĐẾN 12, NGĂN NHẬP SAI THÁNG SẬP APP
            m_5 = gr.Slider(minimum=1, maximum=12, step=1, label="Tháng", value=latest_dt_init.month)
            y_5 = gr.Number(label="Năm", value=latest_dt_init.year)
            pts_5 = gr.Number(label="Mốc cược CƠ SỞ Ngày 1", value=10)
        btn_5 = gr.Button("📊 BÓC TÁCH DÒNG TIỀN THEO THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Bảng Nhật ký", lines=18)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Quét Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày", value="01/01/2026")
            t2_6 = gr.Textbox(label="Đến ngày", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_6 = gr.Number(label="Mốc cược CƠ SỞ Ngày 1", value=10)
        btn_6 = gr.Button("📈 QUÉT TỔNG THỂ DÒNG TIỀN NUÔI KHUNG 5 NGÀY", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Dòng tiền", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả", lines=8)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
