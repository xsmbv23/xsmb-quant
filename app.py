import os
import sys
import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V33.7 - T-7 TINH GỌN (BẢN DEEP TEST & UI ĐỒNG BỘ 100%)
# ==============================================================================
VERSION = "V33.7 (DEEP TESTED - 7 TAB ĐỒNG BỘ)"
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

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
        return db, f"🛑 LỖI HỆ THỐNG: Không tìm thấy file '{DATA_FILE}'."
    try:
        df = pd.read_excel(DATA_FILE, dtype=str)
        # [ĐÃ FIX DEEP-TEST]: Chặn lỗi nếu file Excel bị mất cột
        if df.shape[1] < 2:
            return db, "🛑 LỖI CẤU TRÚC FILE: File Excel phải có ít nhất 2 cột (Ngày và Lô Tô)."
            
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
        return db, f"🟢 NẠP THÀNH CÔNG {len(db)} NGÀY HỢP LỆ."
    except Exception as e: return db, f"🛑 LỖI ĐỌC FILE: {e}"

def lay_ngay_chot_tu_excel(db):
    if not db: return datetime(2026, 7, 21), datetime(2026, 7, 21), datetime(2026, 7, 22)
    all_dates = [info['date_obj'] for info in db.values()]
    min_dt = min(all_dates)
    max_dt = max(all_dates)
    return min_dt, max_dt, max_dt + timedelta(days=1)

def tim_dan_t7(target_dt, db):
    t_minus_7 = target_dt - timedelta(days=7)
    ngay_str_t7 = t_minus_7.strftime("%d/%m/%Y")
    
    if ngay_str_t7 not in db: 
        return []

    loto_27_tuantruoc = db[ngay_str_t7]['prizes_int']
    return sorted(list(set(loto_27_tuantruoc)))

# ==============================================================================
# 🖥️ PHÂN HỆ GIAO DIỆN (ĐỒNG BỘ 100% HIỂN THỊ TÊN TAB)
# ==============================================================================

def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    _, latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    res = f"📑 [TAB 1] BÁO CÁO: CẬP NHẬT DB\n"
    res += f"=================================================================================\n"
    res += f"• Phiên bản    : {VERSION}\n"
    res += f"• Tình trạng DB: {msg}\n"
    res += f"• Cập nhật cuối: 📅 [{latest_dt.strftime('%d/%m/%Y')}]\n"
    res += f"• Lịch tính toán: 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]\n"
    return res, f"#### CẤP LỆNH KỲ TIẾP THEO: {next_predict_dt.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        _, latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
        base_pts = int(pts_per_code_base)
        if base_pts <= 0: return "🛑 LỖI KẾ TOÁN: Mức cược phải lớn hơn 0 điểm."
        
        dan = tim_dan_t7(next_predict_dt, db)
        
        res = f"📑 [TAB 2] BÁO CÁO: LỆNH CHỐT KẾ TIẾP\n"
        res += f"=======================================================\n"
        
        if not dan:
            ngay_t7 = (next_predict_dt - timedelta(days=7)).strftime('%d/%m/%Y')
            res += f"🎯 LỆNH KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
            res += f"🛑 CẢNH BÁO: Dữ liệu T-7 ({ngay_t7}) bị khuyết. HỆ THỐNG KHÓA LỆNH ĐỂ BẢO TOÀN VỐN.\n"
            return res
            
        so_luong_lo = len(dan)
        von_ngay = so_luong_lo * base_pts * COST_PER_POINT
        dan_str = " ".join([f"{x:02d}" for x in dan])
        
        doanh_thu_1_nhay = base_pts * WIN_PER_NHAY
        diem_hoa_von_nhay = math.ceil(von_ngay / doanh_thu_1_nhay)
        
        res += f"🎯 XUẤT LỆNH CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"📋 DÀN T-7 ({so_luong_lo} SỐ ĐỘC BẢN TỪ TUẦN TRƯỚC):\n"
        res += f" [ {dan_str} ]\n"
        res += f"-------------------------------------------------------\n"
        res += f" • Khối lượng Cược: {base_pts} điểm / 1 con lô\n"
        res += f"💰 TỔNG TIỀN PHẢI XUẤT: {von_ngay:,.0f} VND\n"
        res += f"💡 KỊCH BẢN LÃI RÒNG: Cần trúng ÍT NHẤT {diem_hoa_von_nhay} Nháy.\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 2: {e}"

def web_phan_he_3_risk_audit(base_pts, sim_size):
    try:
        base_pts = int(base_pts)
        so_luong_lo = int(sim_size)
        if base_pts <= 0 or so_luong_lo <= 0: return "🛑 LỖI KẾ TOÁN: Nhập số liệu lớn hơn 0."
        
        von_ngay = so_luong_lo * base_pts * COST_PER_POINT
        
        res = f"📑 [TAB 3] BÁO CÁO: BẢNG VỐN KHUNG NHÁY\n"
        res += f"====================================================================\n"
        res += f"📊 KỊCH BẢN ĐÁNH DÀN {so_luong_lo} SỐ - TỔNG CHI PHÍ: {von_ngay:,.0f} VNĐ\n"
        res += f"--------------------------------------------------------------------\n"
        res += f" KẾT QUẢ NHÁY | DOANH THU THU VỀ | LÃI / LỖ RÒNG | TRẠNG THÁI\n"
        res += f"--------------------------------------------------------------------\n"
        for nhay in range(0, int(so_luong_lo * 0.7) + 2):
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_ngay
            status = "🟢 LÃI RÒNG" if lai > 0 else "🔴 LỖ"
            if nhay == 0: status += " (MẤT TRẮNG)"
            
            lai_str = f"{lai:+,.0f}" if lai != 0 else "0"
            res += f" Về {nhay:>2} nháy  | {thuong:>16,.0f} | {lai_str:>13} | {status}\n"
        res += f"====================================================================\n"
        return res
    except Exception as e: return f"🛑 LỖI TAB 3: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 DỮ LIỆU RỖNG: Ngày {ngay_str} không có trong Excel."
            
        base_pts = int(pts_per_code_base)
        # [ĐÃ FIX DEEP-TEST]: Chặn người dùng gõ cược 0đ làm sai lệch kết quả Win/Loss
        if base_pts <= 0: return "🛑 LỖI KẾ TOÁN: Mức cược phải lớn hơn 0."
        
        lo_to_27_today = db[ngay_str]['prizes_int']
        
        t_minus_7 = d_obj - timedelta(days=7)
        t_minus_1 = d_obj - timedelta(days=1)
        ngay_str_t7 = t_minus_7.strftime("%d/%m/%Y")
        ngay_str_t1 = t_minus_1.strftime("%d/%m/%Y")
        
        report = f"📑 [TAB 4] BÁO CÁO: KIỂM TOÁN 1 NGÀY (SOI RÁC)\n"
        report += f"========================================================================\n\n"
        
        if ngay_str_t7 not in db:
            report += f"🔭 LỖI: Ngày T-7 ({ngay_str_t7}) bị khuyết dữ liệu. Không thể phân lập chu kỳ!\n"
            return report

        dan_t7 = set(db[ngay_str_t7]['prizes_int'])
        
        def cal_pnl(danh_sach):
            sl = len(danh_sach)
            if sl == 0: return 0, 0, 0, 0, 0, "⚫ TRỐNG LỆNH"
            chi_phi = sl * base_pts * COST_PER_POINT
            nhay = sum(lo_to_27_today.count(x) for x in danh_sach)
            doanh_thu = nhay * base_pts * WIN_PER_NHAY
            lai = doanh_thu - chi_phi
            status = "🟢 WIN" if lai > 0 else "🔴 LOSS"
            return sl, chi_phi, nhay, doanh_thu, lai, status

        list_full = sorted(list(dan_t7))
        sl_f, chi_f, nhay_f, thu_f, lai_f, st_f = cal_pnl(list_full)

        report += f"📡 KẾT QUẢ THỰC TẾ NGÀY: {ngay_str} (MỨC CƯỢC: {base_pts}đ/con)\n\n"
        report += f"🛑 [KỊCH BẢN 1] - ĐÁNH TOÀN BỘ T-7 (Bao gồm Tinh hoa + Rác)\n"
        report += f" • Dàn {sl_f} số: " + " ".join([f"{x:02d}" for x in list_full]) + "\n"
        report += f" • Nổ {nhay_f} nháy.  Vốn chi: {chi_f:,.0f}đ  | Thu về: {thu_f:,.0f}đ\n"
        report += f" 👉 LÃI/LỖ RÒNG: {lai_f:+,.0f} VNĐ ({st_f})\n\n"

        if ngay_str_t1 not in db:
            report += f"⚠️ LƯU Ý: Ngày T-1 ({ngay_str_t1}) khuyết dữ liệu.\nKhông thể bóc tách Kịch bản 2 (Rác) và Kịch bản 3 (Tinh Hoa).\n"
            return report

        kq_t1 = set(db[ngay_str_t1]['prizes_int'])
        tinh_hoa = set()
        for x in dan_t7:
            lon = (x % 10) * 10 + (x // 10) # Chuẩn hóa thuật ngữ: Số Lộn
            if x in kq_t1 or lon in kq_t1:
                tinh_hoa.add(x)
        rac = dan_t7 - tinh_hoa

        list_rac = sorted(list(rac))
        list_tinh_hoa = sorted(list(tinh_hoa))
        
        sl_r, chi_r, nhay_r, thu_r, lai_r, st_r = cal_pnl(list_rac)
        sl_t, chi_t, nhay_t, thu_t, lai_t, st_t = cal_pnl(list_tinh_hoa)
        
        report += f"🗑️ [KỊCH BẢN 2] - BÓC TÁCH: CHỈ ĐÁNH SỐ 'RÁC' (Không Rơi/Không Lộn từ T-1)\n"
        if sl_r == 0:
            report += f" 👉 KẾT QUẢ: KHÔNG CÓ RÁC TRONG DÀN T-7 (Sạch 100% Tinh Hoa)\n\n"
        else:
            report += f" • Dàn {sl_r} số: " + " ".join([f"{x:02d}" for x in list_rac]) + "\n"
            report += f" • Nổ {nhay_r} nháy.  Vốn chi: {chi_r:,.0f}đ  | Thu về: {thu_r:,.0f}đ\n"
            report += f" 👉 KẾT QUẢ DÒNG TIỀN NUÔI RÁC: {lai_r:+,.0f} VNĐ ({st_r})\n\n"
        
        report += f"💎 [KỊCH BẢN 3] - BÓC TÁCH: CHỈ ĐÁNH 'TINH HOA' (Có Rơi/Lộn từ T-1)\n"
        if sl_t == 0:
            report += f" 👉 KẾT QUẢ: KHÔNG CÓ TINH HOA (Toàn bộ là Rác)\n\n"
        else:
            report += f" • Dàn {sl_t} số: " + " ".join([f"{x:02d}" for x in list_tinh_hoa]) + "\n"
            report += f" • Nổ {nhay_t} nháy.  Vốn chi: {chi_t:,.0f}đ  | Thu về: {thu_t:,.0f}đ\n"
            report += f" 👉 LÃI/LỖ RÒNG: {lai_t:+,.0f} VNĐ ({st_t})\n\n"
        
        report += f"========================================================================\n"
        report += f"💡 KẾT LUẬN KIỂM TOÁN TẠI NGÀY NÀY:\n"
        if sl_r == 0: 
            report += f" -> Thật tuyệt vời! Dàn T-7 hôm nay sạch bóng Rác, 100% đều là Tinh Hoa có nhịp rơi.\n"
        elif lai_r < 0: 
            report += f" -> Sếp đã bị RÁC hút máu mất {-lai_r:,.0f}đ. Kịch bản đánh TINH HOA là quyết định cứu rỗi vốn!\n"
        elif lai_r > 0: 
            report += f" -> Cảnh báo! Rác bùng nổ mang lại lãi {lai_r:,.0f}đ. Lồng cầu đang quay cực kỳ hỗn loạn.\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 4: {e}"

def web_phan_he_5_monthly_audit(month, year, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        base_pts = int(pts_per_code_base)
        if base_pts <= 0: return "🛑 LỖI KẾ TOÁN: Mức cược phải lớn hơn 0."
        
        min_dt, max_dt, _ = lay_ngay_chot_tu_excel(db)
        
        start_dt = datetime(nam, thang, 1)
        end_dt = datetime(nam, thang, lay_max_days(thang, nam))
        
        if start_dt < min_dt: start_dt = min_dt
        if end_dt > max_dt: end_dt = max_dt
        if start_dt > end_dt: return f"🛑 BÁO CÁO: Tháng {thang:02d}/{nam} hoàn toàn chưa có dữ liệu."
        
        report = f"📑 [TAB 5] BÁO CÁO: KIỂM TOÁN THEO THÁNG\n"
        report += f"===================================================================================================================\n"
        report += f"📊 THÁNG {thang:02d}/{nam} - CHIẾN THUẬT ĐÁNH TOÀN BỘ DÀN T-7:\n"
        report += f"-------------------------------------------------------------------------------------------------------------------\n"
        report += f"{'NGÀY':<10} | {'TRẠNG THÁI':<15} | {'SỐ LÔ':<6} | {'CHI PHÍ':<12} | {'NHÁY':<5} | {'DOANH THU':<12} | {'LÃI / LỖ':<15} | {'LŨY KẾ':<12}\n"
        report += f"-------------------------------------------------------------------------------------------------------------------\n"
        
        luy_ke_thang = 0; cash_thu = 0; cash_chi = 0; total_phien_danh = 0
        curr = start_dt
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            if ngay_str not in db:
                report += f"{ngay_str:<10} | {'⚠️ MISSING DATA':<15} | {'-':<6} | {'-':<12} | {'-':<5} | {'-':<12} | {'-':<15} | {luy_ke_thang:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
            dan = tim_dan_t7(curr, db)
            if not dan:
                report += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<15} | {'0':<6} | {'-':<12} | {'-':<5} | {'-':<12} | {'[KHUYẾT T-7]':<15} | {luy_ke_thang:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
            total_phien_danh += 1
            so_luong_lo = len(dan)
            von_1_phien = so_luong_lo * base_pts * COST_PER_POINT
            
            lo_to_27 = db[ngay_str]['prizes_int']
            nhay = sum(lo_to_27.count(x) for x in dan)
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_1_phien
            
            luy_ke_thang += lai
            cash_chi += von_1_phien
            cash_thu += thuong
            
            status_str = "🟢 WIN" if lai > 0 else "🔴 LOSS"
            report += f"{ngay_str:<10} | {status_str:<15} | {so_luong_lo:<6} | {von_1_phien:<12,.0f} | {nhay:<5} | {thuong:<12,.0f} | {lai:>+15,.0f} | {luy_ke_thang:>+12,.0f}\n"
            curr += timedelta(days=1)
            
        roi = (luy_ke_thang / cash_chi * 100) if cash_chi > 0 else 0
        report += f"===================================================================================================================\n"
        report += f"📝 ĐỐI SOÁT KẾ TOÁN: {total_phien_danh} NGÀY ĐÁNH\n"
        report += f"• TỔNG DÒNG TIỀN (CASH FLOW): Chi {cash_chi:,.0f} đ | Thu {cash_thu:,.0f} đ\n"
        report += f"• LỢI NHUẬN RÒNG & ROI      : {luy_ke_thang:+,.0f} VND ({roi:+.2f} %)\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 5: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, pts_per_code_base):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi định dạng ngày."
        start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
        
        base_pts = int(pts_per_code_base)
        if base_pts <= 0: return "🛑 LỖI KẾ TOÁN: Mức cược phải lớn hơn 0."
        
        min_dt, max_dt, _ = lay_ngay_chot_tu_excel(db)
        if start_dt < min_dt: start_dt = min_dt
        if end_dt > max_dt: end_dt = max_dt
        if start_dt > end_dt: return "🛑 LỖI: Khoảng thời gian tra cứu hoàn toàn nằm ngoài Database."
        
        report = f"📑 [TAB 6] BÁO CÁO: QUÉT TOÀN CHU KỲ\n"
        report += f"===================================================================================================================\n"
        report += f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN {end_dt.strftime('%d/%m/%Y')} (ĐÁNH TOÀN BỘ T-7)\n"
        report += f"-------------------------------------------------------------------------------------------------------------------\n"
        report += f"{'NGÀY':<10} | {'TRẠNG THÁI':<15} | {'SỐ LÔ':<6} | {'CHI PHÍ HÔM NAY':<16} | {'NHÁY':<5} | {'LÃI / LỖ PHIÊN':<15} | {'LŨY KẾ':<12}\n"
        report += f"-------------------------------------------------------------------------------------------------------------------\n"
        
        curr = start_dt
        total_lai = 0; trades = 0; k_thang = 0; k_thua = 0
        cash_thu = 0; cash_chi = 0  
        
        while curr <= end_dt:
            ngay_str = curr.strftime("%d/%m/%Y")
            if ngay_str not in db:
                report += f"{ngay_str:<10} | {'⚠️ MISSING DATA':<15} | {'-':<6} | {'-':<16} | {'-':<5} | {'-':<15} | {total_lai:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                
            dan = tim_dan_t7(curr, db)
            if not dan:
                report += f"{ngay_str:<10} | {'🔭 QUAN SÁT':<15} | {'0':<6} | {'-':<16} | {'-':<5} | {'[KHUYẾT T-7]':<15} | {total_lai:>+12,.0f}\n"
                curr += timedelta(days=1)
                continue
                    
            trades += 1
            so_luong_lo = len(dan)
            von_1_phien = so_luong_lo * base_pts * COST_PER_POINT
            
            lo_to_27 = db[ngay_str]['prizes_int']
            nhay = sum(lo_to_27.count(x) for x in dan)
            thuong = nhay * base_pts * WIN_PER_NHAY
            lai = thuong - von_1_phien
            
            total_lai += lai
            cash_chi += von_1_phien
            cash_thu += thuong
            
            if lai > 0: 
                k_thang += 1; status_str = "🟢 WIN"
            else: 
                k_thua += 1; status_str = "🔴 LOSS"
                
            report += f"{ngay_str:<10} | {status_str:<15} | {so_luong_lo:<6} | {von_1_phien:<16,.0f} | {nhay:<5} | {lai:>+15,.0f} | {total_lai:>+12,.0f}\n"
            curr += timedelta(days=1)
            
        roi = (total_lai / cash_chi * 100) if cash_chi > 0 else 0
        report += f"===================================================================================================================\n"
        report += f"📊 HIỆU SUẤT T-7: {trades} Phiên | Win: {k_thang} | Loss: {k_thua}\n"
        report += f"📝 DÒNG TIỀN     : Chi {cash_chi:,.0f} đ | Thu {cash_thu:,.0f} đ\n"
        report += f"💰 LỢI NHUẬN RÒNG: {total_lai:+,.0f} VNĐ (ROI: {roi:+.2f} %)\n"
        return report
    except Exception as e: return f"🛑 LỖI TAB 6: {e}"

def web_phan_he_7_raw_db_lookup(ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 Lỗi định dạng ngày."
        _, ngay_str = res
        if ngay_str not in db: return f"🛑 NO DATA: Ngày {ngay_str} chưa có trong Excel."
            
        lo_to_raw = db[ngay_str]['prizes_int']
        lo_to_sorted = sorted([f"{x:02d}" for x in lo_to_raw])
        
        report = f"📑 [TAB 7] BÁO CÁO: TRUY XUẤT RAW DB (DỮ LIỆU GỐC)\n"
        report += f"=======================================================\n"
        report += f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY: {ngay_str}\n"
        report += f"🎰 27 Giải ma trận phẳng:\n"
        for idx, lo in enumerate(lo_to_sorted): 
            report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
        return report
    except Exception as e: return f"🛑 LỖI TAB 7: {e}"

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO V33.7 (CHÍNH XÁC 7 TAB THEO CHỈ ĐẠO CỦA SẾP)
# ==============================================================================
db_init, _ = doc_database_tu_excel()
_, latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V33.7") as demo:
    gr.Markdown("# 🚀 XSMB QUANT V33.7 — CHUẨN MỰC T-7 TINH GỌN (DEEP TESTED)")
    gr.Markdown("*(7 Tab Tinh Gọn. Báo cáo in rành mạch Header tương ứng. Lọc Rác được soi chiếu ngay tại Tab 4)*")
    
    with gr.Tab("🔄 [1] CẬP NHẬT DB"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP & KIỂM TOÁN DB", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=7)
        
    with gr.Tab("🎯 [2] LỆNH CHỐT KẾ TIẾP"):
        title_2 = gr.Markdown(f"#### Lệnh cho kỳ quay tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ (Điểm/1 con lô)", value=10)
        btn_2 = gr.Button("🔍 KIẾT XUẤT LỆNH DÀN T-7", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V33.7", lines=15)
        btn_2.click(web_phan_he_2_predict, inputs=[pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] BẢNG VỐN KHUNG NHÁY"):
        with gr.Row():
            pts_3 = gr.Number(label="Mức cược (Điểm/1 con lô)", value=10)
            sim_size = gr.Number(label="Số lượng Lô giả định", value=22)
        btn_3 = gr.Button("🧪 MÔ PHỎNG LỢI NHUẬN TÙY BIẾN", variant="primary")
        out_3 = gr.Textbox(label="Phân Tích Hòa Vốn & Có Lãi", lines=16)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[pts_3, sim_size], outputs=out_3)

    with gr.Tab("🔍 [4] KIỂM TOÁN 1 NGÀY (SOI RÁC)"):
        gr.Markdown("*(Công cụ Quant chẩn đoán Rác và Tinh Hoa trong 1 ngày)*")
        with gr.Row():
            date_4 = gr.Textbox(label="Ngày Truy Xuất (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_4 = gr.Number(label="Mức cược (Điểm/con)", value=10)
        btn_4 = gr.Button("📡 KIỂM TOÁN ĐỐI SOÁT KÉP", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Lãi/Lỗ Tách Lớp", lines=24)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] KIỂM TOÁN THEO THÁNG"):
        with gr.Row():
            m_5 = gr.Slider(minimum=1, maximum=12, step=1, label="Tháng", value=latest_dt_init.month)
            y_5 = gr.Number(label="Năm", value=latest_dt_init.year)
            pts_5 = gr.Number(label="Mức cược (Điểm/con)", value=10)
        btn_5 = gr.Button("📊 KIỂM TOÁN DÒNG TIỀN THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Audit", lines=22)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] QUÉT TOÀN CHU KỲ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            pts_6 = gr.Number(label="Mức cược (Điểm/con)", value=10)
        btn_6 = gr.Button("📈 KIỂM TOÁN TOÀN BỘ LỊCH SỬ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền", lines=22)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] RAW DB"):
        date_7 = gr.Textbox(label="Nhập ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRUY XUẤT RAW DATA", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Thô", lines=10)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
