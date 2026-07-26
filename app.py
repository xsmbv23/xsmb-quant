import os
import sys
import time
import math
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, List
import gradio as gr

# ==============================================================================
# 🧬 HẠ TẦNG QUANT V28.1 - FULL 7 MENUS & MONTHLY RESET SHIELD
# ==============================================================================
VERSION = "V28.1 FULL SHIELD MASTER"
DATA_FILE = "Ket_Qua_Loto27.xlsx"

GLOBAL_PRED_CACHE = {}

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
    if not os.path.exists(DATA_FILE): return db, f"🛑 CHƯA THẤY FILE '{DATA_FILE}' TRÊN SERVER!"
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
# 🎯 LÕI V28.1: BỘ LỌC MULTI-BRIDGE & 2 LỚP PHANH STOP-LOSS
# ==============================================================================
def tinh_cap_lo_v28_shield(target_dt, db, user_base_pts=10, luy_ke_hien_tai=0.0, streak_loss=0, stop_loss_limit=-2000000):
    
    if luy_ke_hien_tai <= stop_loss_limit:
        return [], False, f"☠️ DEAD ZONE (KHÓA TÀI KHOẢN): Lỗ {luy_ke_hien_tai:,.0f}đ đã chạm ngưỡng Cắt lỗ cứng ({stop_loss_limit:,.0f}đ). TỪ CHỐI GIAO DỊCH!", 0.0, {}, 0, "HARD_STOP_LOSS"

    if streak_loss >= 3:
        return [], False, f"🚨 COOLDOWN BREAKER: Thua {streak_loss} phiên liên tiếp -> Đạp phanh nghỉ 1 phiên cắt đứt dây đen", 0.0, {}, 0, "COOLDOWN_SKIP"

    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(15):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 5:
        return [], False, "🛑 ĐÓNG VAN: Dữ liệu Excel chưa đủ (< 5 ngày)", 0.0, {}, 0, "SKIP"

    scores = np.zeros(100)
    head_counts = np.zeros(10)
    tail_counts = np.zeros(10)

    for p in hist_days[0]:
        scores[p] += 3.5
        head_counts[p // 10] += 1
        tail_counts[p % 10] += 1
        if len(hist_days) > 1 and p in hist_days[1]:
            scores[p] += 1.8

    for idx, r_p in enumerate(hist_days[:5]):
        weight = 1.5 - (idx * 0.25)
        for p in r_p: scores[p] += weight

    top_heads = np.argsort(head_counts)[-3:]
    top_tails = np.argsort(tail_counts)[-3:]
    for h in top_heads:
        for t in top_tails:
            code = h * 10 + t
            scores[code] += 1.5 

    is_cold = np.zeros(100, dtype=bool)
    for i in range(100):
        giam = 0
        for r_p in hist_days:
            if i in r_p: break
            giam += 1
        if giam >= 5: is_cold[i] = True

    valid_pair_scores = {}
    for i in range(100):
        c1 = f"{i:02d}"; c2 = c1[1] + c1[0]
        if c1 == c2: continue
        pair_key = tuple(sorted([c1, c2]))
        if pair_key not in valid_pair_scores:
            idx1, idx2 = int(c1), int(c2)
            if not is_cold[idx1] and not is_cold[idx2]:
                pair_score = scores[idx1] + scores[idx2]
                if idx1 in hist_days[0] and idx2 in hist_days[0]: pair_score += 2.0
                if abs(idx1 - idx2) == 50 or abs(int(c1[0]) - int(c1[1])) == 5: pair_score += 1.2
                valid_pair_scores[pair_key] = pair_score

    sorted_pairs = sorted(valid_pair_scores.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_pairs) < 4:
        return [], False, "🛑 CẤM ĐÁNH: Không đủ cặp hợp lệ", 0.0, {}, 0, "SKIP"

    top_4_pairs = [p[0] for p in sorted_pairs[:4]]
    top_4_scores = [p[1] for p in sorted_pairs[:4]]
    a4_score = float(np.mean(top_4_scores))

    if a4_score < 14.5:
        gate_status = "SKIP"
        is_trade = False
        final_pairs = []
        actual_pts = 0
        reason = f"🛑 LOW SIGNAL (PHANH DU KÍCH): Cầu mờ/Nhiễu (Score = {a4_score:.2f} < 14.50) -> Đứng ngoài bảo toàn vốn"
    elif luy_ke_hien_tai < 0:
        gate_status = "SNIPER_RECOVERY"
        is_trade = True
        final_pairs = top_4_pairs[:1]
        actual_pts = int(user_base_pts)
        reason = f"⚡ SNIPER RECOVERY (GỠ ÂM): Tài khoản đang âm ({luy_ke_hien_tai:,.0f}đ) -> Bắn tỉa duy nhất 1 Cặp lấy +84.3% ROI"
    elif 14.5 <= a4_score < 16.5:
        gate_status = "BALANCED_FLOW"
        is_trade = True
        final_pairs = top_4_pairs[:2]
        actual_pts = max(1, int(user_base_pts * 0.5))
        reason = f"🌗 BALANCED FLOW (CÂN BẰNG): Tín hiệu trung bình (Score = {a4_score:.2f}) -> Đánh 2 Cặp, cược 50% tiền"
    else:
        gate_status = "FULL_POWER"
        is_trade = True
        final_pairs = top_4_pairs
        actual_pts = int(user_base_pts)
        reason = f"🔥 FULL POWER (TẤN CÔNG): Tín hiệu cực nét (Score = {a4_score:.2f} >= 16.50) -> Đánh 4 Cặp, cược 100% tiền"

    pair_details = {p[0]: p[1] for p in sorted_pairs[:4]}
    return final_pairs, is_trade, reason, a4_score, pair_details, actual_pts, gate_status

def truy_xuat_trang_thai_real(db, base_pts, cost_pt, target_dt, stop_loss_limit):
    # Quét chuỗi ngày TRONG CÙNG 1 THÁNG để tính Lũy kế (Tự động Reset quỹ đầu tháng)
    all_dates = sorted([info['date_obj'] for info in db.values() 
                        if info['date_obj'] < target_dt 
                        and info['date_obj'].month == target_dt.month 
                        and info['date_obj'].year == target_dt.year])
    if not all_dates:
        return 0.0, 0
    
    luy_ke = 0.0
    streak_loss = 0
    
    for d_obj in all_dates:
        ngay_str = d_obj.strftime("%d/%m/%Y")
        if ngay_str not in db: continue
        
        pairs, is_trade, _, _, _, actual_pts, gate_status = tinh_cap_lo_v28_shield(
            d_obj, db, user_base_pts=base_pts, luy_ke_hien_tai=luy_ke, streak_loss=streak_loss, stop_loss_limit=stop_loss_limit
        )
        
        if not is_trade:
            if gate_status == "COOLDOWN_SKIP":
                streak_loss = 0
            continue
            
        lo_to_27 = db[ngay_str]['prizes_str']
        all_codes = [c for p in pairs for c in p]
        tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
        
        phi_phien = len(all_codes) * actual_pts * cost_pt
        doanh_thu = tong_nhay * actual_pts * 80000
        so_lai = doanh_thu - phi_phien
        
        luy_ke += so_lai
        if so_lai >= 0:
            streak_loss = 0
        else:
            streak_loss += 1
            
    return luy_ke, streak_loss

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN GRADIO V28.1
# ==============================================================================

# --- PHÂN HỆ 1: SYNC ---
def web_phan_he_1_sync():
    global GLOBAL_PRED_CACHE
    GLOBAL_PRED_CACHE.clear()
    db, msg = doc_database_tu_excel()
    latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    
    res = f"📡 KẾT NỐI HỆ THỐNG QUANT V28.1 FULL SHIELD MASTER:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File Excel : {msg}\n"
    res += f"• Ngày chốt Excel gần nhất: 📅 [{latest_dt.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán MỚI  : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]\n"
    return res, f"#### Kỳ quay dự đoán tiếp theo: {next_predict_dt.strftime('%d/%m/%Y')}"

# --- PHÂN HỆ 2: PREDICT ---
def web_phan_he_2_predict(cost_per_point, pts_per_code_base, sl_limit):
    try:
        db, _ = doc_database_tu_excel()
        latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
        cost_pt = float(cost_per_point)
        base_pts = int(pts_per_code_base)
        stop_loss = -abs(float(sl_limit))
        
        real_luy_ke, real_loss_streak = truy_xuat_trang_thai_real(db, base_pts, cost_pt, next_predict_dt, stop_loss)
        
        pairs, is_trade, reason, sc, p_details, actual_pts, gate_status = tinh_cap_lo_v28_shield(
            next_predict_dt, db, user_base_pts=base_pts, luy_ke_hien_tai=real_luy_ke, streak_loss=real_loss_streak, stop_loss_limit=stop_loss
        )
        
        tong_con = len(pairs) * 2
        tong_diem = tong_con * actual_pts if is_trade else 0
        tong_von = tong_diem * cost_pt
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN V28.1 (SHIELD) CHO KỲ: {next_predict_dt.strftime('%d/%m/%Y')}\n"
        res += f"📌 (Ngưỡng Cắt Lỗ Cứng: {stop_loss:,.0f} VND - Reset mùng 1 hàng tháng)\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"🔍 HỒ SƠ TÀI KHOẢN TRÍCH XUẤT TỪ EXCEL:\n"
        res += f" • Lũy kế dòng tiền TRONG THÁNG NÀY : {real_luy_ke:+,.0f} VND\n"
        res += f" • Số phiên thua liên tiếp vừa qua: {real_loss_streak} phiên\n"
        res += f"=================================================================================\n"
        res += f"🎚️ BỘ CHỈ HUY KIỂM SOÁT DÒNG VỐN : {reason}\n"
        res += f"=================================================================================\n"
        
        if not is_trade:
            res += f"🛑 TRẠNG THÁI: PHANH KỶ LUẬT (BẢO TOÀN VỐN)\n"
            res += f"💵 TỔNG TIỀN ĐÁNH : 0 VND\n"
            return res

        res += f"📋 CHI TIẾT CẶP LÔ CHỌN THỰC TẾ ({len(pairs)} cặp = {tong_con} con số):\n"
        for idx, p in enumerate(pairs):
            sc_val = p_details.get(p, 0.0)
            res += f"   • Cặp {idx+1} [{p[0]} - {p[1]}]: Điểm thô = {sc_val:.2f} | Cược thực tế: {actual_pts} điểm/con\n"
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
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

# --- PHÂN HỆ 3: QUẢN TRỊ VỐN ---
def web_phan_he_3_risk_audit(capital_vnd, cost_per_point):
    try:
        cap_val = float(capital_vnd)
        cost_pt = float(cost_per_point)
        pts_1pair = int((cap_val // cost_pt) // 2)
        von_1pair = pts_1pair * 2 * cost_pt
        
        report = f"🔍 CHƯƠNG TRÌNH XỬ LÝ DÒNG VỐN ÂM CỦA V28.1 ({cap_val:,.0f} VND):\n"
        report += f"=================================================================================\n"
        report += f"📊 MẬT ĐỘ BÓP NGHẸT RỦI RO & BẮN TỈA 1 CẶP (SONG THỦ 2 CON):\n"
        report += f" • Mức cược phân bổ  : {pts_1pair} điểm / con (Tổng {pts_1pair*2} điểm)\n"
        report += f" 💵 TỔNG TIỀN ĐÁNH   : {von_1pair:,.0f} VND (Thấp hơn 75% so với dàn 8 con)\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 ĐIỂM HÒA VỐN & ĐỘT PHÁ LÃI RÒNG GỠ ÂM:\n"
        report += f" • Nổ x1 nháy: Doanh thu {pts_1pair*80000:,.0f}đ -> LÃI RÒNG +{(pts_1pair*80000 - von_1pair):,.0f} VND (+84.3% ROI)! 🟢\n"
        report += f" • Nổ x2 nháy: Doanh thu {pts_1pair*2*80000:,.0f}đ -> LÃI RÒNG +{(pts_1pair*2*80000 - von_1pair):,.0f} VND (+268.6% ROI)! 🟢🟢\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

# --- PHÂN HỆ 4: BACKTEST ---
def web_phan_he_4_single_day_backtest(ngay_raw, cost_per_point, pts_per_code_base, sl_limit):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập không hợp lệ."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} CHƯA CÓ TRONG FILE EXCEL!"
            
        cost_pt = float(cost_per_point)
        base_pts = int(pts_per_code_base)
        stop_loss = -abs(float(sl_limit))
        lo_to_27 = db[ngay_str]['prizes_str']
        
        real_luy_ke, real_loss_streak = truy_xuat_trang_thai_real(db, base_pts, cost_pt, d_obj, stop_loss)
        pairs, is_trade, reason, sc, p_details, actual_pts, gate_status = tinh_cap_lo_v28_shield(
            d_obj, db, user_base_pts=base_pts, luy_ke_hien_tai=real_luy_ke, streak_loss=real_loss_streak, stop_loss_limit=stop_loss
        )
        
        report = f"📡 TRÍCH XUẤT BACKTEST KỲ NGÀY EXCEL: {ngay_str}\n"
        report += f"📌 Lũy kế đầu ngày (Đã reset quỹ theo tháng) = {real_luy_ke:+,.0f}đ | Chuỗi thua = {real_loss_streak} phiên\n"
        report += f"=================================================================================\n"
        report += f"🎚️ LỆNH ĐIỀU CHUYỂN : {reason}\n"
        report += f"=================================================================================\n"
        
        if not is_trade:
            report += f"🛑 TRẠNG THÁI: PHANH KỶ LUẬT KHÔNG VÀO LỆNH\n"
            return report

        all_codes = [c for p in pairs for c in p]
        nhay_dict = {c: lo_to_27.count(c) for c in all_codes}
        tong_nhay = sum(nhay_dict.values())
        tong_von = len(all_codes) * actual_pts * cost_pt
        doanh_thu = tong_nhay * actual_pts * 80000
        so_lai = doanh_thu - tong_von
        
        report += f"🎯 BÓC TÁCH KẾT QUẢ THỰC TẾ:\n"
        for idx, p in enumerate(pairs):
            n1 = nhay_dict[p[0]]; n2 = nhay_dict[p[1]]
            report += f" • Cặp {idx+1} [{p[0]} - {p[1]}]: Tổng x{n1+n2} nháy\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💥 TỔNG SỐ NHÁY TRÚNG : x{tong_nhay} nháy\n"
        report += f"💵 TỔNG TIỀN ĐÁNH     : {tong_von:,.0f} VND\n"
        report += f"📈 SỐ LÃI RÒNG (NET)  : {'+' if so_lai>=0 else ''}{so_lai:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

# --- PHÂN HỆ 5: LŨY KẾ THÁNG ---
def web_phan_he_5_monthly_audit(month, year, cost_per_point, pts_per_code_base, sl_limit):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        cost_pt = float(cost_per_point)
        base_pts = int(pts_per_code_base)
        stop_loss = -abs(float(sl_limit))
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO LŨY KẾ THÁNG {thang:02d}/{nam} (CÓ PHANH V28.1):\n"
        report += f"=======================================================================================================================================\n"
        report += f"{'NGÀY':<10} | {'MỨC ĐÁNH':<16} | {'CẶP LÔ DỰ ĐOÁN':<18} | {'TỔNG TIỀN ĐÁNH':<14} | {'NHÁY':<6} | {'SỐ LÃI PHIÊN':<14} | {'LŨY KẾ LÃI':<15}\n"
        report += f"=======================================================================================================================================\n"
        
        luy_ke_tien = 0; traded_days = 0; skip_days = 0; win_days = 0
        tong_von_thang = 0; tong_thuong_thang = 0
        streak_loss = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            pairs, is_trade, _, _, _, actual_pts, gate_status = tinh_cap_lo_v28_shield(
                d_obj, db, user_base_pts=base_pts, luy_ke_hien_tai=luy_ke_tien, streak_loss=streak_loss, stop_loss_limit=stop_loss
            )
            pair_strs = ",".join(f"{p[0]}-{p[1]}" for p in pairs) if len(pairs) > 0 else ("☠️ KHÓA" if gate_status == "HARD_STOP_LOSS" else "🛑 PHANH")
            lo_to_27 = db[ngay_str]['prizes_str']
            
            if not is_trade:
                skip_days += 1
                report += f"{ngay_str} | {gate_status:<16} | {pair_strs:<18} | {0:>14,.0f} | {0:>6} | {0:>+14,.0f} | {luy_ke_tien:>+15,.0f} đ\n"
                if gate_status == "COOLDOWN_SKIP": streak_loss = 0
                continue
                
            traded_days += 1
            all_codes = [c for p in pairs for c in p]
            tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
            
            phi_phien = len(all_codes) * actual_pts * cost_pt
            doanh_thu = tong_nhay * actual_pts * 80000
            so_lai = doanh_thu - phi_phien
            
            tong_von_thang += phi_phien; tong_thuong_thang += doanh_thu
            luy_ke_tien += so_lai
            
            if so_lai >= 0:
                win_days += 1
                streak_loss = 0
            else:
                streak_loss += 1
                
            report += f"{ngay_str} | {gate_status:<16} | {pair_strs:<18} | {phi_phien:>14,.0f} | {tong_nhay:>6} | {so_lai:>+14,.0f} | {luy_ke_tien:>+15,.0f} đ\n"
            
        report += f"=======================================================================================================================================\n"
        report += f"📊 TỔNG KẾT THÁNG {thang:02d}/{nam}:\n"
        report += f" • Bóp cò: {traded_days} ngày | Bỏ qua/Khóa: {skip_days} ngày\n"
        report += f" 💰 LÃI RÒNG THÁNG NÀY: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

# --- PHÂN HỆ 6: CHU KỲ (CÓ RESET THÁNG) ---
def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, cost_per_point, pts_per_code_base, sl_limit):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 Lỗi định dạng ngày."
        t1, t2 = res1[0], res2[0]
        if t1 > t2: t1, t2 = t2, t1
            
        cost_pt = float(cost_per_point)
        base_pts = int(pts_per_code_base)
        stop_loss = -abs(float(sl_limit))
        
        init_luy_ke, init_streak_loss = truy_xuat_trang_thai_real(db, base_pts, cost_pt, t1, stop_loss)
        
        t_curr = t1
        tong_von_all = 0; tong_thuong_all = 0
        luy_ke_range = init_luy_ke
        active_days = 0; win_days = 0; skip_cnt = 0
        streak_loss = init_streak_loss
        
        report = f"📈 BÁO CÁO CHU KỲ (CÓ RESET QUỸ RỦI RO ĐẦU THÁNG TẠI {stop_loss:,.0f}đ):\n"
        report += f"=======================================================================================================================================\n"
        report += f"{'NGÀY':<10} | {'MỨC ĐÁNH':<16} | {'CẶP LÔ DỰ ĐOÁN':<18} | {'TỔNG TIỀN ĐÁNH':<14} | {'NHÁY':<6} | {'SỐ LÃI PHIÊN':<14} | {'LŨY KẾ LÃI':<15}\n"
        report += f"=======================================================================================================================================\n"
        
        while t_curr <= t2:
            if t_curr > t1 and t_curr.day == 1:
                luy_ke_range = 0.0
                streak_loss = 0
                report += f"🔄 [{t_curr.strftime('%d/%m/%Y')}] --- HỆ THỐNG RESET QUỸ RỦI RO ĐẦU THÁNG MỚI VỀ 0Đ ---\n"
            
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                pairs, is_trade, _, _, _, actual_pts, gate_status = tinh_cap_lo_v28_shield(
                    t_curr, db, user_base_pts=base_pts, luy_ke_hien_tai=luy_ke_range, streak_loss=streak_loss, stop_loss_limit=stop_loss
                )
                pair_strs = ",".join(f"{p[0]}-{p[1]}" for p in pairs) if len(pairs) > 0 else ("☠️ KHÓA" if gate_status == "HARD_STOP_LOSS" else "🛑 PHANH")
                lo_to_27 = db[ngay_str]['prizes_str']
                
                if not is_trade:
                    skip_cnt += 1
                    report += f"{ngay_str} | {gate_status:<16} | {pair_strs:<18} | {0:>14,.0f} | {0:>6} | {0:>+14,.0f} | {luy_ke_range:>+15,.0f} đ\n"
                    if gate_status == "COOLDOWN_SKIP": streak_loss = 0
                else:
                    active_days += 1
                    all_codes = [c for p in pairs for c in p]
                    tong_nhay = sum(lo_to_27.count(c) for c in all_codes)
                    phi_phien = len(all_codes) * actual_pts * cost_pt
                    rev = tong_nhay * actual_pts * 80000
                    so_lai = rev - phi_phien
                    
                    if so_lai >= 0:
                        win_days += 1
                        streak_loss = 0
                    else:
                        streak_loss += 1
                    
                    tong_von_all += phi_phien; tong_thuong_all += rev; luy_ke_range += so_lai
                    report += f"{ngay_str} | {gate_status:<16} | {pair_strs:<18} | {phi_phien:>14,.0f} | {tong_nhay:>6} | {so_lai:>+14,.0f} | {luy_ke_range:>+15,.0f} đ\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong_all - tong_von_all
        report += f"=======================================================================================================================================\n"
        report += f"📊 THỐNG KÊ CHU KỲ:\n"
        report += f" • Bóp cò khai hỏa: {active_days} phiên | Đứng ngoài Đạp Phanh/Khóa: {skip_cnt} phiên\n"
        report += f" 💰 TỔNG SỐ LÃI RÒNG CHU KỲ: {net_profit:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 6]: {e}"

# --- PHÂN HỆ 7: RAW DB ---
def web_phan_he_7_raw_db_lookup(ngay_raw):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Lỗi định dạng ngày."
        _, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} CHƯA CÓ TRONG FILE EXCEL!"
            
        lo_to_sorted = sorted(db[ngay_str]['prizes_str'])
        report = f"📅 KẾT QUẢ DẢI LÔ TÔ THỰC TẾ NGÀY {ngay_str}:\n"
        report += "🎰 27 Giải ma trận phẳng:\n"
        for idx, lo in enumerate(lo_to_sorted): 
            report += f"[{lo}] " + ("\n" if (idx + 1) % 9 == 0 else " ")
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 7]: {e}"

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO V28.1 (ĐẦY ĐỦ 7 TAB TÍNH NĂNG)
# ==============================================================================
db_init, _ = doc_database_tu_excel()
latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

with gr.Blocks(title="XSMB QUANT V28.1 SHIELD") as demo:
    gr.Markdown("# 🛡️ XSMB QUANT V28.1 — FULL 7 MENUS & SHIELD MASTER")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT NẠP DỮ LIỆU", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=5)
        
    with gr.Tab("🎯 [2] Dự Đoán Có Phanh"):
        title_2 = gr.Markdown(f"#### Kỳ quay dự đoán tiếp theo: {next_predict_dt_init.strftime('%d/%m/%Y')}")
        with gr.Row():
            cost_2 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_2 = gr.Number(label="Mốc cược CƠ SỞ", value=10)
            sl_2 = gr.Number(label="Ngưỡng Cắt Lỗ Cứng (VND)", value=-2000000)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT LỆNH", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Lệnh V28.1", lines=14)
        btn_2.click(web_phan_he_2_predict, inputs=[cost_2, pts_2, sl_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn Bắn Tỉa"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
            cost_3 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_3 = gr.Button("🧪 LẬP SƠ ĐỒ ĐIỀU TIẾT VỐN BẮN TỈA", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, cost_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest"):
        with gr.Row():
            date_4 = gr.Textbox(label="Ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
            cost_4 = gr.Number(label="Giá vốn", value=21700)
            pts_4 = gr.Number(label="Cược CƠ SỞ", value=10)
            sl_4 = gr.Number(label="Ngưỡng Cắt Lỗ (VND)", value=-2000000)
        btn_4 = gr.Button("📡 BACKTEST V28.1", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, cost_4, pts_4, sl_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng", value=latest_dt_init.month)
            y_5 = gr.Number(label="Năm", value=latest_dt_init.year)
            cost_5 = gr.Number(label="Giá vốn điểm", value=21700)
            pts_5 = gr.Number(label="Mốc cược CƠ SỞ", value=10)
            sl_5 = gr.Number(label="Cắt Lỗ Tối Đa (VND)", value=-2000000)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Bảng Nhật ký", lines=18)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, cost_5, pts_5, sl_5], outputs=out_5)

    with gr.Tab("📈 [6] Quét Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày", value="01/01/2026")
            t2_6 = gr.Textbox(label="Đến ngày", value=latest_dt_init.strftime("%d/%m/%Y"))
            cost_6 = gr.Number(label="Giá vốn", value=21700)
            pts_6 = gr.Number(label="Mốc cược", value=10)
            sl_6 = gr.Number(label="Cắt Lỗ Tối Đa (VND)", value=-2000000)
        btn_6 = gr.Button("📈 QUÉT CHU KỲ (RESET THÁNG)", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Dòng tiền", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, cost_6, pts_6, sl_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày (DD/MM/YYYY)", value=latest_dt_init.strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả", lines=8)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
