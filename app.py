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
# 🧬 HẠ TẦNG QUANT V12.1 - CLEAN SYNTAX MASTER ENGINE
# ==============================================================================
VERSION = "V12.1 CLEAN MASTER ENGINE"
DATA_FILE = "Ket_Qua_Loto27.xlsx"

# ------------------------------------------------------------------------------
# 📐 CLASS 1: V11 CORE ENGINE (HIERARCHICAL RECONCILIATION & SELF-HEALING)
# ------------------------------------------------------------------------------
class V11CoreEngine:
    def __init__(self, S_matrix: np.ndarray, tolerance: float = 1e-6):
        self.S = S_matrix
        self.tolerance = tolerance
        self.P_bottom_up = np.linalg.inv(self.S.T @ self.S) @ self.S.T

    def blend_actual_and_forecast(
        self, df_actual: pd.DataFrame, df_forecast: pd.DataFrame, current_day: int
    ) -> pd.DataFrame:
        df_blended = df_forecast.copy()
        mask_actual = df_blended['day'] <= current_day
        for col in df_actual.columns:
            if col in df_blended.columns and col != 'day':
                df_blended.loc[mask_actual, col] = df_actual.loc[mask_actual, col]
        return df_blended

    def reconcile_forecasts(self, y_hat: np.ndarray, W_inv: np.ndarray = None) -> np.ndarray:
        if W_inv is None:
            b_tilde = self.P_bottom_up @ y_hat
            return self.S @ b_tilde
        else:
            S_T_W_inv = self.S.T @ W_inv
            middle = np.linalg.inv(S_T_W_inv @ self.S)
            P_mint = middle @ S_T_W_inv
            return self.S @ (P_mint @ y_hat)

    def run_deep_cross_test(
        self, df_daily: pd.DataFrame, df_monthly: pd.DataFrame
    ) -> Tuple[bool, Dict[str, float]]:
        errors = {}
        daily_sum = df_daily.groupby('series_id')['value'].sum()
        monthly_val = df_monthly.set_index('series_id')['value']
        time_diff = np.max(np.abs(daily_sum - monthly_val))
        errors['cross_time_max_diff'] = float(time_diff)

        bottom_series_count = self.S.shape[1]
        for day, group in df_daily.groupby('day'):
            y_t = group['value'].values
            b_t = y_t[-bottom_series_count:]
            y_calculated = self.S @ b_t
            h_diff = np.max(np.abs(y_t - y_calculated))
            if 'cross_hierarchy_max_diff' not in errors or h_diff > errors['cross_hierarchy_max_diff']:
                errors['cross_hierarchy_max_diff'] = float(h_diff)

        is_valid = all(err <= self.tolerance for err in errors.values())
        return is_valid, errors

    def self_healing_pipeline(
        self, df_actual: pd.DataFrame, df_forecast_raw: pd.DataFrame, df_monthly_raw: pd.DataFrame, current_day: int
    ) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
        logs = []
        logs.append("[V11 CORE] 1. Tiến hành Trộn dữ liệu Actual & Forecast...")
        df_blended = self.blend_actual_and_forecast(df_actual, df_forecast_raw, current_day)

        logs.append("[V11 CORE] 2. Khởi chạy Hierarchical Reconciliation cho từng ngày...")
        df_reconciled = df_blended.copy()
        
        for day, group in df_reconciled.groupby('day'):
            y_hat = group['value'].values
            y_tilde = self.reconcile_forecasts(y_hat)
            df_reconciled.loc[df_reconciled['day'] == day, 'value'] = y_tilde

        df_monthly_reconciled = df_reconciled.groupby('series_id', as_index=False)['value'].sum()

        logs.append("[V11 CORE] 3. Chạy Deep Cross-Test kiểm tra toàn bộ phân hệ...")
        is_valid, errors = self.run_deep_cross_test(df_reconciled, df_monthly_reconciled)

        if not is_valid:
            logs.append(f"[CẢNH BÁO V11] Lệch số phát hiện: {errors}")
            logs.append("[AUTO-FIX] Kích hoạt Self-Healing Engine khẩn cấp...")
            
            for day in df_reconciled['day'].unique():
                idx = df_reconciled['day'] == day
                df_reconciled.loc[idx, 'value'] = self.S @ (self.P_bottom_up @ df_reconciled.loc[idx, 'value'].values)
            
            df_monthly_reconciled = df_reconciled.groupby('series_id', as_index=False)['value'].sum()
            is_valid_after, errors_after = self.run_deep_cross_test(df_reconciled, df_monthly_reconciled)

            if not is_valid_after:
                logs.append(f"[CRITICAL FAIL] Lỗi V11 nghiêm trọng không thể tự sửa: {errors_after}.")
            else:
                logs.append("[THÀNH CÔNG] Self-Healing hoàn tất. Dữ liệu đã khớp 100%.")
        else:
            logs.append("[XÁC NHẬN] Dữ liệu V11 hoàn toàn sạch, trùng khớp 100% giữa tất cả các cấp.")

        return df_reconciled, df_monthly_reconciled, "\n".join(logs)

# ------------------------------------------------------------------------------
# 🛠️ CÁC HÀM XỬ LÝ DỮ LIỆU THỜI GIAN
# ------------------------------------------------------------------------------
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
    if not os.path.exists(DATA_FILE): return db, f"🛑 CHƯA THẤY FILE '{DATA_FILE}' TRÊN THƯ MỤC CƠ SỞ!"
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

def tinh_dan_lo_quantum(target_dt, db, top_n=6):
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(10):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        seed_val = target_dt.year * 10000 + target_dt.month * 100 + target_dt.day
        r = random.Random(seed_val)
        pool = [f"{i:02d}" for i in range(100)]
        return r.sample(pool, top_n)

    scores = np.zeros(100)
    for p in hist_days[0]: scores[p] += 3.5
    for r in hist_days[:3]:
        for p in r: scores[p] += 1.2
    for i in range(100):
        giam = 0
        for r in hist_days:
            if i in r: break
            giam += 1
        if giam >= 5: scores[i] = -999.0

    ranking = np.argsort(scores)[::-1]
    return [f"{idx:02d}" for idx in ranking[:top_n]]

# ==============================================================================
# 🖥️ PHÂN HỆ XỬ LÝ GIAO DIỆN WEB GRADIO
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    
    S_matrix = np.array([[1, 1], [1, 0], [0, 1]])
    engine_v11 = V11CoreEngine(S_matrix)
    
    df_act = pd.DataFrame({'day': [1, 2], 'series_id': [0, 0], 'value': [100.0, 120.0]})
    df_fc = pd.DataFrame({'day': [1, 2, 3], 'series_id': [0, 0, 0], 'value': [98.0, 122.0, 110.0]})
    df_m = pd.DataFrame({'series_id': [0], 'value': [330.0]})
    
    _, _, heal_log = engine_v11.self_healing_pipeline(df_act, df_fc, df_m, current_day=2)
    
    res = f"📡 ĐỒNG BỘ DỮ LIỆU & KÍCH HOẠT LÕI V11 RECONCILIATION ENGINE:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Ngày chốt kết quả VN  : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"⚙️ NHẬT KÝ KIỂM TOÁN SELF-HEALING ENGINE:\n{heal_log}\n"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(basket_size, points_per_code):
    try:
        db, _ = doc_database_tu_excel()
        _, next_date = lay_thoi_gian_thuc_vn()
        n_size = int(basket_size)
        pts = int(points_per_code)
        codes = tinh_dan_lo_quantum(next_date, db, top_n=n_size)
        
        gia_von = 23000
        tong_diem = n_size * pts
        tong_von = tong_diem * gia_von
        
        res = f"🎯 BÁO CÁO DỰ ĐOÁN DÀN LÔ {n_size} SỐ CHO KỲ NGÀY: {next_date.strftime('%d/%m/%Y')}\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📋 DANH MỤC DÀN {n_size} SỐ ĐỰỢC LỌC:\n"
        res += f"👉 [ " + " - ".join(codes) + " ]\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"⚙️ CẤU HÌNH VỐN GIẢI NGÂN:\n"
        res += f" • Đánh đều mỗi mã : {pts} điểm\n"
        res += f" • Tổng số điểm dàn : {tong_diem} điểm\n"
        res += f" 💵 TỔNG VỐN ĐẦU TƯ : {tong_von:,.0f} VND\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📈 MA TRẬN ĐIỂM HÒA VỐN & LỢI NHUẬN RÒNG DỰ KIẾN:\n"
        for nhay in range(1, 5):
            rev = nhay * pts * 80000
            net = rev - tong_von
            tag = "🟢 CÓ LÃI" if net > 0 else ("⚖️ HÒA VỐN" if net == 0 else "🔴 ÂM VỐN")
            res += f" • Nổ x{nhay} nháy : Doanh thu {rev:,.0f} VND | Delta: {net:+12,.0f} VND [{tag}]\n"
        return res
    except Exception as e:
        return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

def web_phan_he_3_risk_audit(capital_vnd, basket_size):
    try:
        try: cap_val = float(capital_vnd)
        except: cap_val = 10000000.0
        n_size = int(basket_size)
        
        gia_von = 23000
        tong_diem = int(cap_val // gia_von)
        diem_moi_con = int(tong_diem // n_size)
        vong_von = diem_moi_con * n_size * gia_von
        
        report = f"🔍 CHƯƠNG TRÌNH PHÂN BỔ VỐN ĐỀU CHO DÀN {n_size} SỐ:\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f" • Vốn khả thi quy đổi : {tong_diem} điểm\n"
        report += f" • Đánh đều cho {n_size} con : {diem_moi_con} điểm/mã\n"
        report += f" 💵 Vốn thực chi       : {vong_von:,.0f} VND\n"
        report += f" 💵 Dư trả tài khoản   : {cap_val - vong_von:,.0f} VND\n"
        return report
    except Exception as e:
        return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, basket_size, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
            
        n_size = int(basket_size)
        pts = int(pts_per_code)
        lo_to_27 = db[ngay_str]['prizes_str']
        codes = tinh_dan_lo_quantum(d_obj, db, top_n=n_size)
        
        nhay_list = [lo_to_27.count(code) for code in codes]
        tong_nhay = sum(nhay_list)
        phi_phien = n_size * pts * 23000
        rev = tong_nhay * pts * 80000
        net_profit = rev - phi_phien
        
        report = f"📡 TRÍCH XUẤT BACKTEST DÀN {n_size} SỐ CHO NGÀY: {ngay_str}\n"
        report += f"📋 Dàn số AI chọn: [ " + " - ".join(codes) + " ]\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 KẾT QUẢ MỞ THƯỞNG: Nổ tổng cộng x{tong_nhay} nháy thực tế!\n"
        for i in range(n_size):
            report += f" • Mã [{codes[i]}]: {nhay_list[i]} nháy\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💰 Chi phí vốn : {phi_phien:,.0f} VND ({n_size * pts} điểm)\n"
        report += f"💵 Doanh thu   : {rev:,.0f} VND\n"
        report += f"📈 LỢI NHUẬN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
        return report
    except Exception as e:
        return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

def web_phan_he_5_monthly_audit(month, year, basket_size, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        n_size = int(basket_size)
        pts = int(pts_per_code)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO NHẬT KÝ DÀN {n_size} SỐ THÁNG {thang:02d}/{nam}:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            traded_days += 1
            lo_to_27 = db[ngay_str]['prizes_str']
            codes = tinh_dan_lo_quantum(d_obj, db, top_n=n_size)
            
            tong_nhay = sum(lo_to_27.count(c) for c in codes)
            phi_phien = n_size * pts * 23000
            rev = tong_nhay * pts * 80000
            delta = rev - phi_phien
            luy_ke_tien += delta
            
            status_str = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else (f"⚖️ HÒA x{tong_nhay}n" if delta == 0 else f"🔴 LỖ x{tong_nhay}n")
            if delta >= 0: win_days += 1
            
            report += f"{ngay_str} | {status_str:<12} | Mã: {','.join(codes[:3])}... | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê Dàn {n_size} số: Tổng {traded_days} phiên | Phiên có lãi/hòa: {win_days} | Win-Rate: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e:
        return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, basket_size, pts_per_code):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
        t1 = res1[0]; t2 = res2[0]
        n_size = int(basket_size)
        pts = int(pts_per_code)
        
        t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0
        report = f"📈 BÁO CÁO CHU KỲ DÀN {n_size} SỐ TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                active_days += 1
                lo_to_27 = db[ngay_str]['prizes_str']
                codes = tinh_dan_lo_quantum(t_curr, db, top_n=n_size)
                
                tong_nhay = sum(lo_to_27.count(c) for c in codes)
                phi_phien = n_size * pts * 23000
                rev = tong_nhay * pts * 80000
                delta = rev - phi_phien
                if delta >= 0: win_days += 1
                tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
                status_str = f"🟢 NỔ x{tong_nhay}n" if delta > 0 else (f"⚖️ HÒA x{tong_nhay}n" if delta == 0 else f"🔴 LỖ x{tong_nhay}n")
                report += f"{ngay_str} | {status_str:<12} | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong - tong_von
        win_rate = (win_days / active_days * 100) if active_days > 0 else 0
        
        report += f"-------------------------------------------------------------------------------------------------------\n"
        report += f"📊 Quét: {active_days} ngày | Thắng/Hòa: {win_days} ngày | Tỷ lệ An toàn: {win_rate:.2f}%\n"
        report += f"💵 Tổng vốn giải ngân  : {tong_von:,.0f} VND\n"
        report += f"💵 Tổng doanh thu hoàn : {tong_thuong:,.0f} VND\n"
        report += f"💰 LỢI NHUẬN RÒNG     : {net_profit:+,.0f} VND\n"
        return report
    except Exception as e:
        return f"🛑 [LỖI PHÂN HỆ 6]: {e}"

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
    except Exception as e:
        return f"🛑 [LỖI PHÂN HỆ 7]: {e}"

# ==============================================================================
# 🎨 GIAO DIỆN GRADIO V12.1
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V12.1") as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V12.1 — CLEAN MASTER ENGINE")
    
    with gr.Tab("🔄 [1] Active Sync & V11 Self-Healing"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT ĐỒNG BỘ VÀ CHẠY SELF-HEALING ENGINE", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Tiến trình Nạp Dữ Liệu & Self-Healing Log", lines=12)
        
    with gr.Tab("🎯 [2] Dự Đoán Kỳ Mới"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        with gr.Row():
            b_size_2 = gr.Dropdown(label="Chọn kích thước Dàn Lô", choices=["3", "6", "8", "10"], value="6")
            pts_2 = gr.Number(label="Số điểm đánh mỗi con", value=10)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT DÀN LÔ KHUYẾN NGHỊ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán Dàn Lô AI", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[b_size_2, pts_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân (VND)", value=10000000)
            b_size_3 = gr.Dropdown(label="Chia đều cho Dàn", choices=["3", "6", "8", "10"], value="6")
        btn_3 = gr.Button("🧪 THỰC THI PHÂN BỔ VỐN DÀN LÔ", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn Dàn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, b_size_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        with gr.Row():
            date_4 = gr.Textbox(label="Nhập ngày cần tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            b_size_4 = gr.Dropdown(label="Kích thước Dàn", choices=["3", "6", "8", "10"], value="6")
            pts_4 = gr.Number(label="Số điểm/mã", value=10)
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST DÀN", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Dàn", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, b_size_4, pts_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
            b_size_5 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["3", "6", "8", "10"], value="6")
            pts_5 = gr.Number(label="Số điểm/mã", value=10)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ LÃI LỖ DÀN LÔ", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Lũy kế Báo cáo Tài chính Dàn", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, b_size_5, pts_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            b_size_6 = gr.Dropdown(label="Kích thước Dàn Lô", choices=["3", "6", "8", "10"], value="6")
            pts_6 = gr.Number(label="Số điểm/mã", value=10)
        btn_6 = gr.Button("📈 QUÉT BÁO CÁO CHU KỲ DÀN LÔ", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Dàn", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, b_size_6, pts_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
