import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V30.4 - KHUNG 3 NGÀY (DUAL ACCOUNTING MASTER)
# ==============================================================================
VERSION = "V30.4 KẾ TOÁN KÉP MINH BẠCH"
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

# KỶ LUẬT VỐN: GẤP THẾP 3 NGÀY (1, 2, 4)
TY_LE_VAO_TIEN = [1, 2, 4] 

def chuan_hoa_ngay(ngay_raw):
    if pd.isna(ngay_raw) or not str(ngay_raw).strip(): return None
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

def lay_max_days(thang, nam):
    if thang == 2: return 29 if (nam % 4 == 0 and (nam % 100 != 0 or nam % 400 == 0)) else 28
    elif thang in [4, 6, 9, 11]: return 30
    return 31

def doc_database_tu_excel():
    db = {}
    if not os.path.exists(DATA_FILE): 
        return db, f"🛑 CRITICAL ERROR: Hệ thống không tìm thấy file '{DATA_FILE}'."
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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY. DỮ LIỆU TOÀN VẸN."
    except Exception as e: return db, f"🛑 CRITICAL ERROR KHI ĐỌC FILE: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db: return datetime(2026, 7, 21), datetime(2026, 7, 22)
    max_dt = max(info['date_obj'] for info in db.values())
    return max_dt, max_dt + timedelta(days=1)

# ==============================================================================
# 🎯 LÕI THUẬT TOÁN: QUÉT KHUNG 3 NGÀY
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
                if day_in_khung == 3: khung_active = False # Khung 3 ngày
                else: day_in_khung += 1
        curr += timedelta(days=1)
        
    return khung_active, current_pair, day_in_khung

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN (KẾ TOÁN KÉP)
# ==============================================================================

def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    res = f"📡 HỆ THỐNG V30.4 (KẾ TOÁN KÉP MINH BẠCH):\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Tình trạng DB : {msg}\n"
    res += f"• Cập nhật cuối : 📅 [{latest_dt.strftime('%d/%m/%Y')}]\n"
    res += f"• Tính toán cho : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]\n"
    return res, f"#### CẤP LỆNH KỲ TIẾP THEO: {next_predict_dt.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
        base_pts = int(pts_per_code_base)
        
        active, pair, day_idx = truy_xuat_trang_thai_khung(db, next_predict_dt)
        if not active:
            pair = tim_cap_nuoi(next_predict_dt, db)
            if not pair:
                return f"🎯 LỆNH KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n=======================================================\n🛑 CẢNH BÁO: Dữ liệu chưa đủ độ chín. ĐỨNG NGOÀI."
            day_idx = 1
            status_msg = "🔥 XUẤT LỆNH: VÀO KHUNG MỚI (Ngày 1/3)"
        else:
            status_msg = f"⏳ ÉP KỶ LUẬT: NUÔI TIẾP NGÀY THỨ {day_idx}/3"
            
        pts_con = base_pts * TY_LE_VAO_TIEN[day_idx - 1]
        von_ngay = pts_con * 2 * COST_PER_POINT
        
        res = f"🎯 XUẤT LỆNH V30.4 CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"=======================================================\n"
        res += f"🎚️ TRẠNG THÁI : {status_msg}\n"
        res += f"=======================================================\n"
        res += f"📋 CHỈ ĐỊNH CẶP : [{pair[0]:02d} - {pair[1]:02d}]\n"
        res += f" • Hệ số Gấp thếp : x{TY_LE_VAO_TIEN[day_idx - 1]} (Vốn cơ sở: {base_pts}đ)\n"
        res += f" • Khối lượng Cược: {pts_con} điểm/con\n"
        res += f"-------------------------------------------------------\n"
        res += f"💰 TIỀN PHẢI XUẤT  : {von_ngay:,.0f} VND\n"
        for nhay in range(1, 3):
            rev = nhay * pts_con * 80000
            res += f" • Kịch bản nổ {nhay} nháy: Doanh thu {rev:,.0f} VND\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 2: {e}"

def web_phan_he_3_risk_audit(base_pts):
    try:
        base_pts = int(base_pts)
        res = f"📊 BẢNG AUDIT DÒNG TIỀN (KHUNG MAX 3 NGÀY)\n"
        res += f"======================================================================================\n"
        res += f"NGÀY | HỆ SỐ | MỨC CƯỢC/CON | TỔNG VỐN XUẤT | LŨY KẾ VỐN | DOANH THU 1 NHÁY | LÃI RÒNG\n"
        res += f"======================================================================================\n"
        
        luy_ke_von = 0
        for i, he_so in enumerate(TY_LE_VAO_TIEN):
            pts_con = base_pts * he_so
            von_ngay = pts_con * 2 * COST_PER_POINT
            luy_ke_von += von_ngay
            thuong_1_nhay = pts_con * WIN_PER_NHAY
            lai = thuong_1_nhay - luy_ke_von
            res += f" D+{i+1} |  x{he_so:<2} | {pts_con:>12} | {von_ngay:>13,.0f} | {luy_ke_von:>10,.0f} | {thuong_1_nhay:>16,.0f} | {lai:>+9,.0f}\n"
        
        res += f"======================================================================================\n"
        res += f"⚠️ LỆNH CỨNG: HẾT NGÀY 3 KHÔNG NỔ -> CẮT LỖ {luy_ke_von:,.0f} VNĐ VÀ LẬP TỨC ĐÓNG KHUNG.\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 3: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày (DD/MM/YYYY)."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Ngày {ngay_str} không tồn tại trong Excel."
            
        base_pts = int(pts_per_code_base)
        lo_to_27 = db[ngay_str]['prizes_int']
        
        active, pair, day_idx = truy_xuat_trang_thai_khung(db, d_obj)
        if not active:
            pair = tim_cap_nuoi(d_obj, db)
            if not pair: return f"📡 KIỂM TOÁN NGÀY {ngay_str}\n=======================================================\n🔭 LỊCH SỬ CHƯA ĐỦ ĐỘ CHÍN ĐỂ CẤP LỆNH. QUAN SÁT."
            day_idx = 1
            
        pts_con = base_pts * TY_LE_VAO_TIEN[day_idx - 1]
        von_ngay = pts_con * 2 * COST_PER_POINT
        nhay = lo_to_27.count(pair[0]) + lo_to_27.count(pair[1])
        thuong = nhay * pts_con * WIN_PER_NHAY
        lai = thuong - von_ngay
        
        status = "🟢 WIN (CHỐT LÃI KHUNG)" if nhay > 0 else ("🔴 LOSS (CẮT LỖ TOÀN TẬP)" if day_idx == 3 else "⏳ PENDING (GỒNG LỖ SANG NGÀY)")
        
        report = f"📡 BÁO CÁO KIỂM TOÁN NGÀY: {ngay_str}\n"
        report += f"=======================================================\n"
        report += f"📋 VỊ THẾ KHUNG : [{pair[0]:02d} - {pair[1]:02d}] (Ngày thứ {day_idx}/3)\n"
        report += f" • Điểm Cược/con: {pts_con} điểm\n"
        report += f" • Kết quả Nháy : x{nhay} nháy -> {status}\n"
        report += f"-------------------------------------------------------\n"
        report += f"💰 CHI PHÍ      : {von_ngay:,.0f} VND\n"
        report += f"📈 DOANH THU    : {thuong:,.0f} VND\n"
        report += f"💵 BIẾN ĐỘNG    : {lai:+,.0f} VND\n"
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
        
        cash_chi_phi = 0
        cash_doanh_thu = 0
        luy_ke_thang = 0
        
        report = f"📊 KIỂM TOÁN ĐỐI SOÁT THÁNG {thang:02d}/{nam} (ĐÃ MỞ CỘT LŨY KẾ THEO DÕI):\n"
        report += f"============================================================================================================================\n"
        report += f"{'NGÀY':<10} | {'TRẠNG THÁI':<18} | {'VỊ THẾ':<8} | {'NGÀY':<5} | {'CHI PHÍ HÔM NAY':<16} | {'KQ':<4} | {'LÃI CHỐT KHUNG':<15} | {'LŨY KẾ':<12}\n"
        report += f"============================================================================================================================\n"
        
        if khung_active:
            report += f"➡️ [SỐ DƯ ĐẦU KỲ]: Đang gồng Khung [{current_pair[0]:02d}-{current_pair[1]:02d}] từ tháng trước. Vốn ngâm: {von_khung_hien_tai:,.0f} đ\n"
            report += f"----------------------------------------------------------------------------------------------------------------------------\n"
            
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
                    report += f"{ngay_str:<10} | {'🔭 QUAN SÁT/NO DATA':<18} | {'-':<8} | {'-':<5} | {0:<16} | {'-':<4} | {0:<15} | {luy_ke_thang:>+12,.0f}\n"
                    curr += timedelta(days=1)
                    continue
                    
            if ngay_str in db:
                pts_con = base_pts * TY_LE_VAO_TIEN[day_in_khung - 1]
                von_ngay = pts_con * 2 * COST_PER_POINT
                von_khung_hien_tai += von_ngay
                cash_chi_phi += von_ngay
                
                lo_to = db[ngay_str]['prizes_int']
                nhay = lo_to.count(current_pair[0]) + lo_to.count(current_pair[1])
                thuong = nhay * pts_con * WIN_PER_NHAY
                cash_doanh_thu += thuong
                
                p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                
                if nhay > 0:
                    lai_khung = thuong - von_khung_hien_tai
                    luy_ke_thang += lai_khung
                    report += f"{ngay_str:<10} | {'🟢 WIN (CHỐT LÃI)':<18} | {p_str:<8} | {day_in_khung:<5} | {von_ngay:<16,.0f} | {nhay:<4} | {lai_khung:>+15,.0f} | {luy_ke_thang:>+12,.0f}\n"
                    khung_active = False
                else:
                    if day_in_khung == 3:
                        lai_khung = -von_khung_hien_tai
                        luy_ke_thang += lai_khung
                        report += f"{ngay_str:<10} | {'🔴 LOSS (CẮT LỖ)':<18} | {p_str:<8} | {day_in_khung:<5} | {von_ngay:<16,.0f} | {0:<4} | {lai_khung:>+15,.0f} | {luy_ke_thang:>+12,.0f}\n"
                        khung_active = False
                    else:
                        report += f"{ngay_str:<10} | {'⏳ PENDING (GỒNG)':<18} | {p_str:<8} | {day_in_khung:<5} | {von_ngay:<16,.0f} | {0:<4} | {'...':<15} | {luy_ke_thang:>+12,.0f}\n"
                        day_in_khung += 1
            curr += timedelta(days=1)
            
        report += f"============================================================================================================================\n"
        report += f"📝 ĐỐI SOÁT KẾ TOÁN KÉP (DUAL ACCOUNTING):\n"
        report += f"1. TỔNG LỢI NHUẬN RÒNG ĐÃ CHỐT SỔ (Realized PnL) : {luy_ke_thang:+,.0f} VND (Khớp với dòng Lũy kế cuối cùng)\n"
        report += f"2. DÒNG TIỀN XUẤT/NHẬP THỰC TẾ TRONG THÁNG    : Chi {cash_chi_phi:,.0f}đ | Thu {cash_doanh_thu:,.0f}đ -> Chênh lệch: {cash_doanh_thu - cash_chi_phi:+,.0f} VND\n"
        
        if khung_active:
            report += f"\n⚠️ TRẠNG THÁI CUỐI THÁNG: Đang gồng Khung [{current_pair[0]:02d}-{current_pair[1]:02d}] chưa chốt sổ. Khoản vốn {von_khung_hien_tai:,.0f}đ đang bị ngâm chờ kết quả vào tháng sau (Chưa tính vào Lãi/Lỗ tháng này).\n"
            
        return report
    except Exception as e: return f"🛑 LỖI TAB 5: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi định dạng ngày nhập liệu."
        start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
        base_pts = int(pts_per_code_base)
        
        khung_active, current_pair, day_in_khung = truy_xuat_trang_thai_khung(db, start_dt)
        von_khung_hien_tai = sum([base_pts * TY_LE_VAO_TIEN[i] * 2 * COST_PER_POINT for i in range(day_in_khung-1)]) if khung_active else 0
        
        cash_chi = 0
        cash_thu = 0
        
        rep = f"📈 BÁO CÁO KIỂM TOÁN CHU KỲ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')}\n"
        rep += "="*115 + "\n"
        rep += f"{'NGÀY':<10} | {'TRẠNG THÁI':<18} | {'VỊ THẾ':<8} | {'NGÀY VÀO':<8} | {'CHI PHÍ HÔM NAY':<16} | {'KQ':<4} | {'LÃI CHỐT KHUNG':<15} | {'LŨY KẾ':<12}\n"
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
                    rep += f"{ngay_str:<10} | {'🔭 NO DATA':<18} | {'-':<8} | {'-':<8} | {0:<16} | {'-':<4} | {0:<15} | {total_lai:>+12,.0f}\n"
                    curr += timedelta(days=1)
                    continue
                    
            if ngay_str in db:
                pts_con = base_pts * TY_LE_VAO_TIEN[day_in_khung - 1]
                von_ngay = pts_con * 2 * COST_PER_POINT
                von_khung_hien_tai += von_ngay
                cash_chi += von_ngay
                
                lo_to = db[ngay_str]['prizes_int']
                nhay = lo_to.count(current_pair[0]) + lo_to.count(current_pair[1])
                thuong = nhay * pts_con * WIN_PER_NHAY
                cash_thu += thuong
                p_str = f"{current_pair[0]:02d}-{current_pair[1]:02d}"
                
                if nhay > 0:
                    lai_khung = thuong - von_khung_hien_tai
                    total_lai += lai_khung
                    k_thang += 1
                    rep += f"{ngay_str:<10} | {'🟢 WIN (CHỐT LÃI)':<18} | {p_str:<8} | {day_in_khung:<8} | {von_ngay:<16,.0f} | {nhay:<4} | {lai_khung:>+15,.0f} | {total_lai:>+12,.0f}\n"
                    khung_active = False 
                else:
                    if day_in_khung == 3:
                        lai_khung = -von_khung_hien_tai
                        total_lai += lai_khung
                        k_thua += 1
                        rep += f"{ngay_str:<10} | {'🔴 LOSS (CẮT LỖ)':<18} | {p_str:<8} | {day_in_khung:<8} | {von_ngay:<16,.0f} | {0:<4} | {lai_khung:>+15,.0f} | {total_lai:>+12,.0f}\n"
                        khung_active = False 
                    else:
                        rep += f"{ngay_str:<10} | {'⏳ PENDING (GỒNG)':<18} | {p_str:<8} | {day_in_khung:<8} | {von_ngay:<16,.0f} | {0:<4} | {'...':<15} | {total_lai:>+12,.0f}\n"
                        day_in_khung += 1
            curr += timedelta(days=1)
            
        rep += "="*115 + "\n"
        rep += f"📊 HIỆU SUẤT KHUNG: Số Khung Hoàn Thành: {k_thang + k_thua} | Tỷ lệ Win: {k_thang} | Tỷ lệ Cắt Lỗ: {k_thua}\n"
        rep += f"1. TỔNG LỢI NHUẬN RÒNG ĐÃ CHỐT SỔ (Realized PnL): {total_lai:+,.0f} VNĐ\n"
        rep += f"2. DÒNG TIỀN XUẤT NHẬP (Cash Flow): Chi {cash_chi:,.0f}đ | Thu {cash_thu:,.0f}đ -> Chênh lệch: {cash_thu - cash_chi:+,.0f} VNĐ\n"
        if khung_active:
             rep += f"\n⚠️ LƯU Ý KẾ TOÁN: Chu kỳ kết thúc nhưng còn Khung [{current_pair[0]:02d}-{current_pair[1]:02d}] đang gồng. Khoản tiền {von_khung_hien_tai:,.0f}đ chưa được chốt sổ.\n"
             
        return rep
    except Exception as e: return f"🛑 LỖI TAB 6: {e}"

def web_phan_he_7_raw_db_lookup(ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        _, ngay_str = res
        if ngay_str not in db: return f"🛑 NO DATA: Ngày {ngay_str} chưa được ghi nhận trong Excel."
            
        lo_to_raw = db[ngay_str]['prizes_int']
        lo_to_sorted = sorted([f"{x:02d}" for x in lo_to_raw])
        report = f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY {ngay_str}:\n"
        report += "🎰 27 Giải ma trận phẳng:\n"
        for idx, lo in enumerate(lo_to_sorted): 
            report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
        return report
    except Exception as e: return f"🛑 LỖI TAB 7: {e}"

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO V30.4 (KHÓA SLIDER AN TOÀN)
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V30.4") as demo:
    gr.Markdown("# 🚀 XSMB QUANT V30.4 — KHUNG 3 NGÀY (KẾ TOÁN KÉP MINH BẠCH)")
    
    with gr.Tab("🔄 [1] Cập Nhật Dữ Liệu"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP & KIỂM TOÁN DB", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=5)
        
    with gr.Tab("🎯 [2] Lệnh Chốt Kế Tiếp"):
        title_2 = gr.Markdown(f"#### Lệnh cho kỳ quay tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ (Điểm/con cho Ngày 1)", value=10)
        btn_2 = gr.Button("🔍 KIẾT XUẤT LỆNH", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V30.4", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Bảng Vốn Khung 3 Ngày"):
        with gr.Row():
            pts_3 = gr.Number(label="Mốc cược cơ sở Ngày 1 (Điểm/con)", value=10)
        btn_3 = gr.Button("🧪 MÔ PHỎNG CHI PHÍ GẤP THẾP", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[pts_3], outputs=out_3)

    with gr.Tab("🔍 [4] Kiểm Toán Đơn Ngày"):
        with gr.Row():
            date_4 = gr.Textbox(label="Ngày Truy Xuất (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_4 = gr.Number(label="Mốc cược CƠ SỞ Ngày 1", value=10)
        btn_4 = gr.Button("📡 KIỂM TOÁN TỨC THỜI", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trạng Thái Khung", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Kiểm Toán Theo Tháng"):
        with gr.Row():
            # Khóa cứng Slider không cho phép sập app
            m_5 = gr.Slider(minimum=1, maximum=12, step=1, label="Chọn Tháng", value=latest_dt_init.month)
            y_5 = gr.Number(label="Năm", value=latest_dt_init.year)
            pts_5 = gr.Number(label="Mốc cược CƠ SỞ Ngày 1", value=10)
        btn_5 = gr.Button("📊 KIỂM TOÁN DÒNG TIỀN THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Audit", lines=20)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Kiểm Toán Tổng Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_6 = gr.Number(label="Mốc cược CƠ SỞ Ngày 1", value=10)
        btn_6 = gr.Button("📈 KIỂM TOÁN TOÀN BỘ CHU KỲ LỊCH SỬ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Tổng", lines=20)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Khớp Lệnh Lô Tô Gốc"):
        date_7 = gr.Textbox(label="Nhập ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRUY XUẤT RAW DATA EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Thô", lines=8)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
