import calendar
from datetime import datetime, timedelta
import math
import os
import re
import sys
import gradio as gr
import numpy as np
import pandas as pd

VERSION = "V36.1.0 PRO ALGO (BẢN THƯƠNG MẠI CAO CẤP - TÍCH HỢP TOÀN DIỆN)"
DATA_FILE = "Ket_Qua_Loto27.xlsx"
COST_PER_POINT = 21700
WIN_PER_NHAY = 80000

MODES = [
    "Giao Dịch Toàn Bộ T-7",
    "Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
    "Chỉ Giao Dịch SỐ KHUYẾT (Không Rơi/Đảo)",
]


def chuan_hoa_ngay(ngay_raw):
  if pd.isna(ngay_raw) or not str(ngay_raw).strip():
    return None
  try:
    s = str(ngay_raw).strip().split()[0].replace("-", "/").replace(".", "/")
    parts = [p for p in s.split("/") if p]
    if len(parts) < 3:
      return None
    d, m, y = parts[0], parts[1], parts[2]
    if len(d) == 4:
      y, m, d = d, m, y
    if len(d) == 1:
      d = "0" + d
    if len(m) == 1:
      m = "0" + m
    if len(y) == 2:
      y = "20" + y
    str_chuan = f"{d}/{m}/{y}"
    return datetime.strptime(str_chuan, "%d/%m/%Y"), str_chuan
  except Exception:
    return None


def lay_max_days(thang, nam):
  return calendar.monthrange(nam, thang)[1]


def safe_int(val, default=0):
  try:
    return int(float(val))
  except (ValueError, TypeError):
    return default


def check_valid_number(val, name):
  if val is None or str(val).strip() == "":
    return False, f"🛑 LỖI THÔNG SỐ: Vui lòng nhập thông tin cho '{name}'."
  try:
    f_val = float(val)
    if f_val <= 0:
      return False, f"🛑 LỖI THÔNG SỐ: Giá trị '{name}' phải lớn hơn 0."
    return True, ""
  except (ValueError, TypeError):
    return False, f"🛑 LỖI THÔNG SỐ: '{name}' không đúng định dạng số."


def doc_database_tu_excel():
  db = {}
  if not os.path.exists(DATA_FILE):
    return db, f"🛑 LỖI HỆ THỐNG: Không tìm thấy cơ sở dữ liệu '{DATA_FILE}'."
  try:
    df = pd.read_excel(DATA_FILE, dtype=str)
    if df.shape[1] < 2:
      return (
          db,
          "🛑 LỖI CẤU TRÚC: File dữ liệu phải có ít nhất 2 cột (Ngày và Danh"
          " sách kết quả).",
      )
    col_ngay = df.columns[0]
    col_loto = df.columns[1]
    dup_count = 0
    for _, row in df.iterrows():
      res_date = chuan_hoa_ngay(row[col_ngay])
      if not res_date:
        continue
      dt_obj, ngay_str = res_date
      loto_raw = re.sub(r"[^\d\s]", " ", str(row[col_loto]))
      loto_list = [
          int(x.strip()[-2:]) for x in loto_raw.split() if x.strip().isdigit()
      ]
      if len(loto_list) >= 27:
        if ngay_str in db:
          dup_count += 1
        db[ngay_str] = {
            "date_obj": dt_obj,
            "date_str": ngay_str,
            "prizes_int": loto_list[:27],
        }
    msg = f"🟢 ĐỒNG BỘ THÀNH CÔNG {len(db)} PHIÊN GIAO DỊCH."
    if dup_count > 0:
      msg += f" (Cảnh báo: Phát hiện {dup_count} dòng trùng ngày đã ghi đè)."
    return db, msg
  except Exception as e:
    return db, f"🛑 LỖI TRUY XUẤT DỮ LIỆU: {e}"


def lay_ngay_chot_tu_excel(db):
  if not db:
    today = datetime.now()
    return today, today, today + timedelta(days=1)
  all_dates = [info["date_obj"] for info in db.values()]
  min_dt = min(all_dates)
  max_dt = max(all_dates)
  return min_dt, max_dt, max_dt + timedelta(days=1)


def get_signal_v36(target_dt, db, mode):
  t_minus_7 = target_dt - timedelta(days=7)
  t_minus_1 = target_dt - timedelta(days=1)
  str_t7 = t_minus_7.strftime("%d/%m/%Y")
  str_t1 = t_minus_1.strftime("%d/%m/%Y")
  if str_t7 not in db:
    return None, f"[THIẾU DỮ LIỆU T-7 ({str_t7})]"
  dan_t7 = set(db[str_t7]["prizes_int"])
  if mode in [
      "Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
      "Chỉ Giao Dịch SỐ KHUYẾT (Không Rơi/Đảo)",
  ]:
    if str_t1 not in db:
      return None, f"[THIẾU DỮ LIỆU T-1 ({str_t1})]"
    kq_t1 = set(db[str_t1]["prizes_int"])
    tinh_hoa = set()
    for x in dan_t7:
      lon = (x % 10) * 10 + (x // 10)
      if x in kq_t1 or lon in kq_t1:
        tinh_hoa.add(x)
    if mode == "Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)":
      return sorted(list(tinh_hoa)), "OK"
    else:
      return sorted(list(dan_t7 - tinh_hoa)), "OK"
  else:
    return sorted(list(dan_t7)), "OK"


def web_phan_he_1_sync():
  db, msg = doc_database_tu_excel()
  _, latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
  lines = [
      "📑 [PHÂN HỆ 1] BÁO CÁO: ĐỒNG BỘ CƠ SỞ DỮ LIỆU",
      "=================================================================================",
      f"• Phiên bản hệ thống : {VERSION}",
      f"• Trạng thái Dữ liệu : {msg}",
      f"• Phiên cập nhật cuối: 📅 [{latest_dt.strftime('%d/%m/%Y')}]",
      f"• Lịch phân tích tới : 🚀 [{next_predict_dt.strftime('%d/%m/%Y')}]",
  ]
  return "\n".join(lines), (
      f"#### KHUYẾN NGHỊ GIAO DỊCH KỲ: {next_predict_dt.strftime('%d/%m/%Y')}"
  )


def web_phan_he_2_predict(pts_per_code_base, mode):
  try:
    db, _ = doc_database_tu_excel()
    _, latest_dt, next_predict_dt = lay_ngay_chot_tu_excel(db)
    is_valid, err_msg = check_valid_number(pts_per_code_base, "Khối lượng vốn")
    if not is_valid:
      return err_msg
    base_pts = safe_int(pts_per_code_base)
    dan, msg = get_signal_v36(next_predict_dt, db, mode)
    lines = [
        "📑 [PHÂN HỆ 2] BÁO CÁO: KHUYẾN NGHỊ GIAO DỊCH KẾ TIẾP",
        "=======================================================\n",
        f"🎯 PHIÊN GIAO DỊCH MỤC TIÊU: {next_predict_dt.strftime('%d/%m/%Y')}",
        f"🎚️ CHIẾN LƯỢC ÁP DỤNG: {mode}\n",
    ]
    if dan is None:
      lines.append(f"🛑 CẢNH BÁO RỦI RO: Dữ liệu tham chiếu {msg}.")
      lines.append(
          "HỆ THỐNG TỰ ĐỘNG TẠM NGỪNG CẤP TÍN HIỆU ĐỂ BẢO TOÀN VỐN."
      )
      return "\n".join(lines)
    so_luong_lo = len(dan)
    von_ngay = so_luong_lo * base_pts * COST_PER_POINT
    if so_luong_lo > 0:
      dan_str = " ".join([f"{x:02d}" for x in dan])
      lines.append(f"📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN ({so_luong_lo} MÃ):")
      lines.append(f" [ {dan_str} ]")
      lines.append("-------------------------------------------------------")
      lines.append(f" • Khối lượng phân bổ : {base_pts} điểm / 1 mã")
      lines.append(f"💰 TỔNG VỐN YÊU CẦU   : {von_ngay:,.0f} VND")
      diem_hoa_von_nhay = (
          math.ceil(von_ngay / (base_pts * WIN_PER_NHAY)) if base_pts > 0 else 0
      )
      lines.append(
          f"💡 MỤC TIÊU HÒA VỐN   : Cần tối thiểu {diem_hoa_von_nhay} lượt"
          " trúng."
      )
    else:
      lines.append("📋 DANH MỤC MÃ SỐ ĐẠT CHUẨN:")
      lines.append(" 👉 🚫 [KHÔNG CÓ TÍN HIỆU KHẢ THI]")
      lines.append("-------------------------------------------------------")
      lines.append("💰 TỔNG VỐN YÊU CẦU: 0 VND")
      lines.append(
          "💡 HỆ THỐNG KHUYẾN NGHỊ ĐỨNG NGOÀI THỊ TRƯỜNG TRONG PHIÊN NÀY."
      )
    return "\n".join(lines)
  except Exception as e:
    return f"🛑 LỖI PHÂN HỆ 2: {e}"


def web_phan_he_3_risk_audit(base_pts, sim_size):
  try:
    valid1, err1 = check_valid_number(base_pts, "Khối lượng vốn")
    valid2, err2 = check_valid_number(sim_size, "Số lượng Mã")
    if not valid1:
      return err1
    if not valid2:
      return err2
    base_pts = safe_int(base_pts)
    so_luong_lo = safe_int(sim_size)
    von_ngay = so_luong_lo * base_pts * COST_PER_POINT
    lines = [
        "📑 [PHÂN HỆ 3] BÁO CÁO: QUẢN TRỊ RỦI RO & MÔ PHỎNG LỢI NHUẬN",
        "====================================================================",
        (
            f"📊 KỊCH BẢN PHÂN BỔ {so_luong_lo} MÃ - TỔNG VỐN ĐẦU TƯ:"
            f" {von_ngay:,.0f} VNĐ"
        ),
        "--------------------------------------------------------------------",
        " LƯỢT TRÚNG   | DOANH THU KỲ VỌNG | LỢI NHUẬN RÒNG | TRẠNG THÁI",
        "--------------------------------------------------------------------",
    ]
    for nhay in range(0, int(so_luong_lo * 0.7) + 2):
      thuong = nhay * base_pts * WIN_PER_NHAY
      lai = thuong - von_ngay
      status = "🟢 LÃI RÒNG" if lai > 0 else "🔴 THUA LỖ"
      if nhay == 0:
        status += " (MẤT VỐN)"
      lai_str = f"{lai:+,.0f}" if lai != 0 else "0"
      lines.append(
          f" Đạt {nhay:>2} lượt  | {thuong:>17,.0f} | {lai_str:>14} |"
          f" {status}"
      )
    lines.append(
        "===================================================================="
    )
    return "\n".join(lines)
  except Exception as e:
    return f"🛑 LỖI PHÂN HỆ 3: {e}"


def web_phan_he_4_single_day_backtest(ngay_raw, pts_per_code_base):
  try:
    db, _ = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res:
      return "🛑 LỖI DỮ LIỆU: Định dạng ngày không hợp lệ."
    d_obj, ngay_str = res
    if ngay_str not in db:
      return (
          f"🛑 KHÔNG TÌM THẤY DỮ LIỆU: Phiên giao dịch {ngay_str} chưa được cập"
          " nhật."
      )
    valid, err = check_valid_number(pts_per_code_base, "Khối lượng vốn")
    if not valid:
      return err
    base_pts = safe_int(pts_per_code_base)
    lo_to_27_today = db[ngay_str]["prizes_int"]
    t_minus_7 = d_obj - timedelta(days=7)
    t_minus_1 = d_obj - timedelta(days=1)
    ngay_str_t7 = t_minus_7.strftime("%d/%m/%Y")
    ngay_str_t1 = t_minus_1.strftime("%d/%m/%Y")
    lines = [
        "📑 [PHÂN HỆ 4] BÁO CÁO: KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN",
        "========================================================================\n",
    ]
    if ngay_str_t7 not in db:
      lines.append(f"📡 THÔNG TIN PHIÊN: {ngay_str}")
      lines.append(
          f"🔭 LỖI CHU KỲ: Thiếu dữ liệu mốc T-7 ({ngay_str_t7}). Không thể phân"
          " tích!"
      )
      return "\n".join(lines)
    dan_t7 = set(db[ngay_str_t7]["prizes_int"])

    def cal_pnl(danh_sach):
      sl = len(danh_sach)
      if sl == 0:
        return 0, 0, 0, 0, 0, "⚫ KHÔNG GIAO DỊCH"
      chi_phi = sl * base_pts * COST_PER_POINT
      nhay = sum(lo_to_27_today.count(x) for x in danh_sach)
      doanh_thu = nhay * base_pts * WIN_PER_NHAY
      lai = doanh_thu - chi_phi
      status = "🟢 WIN" if lai > 0 else "🔴 LOSS"
      return sl, chi_phi, nhay, doanh_thu, lai, status

    list_full = sorted(list(dan_t7))
    sl_f, chi_f, nhay_f, thu_f, lai_f, st_f = cal_pnl(list_full)
    lai_f_str = f"{lai_f:+,.0f}" if lai_f != 0 else "0"
    lines.append(
        f"📡 KẾT QUẢ GIAO DỊCH PHIÊN: {ngay_str} (Phân bổ: {base_pts}đ/mã)\n"
    )
    lines.append(
        "🛑 [KỊCH BẢN 1] - GIAO DỊCH TOÀN BỘ T-7 (Tinh hoa + Khuyết nhịp)"
    )
    lines.append(
        f" • Danh mục {sl_f} mã: "
        + " ".join([f"{x:02d}" for x in list_full])
    )
    lines.append(
        f" • Đạt {nhay_f} lượt.  Vốn đầu tư: {chi_f:,.0f}đ  | Doanh thu:"
        f" {thu_f:,.0f}đ"
    )
    lines.append(f" 👉 LỢI NHUẬN RÒNG: {lai_f_str} VNĐ ({st_f})\n")
    if ngay_str_t1 not in db:
      lines.append(
          f"⚠️ LƯU Ý: Thiếu dữ liệu mốc T-1 ({ngay_str_t1}).\nKhông thể phân"
          " tách rủi ro cho Kịch bản 2 và 3."
      )
      return "\n".join(lines)
    kq_t1 = set(db[ngay_str_t1]["prizes_int"])
    tinh_hoa = set()
    for x in dan_t7:
      lon = (x % 10) * 10 + (x // 10)
      if x in kq_t1 or lon in kq_t1:
        tinh_hoa.add(x)
    rac = dan_t7 - tinh_hoa
    list_rac = sorted(list(rac))
    list_tinh_hoa = sorted(list(tinh_hoa))
    sl_r, chi_r, nhay_r, thu_r, lai_r, st_r = cal_pnl(list_rac)
    sl_t, chi_t, nhay_t, thu_t, lai_t, st_t = cal_pnl(list_tinh_hoa)
    lai_r_str = f"{lai_r:+,.0f}" if lai_r != 0 else "0"
    lai_t_str = f"{lai_t:+,.0f}" if lai_t != 0 else "0"
    lines.append(
        "📉 [KỊCH BẢN 2] - BÓC TÁCH: SỐ KHUYẾT NHỊP (Không Rơi/Đảo từ T-1)"
    )
    if sl_r == 0:
      lines.append(
          " 👉 KẾT QUẢ: 100% Danh mục duy trì động lượng tốt (Không có mã"
          " khuyết nhịp)\n"
      )
    else:
      lines.append(
          f" • Danh mục {sl_r} mã: " + " ".join([f"{x:02d}" for x in list_rac])
      )
      lines.append(
          f" • Đạt {nhay_r} lượt.  Vốn đầu tư: {chi_r:,.0f}đ  | Doanh thu:"
          f" {thu_r:,.0f}đ"
      )
      lines.append(
          f" 👉 HIỆU QUẢ CỦA MÃ KHUYẾT: {lai_r_str} VNĐ ({st_r})\n"
      )
    lines.append(
        "💎 [KỊCH BẢN 3] - BÓC TÁCH: SỐ TINH HOA (Động lượng Rơi/Đảo từ T-1)"
    )
    if sl_t == 0:
      lines.append(
          " 👉 KẾT QUẢ: KHÔNG CÓ MÃ ĐẠT CHUẨN (Toàn bộ danh mục mất động"
          " lượng)\n"
      )
    else:
      lines.append(
          f" • Danh mục {sl_t} mã: "
          + " ".join([f"{x:02d}" for x in list_tinh_hoa])
      )
      lines.append(
          f" • Đạt {nhay_t} lượt.  Vốn đầu tư: {chi_t:,.0f}đ  | Doanh thu:"
          f" {thu_t:,.0f}đ"
      )
      lines.append(f" 👉 LỢI NHUẬN RÒNG: {lai_t_str} VNĐ ({st_t})\n")
    lines.append(
        "========================================================================"
    )
    lines.append("💡 KẾT LUẬN KIỂM TOÁN CHUYÊN SÂU:")
    if sl_r == 0:
      lines.append(
          " -> Đánh giá: Danh mục cấu trúc vững chắc, 100% các mã số duy trì"
          " xu hướng tích cực."
      )
    elif lai_r < 0:
      lines.append(
          f" -> Phân tích: Các mã khuyết nhịp đã làm suy giảm {-lai_r:,.0f} VNĐ"
          " lợi nhuận. Chiến lược TINH HOA là phương án bảo toàn vốn tối ưu."
      )
    elif lai_r > 0:
      lines.append(
          " -> Lưu ý rủi ro: Nhóm số khuyết nhịp tạo ra lợi nhuận bất thường"
          f" {lai_r:,.0f} VNĐ. Thị trường đang có biến động ngoài dự kiến."
      )
    return "\n".join(lines)
  except Exception as e:
    return f"🛑 LỖI PHÂN HỆ 4: {e}"


def web_phan_he_5_monthly_audit(month, year, pts_per_code_base, mode):
  try:
    db, _ = doc_database_tu_excel()
    valid_m, err_m = check_valid_number(month, "Tháng")
    valid_y, err_y = check_valid_number(year, "Năm")
    valid_p, err_p = check_valid_number(pts_per_code_base, "Khối lượng vốn")
    if not valid_m:
      return err_m
    if not valid_y:
      return err_y
    if not valid_p:
      return err_p
    thang = safe_int(month)
    nam = safe_int(year)
    base_pts = safe_int(pts_per_code_base)
    if not (1 <= thang <= 12):
      return '🛑 LỖI THÔNG SỐ: Giá trị "Tháng" phải nằm trong khoảng từ 1 đến 12.'
    min_dt, max_dt, _ = lay_ngay_chot_tu_excel(db)
    start_dt = datetime(nam, thang, 1)
    end_dt = datetime(nam, thang, lay_max_days(thang, nam))
    if start_dt < min_dt:
      start_dt = min_dt
    if end_dt > max_dt:
      end_dt = max_dt
    if start_dt > end_dt:
      return f"🛑 BÁO CÁO: Kỳ kế toán {thang:02d}/{nam} hoàn toàn trống dữ liệu."
    lines = [
        "📑 [PHÂN HỆ 5] BÁO CÁO: TỔNG HỢP HIỆU SUẤT THEO THÁNG",
        "===================================================================================================================",
        f"📊 KỲ BÁO CÁO: {thang:02d}/{nam} - CHIẾN LƯỢC ĐẦU TƯ: {mode}",
        "-------------------------------------------------------------------------------------------------------------------",
        (
            f"{'NGÀY G.DỊCH':<12} | {'TRẠNG THÁI':<15} | {'SỐ MÃ':<7} |"
            f" {'VỐN ĐẦU TƯ':<14} | {'LƯỢT':<5} | {'DOANH THU':<14} |"
            f" {'LỢI NHUẬN':<15} | {'LŨY KẾ':<12}"
        ),
        "-------------------------------------------------------------------------------------------------------------------",
    ]
    luy_ke_thang = 0
    cash_thu = 0
    cash_chi = 0
    total_phien_danh = 0
    curr = start_dt
    while curr <= end_dt:
      ngay_str = curr.strftime("%d/%m/%Y")
      if ngay_str not in db:
        lines.append(
            f"{ngay_str:<12} | {'⚠️ THIẾU DATA':<15} | {'-':<7} | {'-':<14} |"
            f" {'-':<5} | {'-':<14} | {'-':<15} | {luy_ke_thang:>+12,.0f}"
        )
        curr += timedelta(days=1)
        continue
      dan, msg = get_signal_v36(curr, db, mode)
      if dan is None:
        lines.append(
            f"{ngay_str:<12} | {'🔭 THEO DÕI':<15} | {'0':<7} | {'-':<14} |"
            f" {'-':<5} | {'-':<14} | {msg:<15} | {luy_ke_thang:>+12,.0f}"
        )
        curr += timedelta(days=1)
        continue
      if len(dan) == 0:
        lines.append(
            f"{ngay_str:<12} | {'🔭 THEO DÕI':<15} | {'0':<7} | {'-':<14} |"
            f" {'-':<5} | {'-':<14} | {'[KHÔNG TÍN HIỆU]':<15} |"
            f" {luy_ke_thang:>+12,.0f}"
        )
        curr += timedelta(days=1)
        continue
      total_phien_danh += 1
      so_luong_lo = len(dan)
      von_1_phien = so_luong_lo * base_pts * COST_PER_POINT
      lo_to_27 = db[ngay_str]["prizes_int"]
      nhay = sum(lo_to_27.count(x) for x in dan)
      thuong = nhay * base_pts * WIN_PER_NHAY
      lai = thuong - von_1_phien
      luy_ke_thang += lai
      cash_chi += von_1_phien
      cash_thu += thuong
      status_str = "🟢 WIN" if lai > 0 else "🔴 LOSS"
      lines.append(
          f"{ngay_str:<12} | {status_str:<15} | {so_luong_lo:<7} |"
          f" {von_1_phien:<14,.0f} | {nhay:<5} | {thuong:<14,.0f} |"
          f" {lai:>+15,.0f} | {luy_ke_thang:>+12,.0f}"
      )
      curr += timedelta(days=1)
    roi = (luy_ke_thang / cash_chi * 100) if cash_chi > 0 else 0
    lines.append(
        "==================================================================================================================="
    )
    lines.append(f"📝 ĐỐI SOÁT KẾ TOÁN: {total_phien_danh} PHIÊN CÓ XUẤT LỆNH")
    lines.append(
        f"• TỔNG DÒNG TIỀN (CASH FLOW): Giải ngân {cash_chi:,.0f} đ | Thu về"
        f" {cash_thu:,.0f} đ"
    )
    lines.append(
        f"• LỢI NHUẬN RÒNG & BIÊN R.O.I: {luy_ke_thang:+,.0f} VND ({roi:+.2f} %)"
    )
    return "\n".join(lines)
  except Exception as e:
    return f"🛑 LỖI PHÂN HỆ 5: {e}"


def web_phan_he_6_range_performance(
    tu_ngay_raw, den_ngay_raw, pts_per_code_base, mode
):
  try:
    db, _ = doc_database_tu_excel()
    res1, res2 = chuan_hoa_ngay(tu_ngay_raw), chuan_hoa_ngay(den_ngay_raw)
    if not res1 or not res2:
      return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
    start_dt, end_dt = min(res1[0], res2[0]), max(res1[0], res2[0])
    valid, err = check_valid_number(pts_per_code_base, "Khối lượng vốn")
    if not valid:
      return err
    base_pts = safe_int(pts_per_code_base)
    min_dt, max_dt, _ = lay_ngay_chot_tu_excel(db)
    if start_dt < min_dt:
      start_dt = min_dt
    if end_dt > max_dt:
      end_dt = max_dt
    if start_dt > end_dt:
      return (
          "🛑 LỖI TRUY XUẤT: Khoảng thời gian tra cứu nằm ngoài Phạm vi Dữ liệu"
          " hệ thống."
      )
    lines = [
        "📑 [PHÂN HỆ 6] BÁO CÁO: ĐẠI KẾ TOÁN QUÉT CHU KỲ & DIỄN BIẾN LỢI NHUẬN",
        "===================================================================================================================",
        (
            f"📈 KẾT QUẢ TỪ {start_dt.strftime('%d/%m/%Y')} ĐẾN"
            f" {end_dt.strftime('%d/%m/%Y')} (CHIẾN LƯỢC: {mode})"
        ),
        "===================================================================================================================\n",
    ]
    curr = start_dt
    daily_records = []
    while curr <= end_dt:
      ngay_str = curr.strftime("%d/%m/%Y")
      if ngay_str in db:
        dan, msg = get_signal_v36(curr, db, mode)
        if dan is not None and len(dan) > 0:
          so_luong_lo = len(dan)
          von_1_phien = so_luong_lo * base_pts * COST_PER_POINT
          lo_to_27 = db[ngay_str]["prizes_int"]
          nhay = sum(lo_to_27.count(x) for x in dan)
          thuong = nhay * base_pts * WIN_PER_NHAY
          lai = thuong - von_1_phien
          daily_records.append({
              "dt": curr,
              "year": curr.year,
              "month_str": curr.strftime("%m/%Y"),
              "date_str": ngay_str,
              "codes": so_luong_lo,
              "chi": von_1_phien,
              "nhay": nhay,
              "thu": thuong,
              "lai": lai,
              "win": 1 if lai > 0 else 0,
              "loss": 1 if lai <= 0 else 0,
          })
      curr += timedelta(days=1)
    if not daily_records:
      return (
          "\n".join(lines)
          + "🛑 KHÔNG CÓ PHIÊN GIAO DỊCH NÀO ĐẠT ĐIỀU KIỆN XUẤT LỆNH THỰC TẾ."
      )
    df_rec = pd.DataFrame(daily_records)
    lines.append(
        "📊 1. BẢNG TỔNG HỢP DIỄN BIẾN THEO NĂM (YEARLY PNL BREAKDOWN)"
    )
    lines.append(
        "-------------------------------------------------------------------------------------------------------------------"
    )
    lines.append(
        f"{'NĂM':<10} | {'PHIÊN':<7} | {'SỐ MÃ':<8} | {'VỐN ĐẦU TƯ':<14} |"
        f" {'DOANH THU':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI (%)':<8}"
    )
    lines.append(
        "-------------------------------------------------------------------------------------------------------------------"
    )
    for year, g_y in df_rec.groupby("year"):
      p_chi = g_y["chi"].sum()
      p_thu = g_y["thu"].sum()
      p_lai = g_y["lai"].sum()
      p_roi = (p_lai / p_chi * 100) if p_chi > 0 else 0
      lines.append(
          f"Năm {year:<6} | {len(g_y):<7} | {g_y['codes'].sum():<8} |"
          f" {p_chi:<14,.0f} | {p_thu:<14,.0f} | {p_lai:>+16,.0f} |"
          f" {p_roi:>+7.2f}%"
      )
    lines.append(
        "\n📊 2. BẢNG TỔNG HỢP DIỄN BIẾN THEO THÁNG (MONTHLY PNL BREAKDOWN)"
    )
    lines.append(
        "-------------------------------------------------------------------------------------------------------------------"
    )
    lines.append(
        f"{'THÁNG/NĂM':<10} | {'PHIÊN':<7} | {'WIN/LOSS':<10} | {'VỐN"
        f" ĐẦU TƯ':<14} | {'DOANH THU':<14} | {'LỢI NHUẬN RÒNG':<16} | {'ROI"
        f" (%)':<8}"
    )
    lines.append(
        "-------------------------------------------------------------------------------------------------------------------"
    )
    for m_str, g_m in df_rec.groupby("month_str", sort=False):
      m_chi = g_m["chi"].sum()
      m_thu = g_m["thu"].sum()
      m_lai = g_m["lai"].sum()
      m_roi = (m_lai / m_chi * 100) if m_chi > 0 else 0
      w_cnt = g_m["win"].sum()
      l_cnt = g_m["loss"].sum()
      wl_str = f"{w_cnt}W/{l_cnt}L"
      lines.append(
          f"Tháng {m_str:<5} | {len(g_m):<7} | {wl_str:<10} | {m_chi:<14,.0f} |"
          f" {m_thu:<14,.0f} | {m_lai:>+16,.0f} | {m_roi:>+7.2f}%"
      )
    tot_chi = df_rec["chi"].sum()
    tot_thu = df_rec["thu"].sum()
    tot_lai = df_rec["lai"].sum()
    tot_roi = (tot_lai / tot_chi * 100) if tot_chi > 0 else 0
    tot_win = df_rec["win"].sum()
    tot_loss = df_rec["loss"].sum()
    lines.append(
        "==================================================================================================================="
    )
    lines.append(
        f"📝 ĐẠI KẾ TOÁN TỔNG CỘNG ({len(df_rec)} PHIÊN CÓ XUẤT LỆNH | Win:"
        f" {tot_win} - Loss: {tot_loss}):"
    )
    lines.append(f"• TỔNG VỐN ĐẦU TƯ  : {tot_chi:,.0f} VNĐ")
    lines.append(f"• TỔNG DOANH THU    : {tot_thu:,.0f} VNĐ")
    lines.append(f"• LỢI NHUẬN RÒNG    : {tot_lai:+,.0f} VNĐ")
    lines.append(f"• TỶ LỆ ROI TOÀN KHUNG: {tot_roi:+.2f} %")
    lines.append(
        "==================================================================================================================="
    )
    return "\n".join(lines)
  except Exception as e:
    return f"🛑 LỖI PHÂN HỆ 6: {e}"


def web_phan_he_7_raw_db_lookup(ngay_raw):
  try:
    db, _ = doc_database_tu_excel()
    res = chuan_hoa_ngay(ngay_raw)
    if not res:
      return "🛑 LỖI THÔNG SỐ: Định dạng ngày không hợp lệ."
    _, ngay_str = res
    if ngay_str not in db:
      return (
          f"🛑 DỮ LIỆU RỖNG: Phiên {ngay_str} chưa tồn tại trên hệ thống."
      )
    lo_to_raw = db[ngay_str]["prizes_int"]
    lo_to_formatted = [f"{x:02d}" for x in lo_to_raw]
    lines = [
        "📑 [PHÂN HỆ 7] BÁO CÁO: TRUY XUẤT RAW DB (DỮ LIỆU THÔ THỨ TỰ LỒNG CẦU)",
        "=======================================================\n",
        f"📅 BIÊN BẢN KẾT QUẢ PHIÊN GIAO DỊCH: {ngay_str}",
        "🎰 Danh sách 27 giải ma trận phẳng (Thứ tự mở thưởng):",
    ]
    grid_lines = []
    row_str = ""
    for idx, lo in enumerate(lo_to_formatted):
      row_str += f"[{lo}] "
      if (idx + 1) % 9 == 0:
        grid_lines.append(row_str.strip())
        row_str = ""
    lines.extend(grid_lines)
    return "\n".join(lines)
  except Exception as e:
    return f"🛑 LỖI PHÂN HỆ 7: {e}"


db_init, _ = doc_database_tu_excel()
_, latest_dt_init, next_predict_dt_init = lay_ngay_chot_tu_excel(db_init)

MENU_OPTIONS = [
    "🔄 1. ĐỒNG BỘ DỮ LIỆU",
    "🎯 2. KHUYẾN NGHỊ LỆNH",
    "🛡️ 3. QUẢN TRỊ RỦI RO",
    "🔍 4. KIỂM TOÁN ĐƠN PHIÊN",
    "📊 5. BÁO CÁO THÁNG",
    "📈 6. PHÂN TÍCH CHU KỲ",
    "🎰 7. DỮ LIỆU THÔ",
]

with gr.Blocks(title="XSMB QUANT V36.1.0 PRO") as demo:
  gr.Markdown(
      "# 🚀 XSMB QUANT V36.1.0 — PHIÊN BẢN THƯƠNG MẠI (TÍCH HỢP HOÀN CHỈNH)"
  )
  gr.Markdown(
      "*(Hệ thống Phân tích Định lượng & Quản trị Rủi ro. Đã tối ưu hóa và sửa"
      " lỗi toàn diện.)*"
  )
  with gr.Row():
    nav_menu = gr.Radio(
        choices=MENU_OPTIONS,
        value=MENU_OPTIONS[0],
        label="🎛️ BẢNG ĐIỀU KHIỂN CHÍNH (Vui lòng chọn chức năng)",
    )
  with gr.Column(visible=True) as col_1:
    btn_1 = gr.Button(
        "⚡ KHỞI CHẠY KIỂM TOÁN VÀ ĐỒNG BỘ DỮ LIỆU", variant="primary"
    )
    out_1 = gr.Textbox(label="Biên bản Hệ thống", lines=7)
  with gr.Column(visible=False) as col_2:
    title_2 = gr.Markdown(
        "#### Dự phóng Tín hiệu cho phiên giao dịch kế tiếp:"
        f" {next_predict_dt_init.strftime('%d/%m/%Y')}"
    )
    with gr.Row():
      pts_2 = gr.Number(label="Khối lượng Vốn Cơ sở (Điểm / Mã)", value=10)
      mode_2 = gr.Radio(
          choices=MODES,
          value="Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
          label="Chiến lược Áp dụng",
      )
    btn_2 = gr.Button("🔍 XUẤT KHUYẾN NGHỊ GIAO DỊCH", variant="primary")
    out_2 = gr.Textbox(label="Hồ sơ Giao dịch V36.1.0", lines=16)
    btn_2.click(web_phan_he_2_predict, inputs=[pts_2, mode_2], outputs=out_2)
  with gr.Column(visible=False) as col_3:
    with gr.Row():
      pts_3 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
      sim_size = gr.Number(label="Quy mô Danh mục (Số lượng mã)", value=12)
    btn_3 = gr.Button("🧪 KHỞI CHẠY MÔ PHỎNG LỢI NHUẬN", variant="primary")
    out_3 = gr.Textbox(label="Báo cáo Quản trị Biên độ Rủi ro", lines=16)
    btn_3.click(web_phan_he_3_risk_audit, inputs=[pts_3, sim_size], outputs=out_3)
  with gr.Column(visible=False) as col_4:
    with gr.Row():
      date_4 = gr.Textbox(
          label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)",
          value=latest_dt_init.strftime("%d/%m/%Y"),
      )
      pts_4 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
    btn_4 = gr.Button("📡 KIỂM TOÁN HIỆU SUẤT ĐƠN PHIÊN", variant="primary")
    out_4 = gr.Textbox(label="Báo cáo Bóc tách Động lượng", lines=24)
    btn_4.click(
        web_phan_he_4_single_day_backtest, inputs=[date_4, pts_4], outputs=out_4
    )
  with gr.Column(visible=False) as col_5:
    with gr.Row():
      m_5 = gr.Number(
          label="Kỳ Báo cáo (Tháng 1-12)", value=latest_dt_init.month
      )
      y_5 = gr.Number(label="Năm Tài chính", value=latest_dt_init.year)
      pts_5 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
      mode_5 = gr.Radio(
          choices=MODES,
          value="Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
          label="Chiến lược Áp dụng",
      )
    btn_5 = gr.Button("📊 TRUY XUẤT BÁO CÁO THÁNG", variant="primary")
    out_5 = gr.Textbox(label="Sổ Cái Kế Toán", lines=22)
    btn_5.click(
        web_phan_he_5_monthly_audit,
        inputs=[m_5, y_5, pts_5, mode_5],
        outputs=out_5,
    )
  with gr.Column(visible=False) as col_6:
    with gr.Row():
      t1_6 = gr.Textbox(label="Từ ngày (DD/MM/YYYY)", value="01/01/2026")
      t2_6 = gr.Textbox(
          label="Đến ngày (DD/MM/YYYY)",
          value=latest_dt_init.strftime("%d/%m/%Y"),
      )
      pts_6 = gr.Number(label="Khối lượng Vốn (Điểm / Mã)", value=10)
      mode_6 = gr.Radio(
          choices=MODES,
          value="Chỉ Giao Dịch TINH HOA (Lọc Số Khuyết)",
          label="Chiến lược Áp dụng",
      )
    btn_6 = gr.Button(
        "📈 KIỂM TOÁN BIÊN ĐỘ LỢI NHUẬN CHU KỲ", variant="primary"
    )
    out_6 = gr.Textbox(label="Báo cáo Tổng Dòng Tiền", lines=22)
    btn_6.click(
        web_phan_he_6_range_performance,
        inputs=[t1_6, t2_6, pts_6, mode_6],
        outputs=out_6,
    )
  with gr.Column(visible=False) as col_7:
    date_7 = gr.Textbox(
        label="Phiên Giao dịch Truy xuất (DD/MM/YYYY)",
        value=latest_dt_init.strftime("%d/%m/%Y"),
    )
    btn_7 = gr.Button("💾 TRUY XUẤT DỮ LIỆU THÔ (RAW DATA)", variant="primary")
    out_7 = gr.Textbox(label="Log Dữ Liệu Máy Chủ", lines=10)
    btn_7.click(web_phan_he_7_raw_db_lookup, inputs=date_7, outputs=out_7)
  btn_1.click(web_phan_he_1_sync, outputs=[out_1, title_2])

  def update_visibility(choice):
    return [
        gr.update(visible=(choice == MENU_OPTIONS[0])),
        gr.update(visible=(choice == MENU_OPTIONS[1])),
        gr.update(visible=(choice == MENU_OPTIONS[2])),
        gr.update(visible=(choice == MENU_OPTIONS[3])),
        gr.update(visible=(choice == MENU_OPTIONS[4])),
        gr.update(visible=(choice == MENU_OPTIONS[5])),
        gr.update(visible=(choice == MENU_OPTIONS[6])),
    ]

  nav_menu.change(
      fn=update_visibility,
      inputs=[nav_menu],
      outputs=[col_1, col_2, col_3, col_4, col_5, col_6, col_7],
  )

if __name__ == "__main__":
  port = int(os.environ.get("PORT", 10000))
  demo.launch(
      server_name="0.0.0.0", server_port=port, share=False, theme=gr.themes.Soft()
  )
