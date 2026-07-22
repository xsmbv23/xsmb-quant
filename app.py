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
# 🧬 HẠ TẦNG QUANT V16.0 - PROPORTIONAL RISK & SNIPER ENGINE
# ==============================================================================
VERSION = "V16.0 PROPORTIONAL RISK ENGINE"
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
# 🎯 LÕI V16.0: SOI MÃ + QUẢN TRỊ RỦI RO BÓP CÒ THEO TỶ LỆ DỰ ĐOÁN
# ==============================================================================
def tinh_dan_lo_proportional_risk(target_dt, db, top_n=30):
    """
    1. Soi điểm Ma trận Heatmap & Momentum
    2. Đánh giá Chỉ số Anomaly Score (0.0 - 10.0)
    3. Quyết định Van Bóp Cò (SKIP / HALF / FULL)
    4. Phân bổ điểm cược theo tỷ lệ tự tin (3x / 2x / 1x)
    """
    hist_days = []
    curr_t = target_dt - timedelta(days=1)
    for _ in range(12):
        s_str = curr_t.strftime("%d/%m/%Y")
        if s_str in db:
            hist_days.append(db[s_str]['prizes_int'])
        curr_t -= timedelta(days=1)

    if len(hist_days) < 3:
        seed_val = target_dt.year * 10000 + target_dt.month * 100 + target_dt.day
        r = random.Random(seed_val)
        pool = [f"{i:02d}" for i in range(100)]
        codes = sorted(r.sample(pool, top_n))
        pts_dict = {c: 1 for c in codes}
        return codes, pts_dict, False, "🛑 THIẾU DATA NỀN - TẮT VAN", 0.0

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

    ranking = np.argsort(scores)[::-1]
    top_indices = ranking[:top_n]
    top_codes = sorted([f"{idx:02d}" for idx in top_indices])

    # Đánh giá Anomaly Score
    top_scores = scores[top_indices]
    valid_scores = [s for s in top_scores if s > 0]
    anomaly_score = np.mean(valid_scores) if len(valid_scores) > 0 else 0.0

    # 🎚️ VAN BÓP CÒ THEO TỶ LỆ (TIERED FIRING TRIGGER)
    if anomaly_score < 6.5:
        is_trade = False
        multiplier = 0.0
        reason = f"🛡️ TẮT VAN: Chỉ số dị biệt quá thấp ({anomaly_score:.1f} < 6.5) -> Né nhiễu rác"
    elif anomaly_score < 8.0:
        is_trade = True
        multiplier = 0.5
        reason = f"🌗 BÓP CÒ 50% VỐN (HALF SNIPER): Độ lệch trung bình ({anomaly_score:.1f})"
    else:
        is_trade = True
        multiplier = 1.0
        reason = f"🔥 BÓP CÒ 100% VỐN (FULL SNIPER): Độ lệch hội tụ cực cao ({anomaly_score:.1f})"

    # 📊 PHÂN BỔ ĐIỂM CƯỢC THEO TỶ LỆ TỰ TIN (3x / 2x / 1x)
    pts_dict = {}
    for rank_idx, idx_val in enumerate(top_indices):
        code_str = f"{idx_val:02d}"
        if not is_trade:
            pts_dict[code_str] = 0
        else:
            if rank_idx < 10:
                base_p = 3  # Lớp Mũi Nhọn
            elif rank_idx < 20:
                base_p = 2  # Lớp Trung Gian
            else:
                base_p = 1  # Lớp Vệ Tinh
            
            final_p = max(1, int(round(base_p * multiplier))) if multiplier > 0 else 0
            pts_dict[code_str] = final_p

    return top_codes, pts_dict, is_trade, reason, anomaly_score

# ==============================================================================
# 🖥️ FULL 7 PHÂN HỆ GIAO DIỆN V16.0
# ==============================================================================
def web_phan_he_1_sync():
    db, msg = doc_database_tu_excel()
    curr_date, next_date = lay_thoi_gian_thuc_vn()
    res = f"📡 KẾT NỐI HỆ THỐNG V16.0 PROPORTIONAL RISK ENGINE:\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"• Trạng thái File       : {msg}\n"
    res += f"• Mốc chốt kết quả VN   : [{curr_date.strftime('%d/%m/%Y')}]\n"
    res += f"• Kỳ quay dự đoán mới   : 🚀 [{next_date.strftime('%d/%m/%Y')}]\n"
    res += f"---------------------------------------------------------------------------------\n"
    res += f"💡 QUẢN TRỊ RỦI RO MỚI: Tự động Bóp cò phân lớp (SKIP/HALF/FULL) & Cược tỷ lệ (3x/2x/1x)!"
    return res, f"#### Kỳ quay ngày: {next_date.strftime('%d/%m/%Y')}"

def web_phan_he_2_predict(cost_per_point):
    try:
        db, _ = doc_database_tu_excel()
        _, next_date = lay_thoi_gian_thuc_vn()
        cost_pt = float(cost_per_point)
        
        codes, pts_dict, is_trade, reason, sc = tinh_dan_lo_proportional_risk(next_date, db, top_n=30)
        tong_diem = sum(pts_dict.values())
        tong_von = tong_diem * cost_pt
        
        res = f"🎯 BÁO CÁO SOI MÃ & BÓP CÒ THEO TỶ LỆ CHO KỲ: {next_date.strftime('%d/%m/%Y')}\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"🎚️ Phán quyết Van : {reason}\n"
        res += f"📊 Tổng số điểm dàn: {tong_diem} điểm | Chi phí vốn: {tong_von:,.0f} VND (Giá {cost_pt:,.0f}đ)\n"
        res += f"---------------------------------------------------------------------------------\n"
        res += f"📋 DANH MỤC PHÂN BỔ ĐIỂM CƯỢC THEO TỶ LỆ TỰ TIN (Top 30):\n"
        
        top10 = codes[:10]; top20 = codes[10:20]; top30 = codes[20:30]
        res += f"• [LỚP MŨI NHỌN 3X] : " + " ".join(f"{c}({pts_dict[c]}đ)" for c in top10) + "\n"
        res += f"• [LỚP TRUNG GIAN 2X]: " + " ".join(f"{c}({pts_dict[c]}đ)" for c in top20) + "\n"
        res += f"• [LỚP VỆ TINH 1X]  : " + " ".join(f"{c}({pts_dict[c]}đ)" for c in top30) + "\n"
        res += f"---------------------------------------------------------------------------------\n"
        if not is_trade:
            res += f"🛡️ VAN AN TOÀN ĐÓNG: Bảo toàn 100% vốn mặt (0 VNĐ giải ngân).\n"
        else:
            res += f"📈 Kịch bản: Nổ trúng các con Lớp Mũi Nhọn 3x sẽ mang lại lợi nhuận biên đột biến! 🟢\n"
        return res
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 2]: {e}"

def web_phan_he_3_risk_audit(capital_vnd, cost_per_point):
    try:
        cap_val = float(capital_vnd)
        cost_pt = float(cost_per_point)
        
        # Mẫu cược tỷ lệ (10 con x 3đ + 10 con x 2đ + 10 con x 1đ = 60 điểm mẫu)
        diem_mau = 60
        scale_factor = int((cap_val // cost_pt) // diem_mau)
        scale_factor = max(1, scale_factor)
        
        d_top1 = 3 * scale_factor
        d_top2 = 2 * scale_factor
        d_top3 = 1 * scale_factor
        
        tong_diem = (d_top1 * 10) + (d_top2 * 10) + (d_top3 * 10)
        vong_von = tong_diem * cost_pt
        
        report = f"🔍 LẬP SƠ ĐỒ PHÂN BỔ VỐN CƯỢC THEO TỶ LỆ (KELLY PROPORTIONAL):\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f" • Lớp Mũi Nhọn  (10 mã) : Đánh {d_top1} điểm/mã  -> Tổng {d_top1*10} điểm\n"
        report += f" • Lớp Trung Gian (10 mã) : Đánh {d_top2} điểm/mã  -> Tổng {d_top2*10} điểm\n"
        report += f" • Lớp Vệ Tinh   (10 mã) : Đánh {d_top3} điểm/mã  -> Tổng {d_top3*10} điểm\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f" 💵 Tổng số điểm dàn thực chi : {tong_diem} điểm\n"
        report += f" 💵 Vốn thực chi giải ngân    : {vong_von:,.0f} VND (Giá vốn {cost_pt:,.0f}đ)\n"
        report += f" 💵 Số dư dự phòng tài khoản  : {cap_val - vong_von:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 3]: {e}"

def web_phan_he_4_single_day_backtest(ngay_raw, cost_per_point):
    try:
        db, _ = doc_database_tu_excel()
        res = chuan_hoa_ngay(ngay_raw)
        if not res: return "🛑 [ERROR] Định dạng ngày nhập vào không hợp lệ."
        d_obj, ngay_str = res
        if ngay_str not in db: return f"🛑 Ngày {ngay_str} chưa có trong file Excel."
            
        cost_pt = float(cost_per_point)
        lo_to_27 = db[ngay_str]['prizes_str']
        codes, pts_dict, is_trade, reason, sc = tinh_dan_lo_proportional_risk(d_obj, db, top_n=30)
        
        if not is_trade:
            return f"📡 BACKTEST NGÀY: {ngay_str}\n🎚️ Trạng Thái: {reason}\n🛡️ ĐÓNG VAN AN TOÀN -> BẢO TOÀN 100% VỐN (0 VNĐ)"
            
        tong_von = sum(pts_dict.values()) * cost_pt
        tong_thuong = sum(lo_to_27.count(c) * pts_dict[c] * 80000 for c in codes)
        net_profit = tong_thuong - tong_von
        
        report = f"📡 TRÍCH XUẤT BACKTEST BÓP CÒ TỶ LỆ CHO NGÀY: {ngay_str}\n"
        report += f"🎚️ Phán quyết Van : {reason}\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"🎯 CHI TIẾT CÁC MÃ NỔ THEO PHÂN LỚP TỶ LỆ:\n"
        for c in codes:
            nhay = lo_to_27.count(c)
            if nhay > 0:
                report += f" • Mã [{c}] ({pts_dict[c]}đ) -> Nổ x{nhay} nháy (+{nhay * pts_dict[c] * 80000:,.0f}đ) 🟢\n"
        report += f"---------------------------------------------------------------------------------\n"
        report += f"💰 Chi phí vốn : {tong_von:,.0f} VND ({sum(pts_dict.values())} điểm)\n"
        report += f"💵 Doanh thu   : {tong_thuong:,.0f} VND\n"
        report += f"📈 LỢI NHUẬN   : {'+' if net_profit>=0 else ''}{net_profit:,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 4]: {e}"

def web_phan_he_5_monthly_audit(month, year, cost_per_point):
    try:
        db, _ = doc_database_tu_excel()
        thang, nam = int(month), int(year)
        cost_pt = float(cost_per_point)
        max_days = lay_max_days(thang, nam)
        
        report = f"📊 BÁO CÁO QUẢN TRỊ RỦI RO BÓP CÒ TỶ LỆ THÁNG {thang:02d}/{nam}:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        luy_ke_tien = 0; traded_days = 0; skip_days = 0; win_days = 0
        
        for d in range(1, max_days + 1):
            d_obj = datetime(nam, thang, d)
            ngay_str = d_obj.strftime("%d/%m/%Y")
            if ngay_str not in db: continue
            
            codes, pts_dict, is_trade, _, _ = tinh_dan_lo_proportional_risk(d_obj, db, top_n=30)
            lo_to_27 = db[ngay_str]['prizes_str']
            
            if not is_trade:
                skip_days += 1
                report += f"{ngay_str} | 🛡️ ĐÓNG VAN  | [ĐÓNG VAN AN TOÀN - NÉ BẢO QUẢN CAPITAL]  | {luy_ke_tien:+12,.0f} VND\n"
                continue
                
            traded_days += 1
            tong_von = sum(pts_dict.values()) * cost_pt
            tong_thuong = sum(lo_to_27.count(c) * pts_dict[c] * 80000 for c in codes)
            delta = tong_thuong - tong_von
            luy_ke_tien += delta
            
            if delta >= 0: win_days += 1
            status_tag = f"🟢 WIN (+{delta:,.0f}đ)" if delta > 0 else f"🔴 LOSS ({delta:,.0f}đ)"
            report += f"{ngay_str} | {status_tag:<16} | Vốn: {tong_von:,.0f} | Delta: {delta:+10,.0f} | LK: {luy_ke_tien:+12,.0f} VND\n"
            
        report += f"-------------------------------------------------------------------------------------------------------\n"
        win_rate = (win_days / traded_days * 100) if traded_days > 0 else 0
        report += f"📊 Thống kê: Bóp cò {traded_days} phiên | Đóng van bảo toàn vốn: {skip_days} phiên\n"
        report += f"🎯 Phiên thắng/hòa: {win_days} | Tỷ lệ Win-Rate thực tế: {win_rate:.2f}%\n"
        report += f"💰 LỢI NHUẬN RÒNG LŨY KẾ THÁNG: {luy_ke_tien:+,.0f} VND\n"
        return report
    except Exception as e: return f"🛑 [LỖI PHÂN HỆ 5]: {e}"

def web_phan_he_6_range_performance(tu_ngay_raw, den_ngay_raw, cost_per_point):
    try:
        db, _ = doc_database_tu_excel()
        res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
        if not res1 or not res2: return "🛑 [ERROR] Lỗi định dạng ngày."
        t1 = res1[0]; t2 = res2[0]
        cost_pt = float(cost_per_point)
        
        t_curr = t1; tong_von = 0; tong_thuong = 0; luy_ke_range = 0; active_days = 0; win_days = 0; skip_cnt = 0
        report = f"📈 BÁO CÁO QUẢN TRỊ RỦI RO TỪ [{res1[1]}] ĐẾN [{res2[1]}]:\n"
        report += f"-------------------------------------------------------------------------------------------------------\n"
        while t_curr <= t2:
            ngay_str = t_curr.strftime("%d/%m/%Y")
            if ngay_str in db:
                codes, pts_dict, is_trade, _, _ = tinh_dan_lo_proportional_risk(t_curr, db, top_n=30)
                lo_to_27 = db[ngay_str]['prizes_str']
                
                if is_trade:
                    active_days += 1
                    phi_phien = sum(pts_dict.values()) * cost_pt
                    rev = sum(lo_to_27.count(c) * pts_dict[c] * 80000 for c in codes)
                    delta = rev - phi_phien
                    if delta >= 0: win_days += 1
                    tong_von += phi_phien; tong_thuong += rev; luy_ke_range += delta
                    status_tag = f"🟢 WIN (+{delta:,.0f}đ)" if delta > 0 else f"🔴 LOSS ({delta:,.0f}đ)"
                    report += f"{ngay_str} | {status_tag:<16} | Delta: {delta:+10,.0f} | LK: {luy_ke_range:+12,.0f} VND\n"
                else:
                    skip_cnt += 1
                    report += f"{ngay_str} | 🛡️ SKIP         | [ĐÓNG VAN BẢO TOÀN VỐN]          | LK: {luy_ke_range:+12,.0f} VND\n"
            t_curr += timedelta(days=1)
            
        net_profit = tong_thuong - tong_von
        win_rate = (win_days / active_days * 100) if active_days > 0 else 0
        
        report += f"-------------------------------------------------------------------------------------------------------\n"
        report += f"📊 Quét: Bóp cò {active_days} phiên | ĐỨng ngoài né bão: {skip_cnt} phiên\n"
        report += f"🎯 Phiên thắng/hòa: {win_days} | Tỷ lệ An toàn: {win_rate:.2f}%\n"
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
# 🎨 GIAO DIỆN GRADIO V16.0
# ==============================================================================
_, INITIAL_NEXT_DATE = lay_thoi_gian_thuc_vn()

with gr.Blocks(title="XSMB QUANT ENGINE V16.0") as demo:
    gr.Markdown("# 🚀 XSMB QUANT ENGINE V16.0 — PROPORTIONAL RISK & SNIPER ENGINE")
    
    with gr.Tab("🔄 [1] Active Sync"):
        btn_1 = gr.Button("⚡ KÍCH HOẠT ĐỒNG BỘ DỮ LIỆU CẬP NHẬT CHẾ ĐỘ RISK ENGINE", variant="primary")
        out_1 = gr.Textbox(label="Báo cáo Nạp Dữ Liệu", lines=8)
        
    with gr.Tab("🎯 [2] Dự Đoán & Bóp Cò Tỷ Lệ"):
        title_2 = gr.Markdown(f"#### Kỳ quay ngày: {INITIAL_NEXT_DATE.strftime('%d/%m/%Y')}")
        cost_2 = gr.Number(label="Giá vốn điểm (21700đ Web hoặc 23000đ Thường)", value=21700)
        btn_2 = gr.Button("🔍 TRÍCH XUẤT PHÂN BỔ ĐIỂM CƯỢC THEO TỶ LỆ", variant="primary")
        out_2 = gr.Textbox(label="Hồ sơ Dự đoán & Van Bóp Cò AI", lines=12)
        btn_2.click(web_phan_he_2_predict, inputs=[cost_2], outputs=out_2)

    with gr.Tab("🛡️ [3] Quản Trị Vốn Kelly"):
        with gr.Row():
            cap_3 = gr.Number(label="Số vốn giải ngân tổng (VND)", value=10000000)
            cost_3 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_3 = gr.Button("🧪 LẬP SƠ ĐỒ CƯỢC THEO TỶ LỆ TỰ TIN", variant="primary")
        out_3 = gr.Textbox(label="Chi Tiết Phân Bổ Vốn", lines=10)
        btn_3.click(web_phan_he_3_risk_audit, inputs=[cap_3, cost_3], outputs=out_3)

    with gr.Tab("🔍 [4] Backtest Đơn Phiên"):
        with gr.Row():
            date_4 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            cost_4 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_4 = gr.Button("📡 TRÍCH XUẤT BACKTEST BÓP CÒ TỶ LỆ", variant="primary")
        out_4 = gr.Textbox(label="Báo cáo Trúng thưởng Dàn Lô", lines=12)
        btn_4.click(web_phan_he_4_single_day_backtest, inputs=[date_4, cost_4], outputs=out_4)

    with gr.Tab("📊 [5] Lũy Kế Tháng"):
        with gr.Row():
            m_5 = gr.Number(label="Tháng cần xem", value=datetime.now().month)
            y_5 = gr.Number(label="Năm cần xem", value=datetime.now().year)
            cost_5 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_5 = gr.Button("📊 BÓC TÁCH LŨY KẾ CẢNH BÁO RISK THÁNG", variant="primary")
        out_5 = gr.Textbox(label="Nhật ký Báo cáo Tài chính Lũy kế Risk Engine", lines=16)
        btn_5.click(web_phan_he_5_monthly_audit, inputs=[m_5, y_5, cost_5], outputs=out_5)

    with gr.Tab("📈 [6] Hiệu Suất Chu Kỳ"):
        with gr.Row():
            t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/07/2026")
            t2_6 = gr.Textbox(label="Đến ngày (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
            cost_6 = gr.Number(label="Giá vốn điểm", value=21700)
        btn_6 = gr.Button("📈 QUÉT CHU KỲ RISK TÀI CHÍNH", variant="primary")
        out_6 = gr.Textbox(label="Báo cáo Hiệu suất Dòng tiền Risk Engine", lines=18)
        btn_6.click(web_phan_he_6_range_performance, inputs=[t1_6, t2_6, cost_6], outputs=out_6)

    with gr.Tab("🎰 [7] Xem 27 Giải Excel"):
        date_7 = gr.Textbox(label="Nhập ngày tra cứu (DD/MM/YYYY)", value=datetime.now().strftime("%d/%m/%Y"))
        btn_7 = gr.Button("💾 TRÍCH XUẤT LÔ TÔ EXCEL", variant="primary")
        out_7 = gr.Textbox(label="Bảng Kết Quả Lô Tô 27 Giải Real", lines=14)
        btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)

    btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    demo.launch(server_name="0.0.0.0", server_port=port, theme=gr.themes.Soft())
