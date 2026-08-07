import os
import sys
import pandas as pd
import numpy as np
import glob
import io
import requests
from datetime import datetime, timedelta
import traceback
import gradio as gr

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG MASTER QUANT ENGINE
# ==============================================================================
class Config:
    VERSION = "V7.1 MASTER QUANT ENGINE (PANEL DATABASE & GMT+7 AUTO-APPEND)" 
    MASTER_DB_FILE = "Master_Stock_Database.xlsx"
    ACTIVE_MODE = "🤖 [VERSION 7.1] PRO QUANT ENGINE (SINGLE MASTER DATABASE & 7 SENSORS)"

class Utils:
    @staticmethod
    def get_vn_time():
        # Ép chuẩn múi giờ GMT+7 Việt Nam tuyệt đối dù Server đặt ở Mỹ/Sing
        return datetime.utcnow() + timedelta(hours=7)

# ==============================================================================
# 📈 BLOCK 2: CHỨNG KHOÁN QUANT ENGINE (CÀO GỘP & CẬP NHẬT LŨY TIẾN)
# ==============================================================================
class StockQuantEngine:
    @staticmethod
    def fetch_stock_data(ticker, days=180):
        # 1. THỬ DNSE ENTRADE OPEN API (Mở rộng cho Cloud)
        try:
            end_date = Utils.get_vn_time()
            start_date = end_date - timedelta(days=days + 60)
            from_ts = int(start_date.timestamp())
            to_ts = int(end_date.timestamp())
            
            url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ticker.upper()}&from={from_ts}&to={to_ts}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
            if res.status_code == 200:
                data = res.json()
                if 't' in data and len(data['t']) >= 20:
                    df = pd.DataFrame({
                        'Ticker': ticker.upper(),
                        'timestamp': data['t'],
                        'Open': data['o'],
                        'High': data['h'],
                        'Low': data['l'],
                        'Close': data['c'],
                        'Volume': data['v']
                    })
                    df['Date'] = (pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)).dt.strftime('%d/%m/%Y')
                    return df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna().reset_index(drop=True), "DNSE API"
        except Exception:
            pass

        # 2. THỬ YAHOO FINANCE GLOBAL (Fallback)
        try:
            yf_ticker = f"{ticker.upper()}.VN"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}?range=1y&interval=1d"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
            if res.status_code == 200:
                data = res.json()
                if data.get('chart', {}).get('result'):
                    result = data['chart']['result'][0]
                    timestamps = result['timestamp']
                    quote = result['indicators']['quote'][0]
                    df = pd.DataFrame({
                        'Ticker': ticker.upper(),
                        'timestamp': timestamps,
                        'Open': quote['open'],
                        'High': quote['high'],
                        'Low': quote['low'],
                        'Close': quote['close'],
                        'Volume': quote['volume']
                    }).dropna()
                    df['Date'] = (pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)).dt.strftime('%d/%m/%Y')
                    return df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True), "Yahoo API"
        except Exception:
            pass
            
        return None, "🛑 LỖI API"

    @staticmethod
    def run_ultra_7_sensors(df):
        if len(df) < 20: return None
        
        df = df.copy()
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)

        # 1. SMART MONEY (VOL RATIO)
        df['MA20_Vol'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['MA20_Vol']

        # 2. MFI (MONEY FLOW INDEX 14)
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        raw_mf = tp * df['Volume']
        pos_mf = np.where(tp > tp.shift(1), raw_mf, 0)
        neg_mf = np.where(tp < tp.shift(1), raw_mf, 0)
        mfi_14 = 100 - (100 / (1 + (pd.Series(pos_mf).rolling(14).sum() / pd.Series(neg_mf).rolling(14).sum().replace(0, np.nan))))
        df['MFI'] = mfi_14

        # 3. Z-SCORE MEAN REVERSION
        df['MA20_Price'] = df['Close'].rolling(20).mean()
        df['Std20_Price'] = df['Close'].rolling(20).std()
        df['Z_Score'] = (df['Close'] - df['MA20_Price']) / df['Std20_Price']

        # 4. RSI 14
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))

        # 5. MACD (12, 26, 9)
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # 6. BOLLINGER BANDS SQUEEZE
        df['BB_Upper'] = df['MA20_Price'] + 2 * df['Std20_Price']
        df['BB_Lower'] = df['MA20_Price'] - 2 * df['Std20_Price']
        df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['MA20_Price']

        # 7. EMA DYNAMIC TREND & ATR 14
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = tr.rolling(14).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        score = 50.0
        signals = []

        if latest['Vol_Ratio'] > 2.0 and latest['Close'] > prev['Close']:
            score += 20; signals.append("🟢 Smart Money Nổ Vol")
        elif latest['Vol_Ratio'] > 2.0 and latest['Close'] < prev['Close']:
            score -= 15; signals.append("🔴 Bán Tháo Xả Vol")

        if latest['Z_Score'] < -2.0:
            score += 25; signals.append("🟣 Bắt Đáy Z-Score (< -2.0)")
        elif latest['Z_Score'] > 2.0:
            score -= 20; signals.append("🔴 Quá Mua Z-Score (> +2.0)")

        if latest['MFI'] > 70: signals.append("🟢 Tiền Vào Mạnh (MFI > 70)")
        elif latest['MFI'] < 30: score += 10; signals.append("🟣 Vùng Đáy Tiền Cạn (MFI < 30)")

        if prev['MACD_Hist'] < 0 and latest['MACD_Hist'] > 0:
            score += 15; signals.append("🟢 MACD Cắt Lên")

        if latest['BB_Width'] < df['BB_Width'].rolling(40).mean().iloc[-1] * 0.8:
            score += 10; signals.append("🟢 BB Thắt Cổ Chai")

        if latest['Close'] > latest['EMA50'] and latest['EMA50'] > latest['EMA200']:
            score += 10; signals.append("🟢 Cấu Trúc Uptrend")

        final_score = min(100, max(0, score))
        atr_val = latest['ATR'] if pd.notna(latest['ATR']) else latest['Close'] * 0.03
        entry_price = latest['Close']

        if final_score >= 80: kelly_alloc = "35% - 40% NAV"
        elif final_score >= 65: kelly_alloc = "20% - 25% NAV"
        elif final_score >= 50: kelly_alloc = "10% - 15% NAV"
        else: kelly_alloc = "0% (Đứng Ngoài)"

        return {
            'Date': latest['Date'], 'Close': entry_price, 'Volume': latest['Volume'],
            'Z_Score': latest['Z_Score'], 'Vol_Ratio': latest['Vol_Ratio'],
            'RSI': latest['RSI'], 'MFI': latest['MFI'], 'ATR': atr_val,
            'Score': final_score, 'Signals': " | ".join(signals) if signals else "Tích lũy bình thường",
            'SL': entry_price - (1.5 * atr_val), 'TP': entry_price + (3.0 * atr_val), 'Kelly': kelly_alloc
        }

    # ==============================================================================
    # 🗄️ QUẢN LÝ DATABASE MASTER GỘP TẤT CẢ CÁC MÃ (MASTER_STOCK_DATABASE.XLSX)
    # ==============================================================================
    @staticmethod
    def create_or_update_master_db(raw_ticker_list, days_history=180):
        tickers = [t.strip().upper() for t in raw_ticker_list.replace(',', ' ').split() if t.strip()]
        if not tickers: return "🛑 Nhập ít nhất 1 mã cổ phiếu.", gr.update(visible=False)

        master_file = Config.MASTER_DB_FILE
        existing_df = pd.DataFrame()
        
        if os.path.exists(master_file):
            try:
                existing_df = pd.read_excel(master_file)
            except Exception: pass

        new_dfs = []
        log_msgs = []

        for t in tickers:
            df_new, src = StockQuantEngine.fetch_stock_data(t, days_history)
            if df_new is not None and not df_new.empty:
                new_dfs.append(df_new)
                log_msgs.append(f"✅ {t}: Lấy {len(df_new)} phiên từ {src}")
            else:
                log_msgs.append(f"❌ {t}: Lỗi kết nối API")

        if not new_dfs:
            return "🛑 KHÔNG LẤY ĐƯỢC DỮ LIỆU MÃ NÀO.\n" + "\n".join(log_msgs), gr.update(visible=False)

        combined_new = pd.concat(new_dfs, ignore_index=True)

        if not existing_df.empty:
            # Gộp dữ liệu cũ và mới, xóa bỏ trùng lặp dựa trên [Ticker, Date]
            final_df = pd.concat([existing_df, combined_new], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
        else:
            final_df = combined_new

        # Sắp xếp lại dữ liệu cho chuẩn hóa
        final_df['dt_temp'] = pd.to_datetime(final_df['Date'], format='%d/%m/%Y')
        final_df = final_df.sort_values(by=['Ticker', 'dt_temp'], ascending=[True, True]).drop(columns=['dt_temp'])

        final_df.to_excel(master_file, index=False)

        unique_tickers = final_df['Ticker'].unique().tolist()
        summary = (
            f"📑 BÁO CÁO BƠM DỮ LIỆU VÀO MASTER DATABASE SERVER\n"
            f"=========================================================\n"
            f"⏱️ Múi giờ thực thi (GMT+7) : {Utils.get_vn_time().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"💾 File Database Tổng       : {master_file}\n"
            f"📊 Tổng số dòng dữ liệu      : {len(final_df):,} dòng\n"
            f"📌 Danh mục mã đang lưu     : {', '.join(unique_tickers)}\n"
            f"=========================================================\n"
            f"CHI TIẾT TIẾN TRÌNH CÀO:\n" + "\n".join(log_msgs)
        )

        return summary, gr.update(value=master_file, visible=True)

    @staticmethod
    def run_omni_radar_scanner():
        master_file = Config.MASTER_DB_FILE
        if not os.path.exists(master_file):
            return "🛑 CHƯA CÓ MASTER DATABASE TRÊN SERVER. Vui lòng sang Tab 3 bấm khởi tạo Database trước."

        try:
            full_df = pd.read_excel(master_file)
            if full_df.empty or 'Ticker' not in full_df.columns:
                return "🛑 FILE MASTER DATABASE RỖNG HOẶC SAI CẤU TRÚC."

            tickers = full_df['Ticker'].unique().tolist()
            results = []

            for t in tickers:
                df_t = full_df[full_df['Ticker'] == t].copy()
                df_t['dt_temp'] = pd.to_datetime(df_t['Date'], format='%d/%m/%Y')
                df_t = df_t.sort_values('dt_temp').reset_index(drop=True)
                
                if len(df_t) >= 20:
                    m = StockQuantEngine.run_ultra_7_sensors(df_t)
                    if m:
                        results.append({
                            'Mã': t, 'Giá': m['Close'], 'Z-Score': m['Z_Score'],
                            'Vol Ratio': m['Vol_Ratio'], 'MFI': m['MFI'], 'RSI': m['RSI'],
                            'Điểm Quant': m['Score'], 'Tín Hiệu': m['Signals'],
                            'SL': m['SL'], 'TP': m['TP'], 'Kelly': m['Kelly'], 'Date': m['Date']
                        })

            if not results: return "🛑 KHÔNG ĐỦ DỮ LIỆU PHÂN TÍCH (Cần ít nhất 20 phiên/mã)."

            res_df = pd.DataFrame(results).sort_values(by='Điểm Quant', ascending=False).reset_index(drop=True)

            lines = [
                "📑 BÁO CÁO QUÉT SIÊU CẢM BIẾN TỪ MASTER DATABASE (OMNI-QUANT RADAR)",
                "======================================================================================================",
                f"⏱️ Thời gian quét (GMT+7 Hà Nội) : {Utils.get_vn_time().strftime('%d/%m/%Y %H:%M:%S')}",
                f"🎯 Danh mục đã quét             : {len(results)} mã từ File Master Database",
                "======================================================================================================",
                f"{'TOP':<3} | {'MÃ':<5} | {'GIÁ (k)':<8} | {'Z-SCORE':<8} | {'VOL RATIO':<9} | {'MFI':<5} | {'RSI':<5} | {'ĐIỂM':<5} | TÍN HIỆU CẢM BIẾN KÍCH HOẠT",
                "------------------------------------------------------------------------------------------------------"
            ]

            for idx, r in res_df.iterrows():
                lines.append(
                    f"#{idx+1:<2} | {r['Mã']:<5} | {r['Giá']/1000:>8,.1f} | {r['Z-Score']:>+8.2f} | x{r['Vol Ratio']:>7.2f} | {r['MFI']:>5.1f} | {r['RSI']:>5.1f} | {r['Điểm Quant']:>5.0f} | {r['Tín Hiệu']}"
                )

            top1 = res_df.iloc[0]
            lines.extend([
                "======================================================================================================",
                f"🚀 KHUYẾN NGHỊ LỆNH TÁC CHIẾN TỐI ƯU NHẤT: MÃ [{top1['Mã']}] (ĐIỂM QUANT: {top1['Điểm Quant']:.0f}/100)",
                "------------------------------------------------------------------------------------------------------",
                f" • 💵 Vùng Giá Mua Giải Ngân : {top1['Giá']:,.0f} VNĐ (Phiên {top1['Date']})",
                f" • 🎯 Mục Tiêu Chốt Lời (TP)  : {top1['TP']:,.0f} VNĐ (+{((top1['TP']-top1['Giá'])/top1['Giá']*100):.1f}%)",
                f" • 🛡️ Cắt Lỗ Tự Động (SL)    : {top1['SL']:,.0f} VNĐ (-{((top1['Giá']-top1['SL'])/top1['Giá']*100):.1f}%)",
                f" • 💰 Phân Bổ Vốn Kelly     : {top1['Kelly']}",
                "======================================================================================================"
            ])

            return "\n".join(lines)
        except Exception as e:
            return f"🛑 LỖI ĐỌC MASTER DATABASE: {str(e)}"

# ==============================================================================
# 🎨 UI & DASHBOARD LAUNCHER
# ==============================================================================
def create_ui():
    with gr.Blocks(title="STOCK QUANT ENGINE V7.1", theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 PRO STOCK QUANT ENGINE {Config.VERSION}")
        gr.Markdown(f"**Trạng thái Múi Giờ:** GMT+7 (Hà Nội) | **Chế độ:** Master Panel Database Lũy Tiến")

        with gr.Tabs():
            # TAB 1: OMNI QUANT RADAR QUÉT TỪ MASTER DB
            with gr.TabItem("🔥 1. OMNI QUANT RADAR (Quét Cảm Biến Danh Mục Master DB)"):
                gr.Markdown("### 📡 CHẠY 7 SIÊU CẢM BIẾN TRÊN TOÀN BỘ MASTER DATABASE")
                gr.Markdown("Bấm nút để quét toàn bộ các mã đang lưu trong file Database tổng (`Master_Stock_Database.xlsx`), phân tích 7 Cảm Biến và xuất Bảng Lệnh Tác Chiến.")
                
                btn_run_omni_radar = gr.Button("🚀 CHẠY SIÊU CẢM BIẾN QUÉT MASTER DATABASE", variant="primary")
                out_omni_report = gr.Textbox(label="Báo Cáo Siêu Phân Tích Quant & Lệnh Tác Chiến Tối Ưu", lines=20)
                
                btn_run_omni_radar.click(
                    StockQuantEngine.run_omni_radar_scanner,
                    inputs=[],
                    outputs=[out_omni_report]
                )

            # TAB 2: QUẢN LÝ MASTER DATABASE FILE
            with gr.TabItem("📊 2. XEM & TẢI MASTER DATABASE SERVER"):
                gr.Markdown("### 💾 QUẢN LÝ TỆP DATABASE TỔNG (`Master_Stock_Database.xlsx`)")
                gr.Markdown("File này chứa toàn bộ dữ liệu giá & khối lượng gộp của tất cả các mã mục tiêu mày đã cào.")
                
                btn_check_db = gr.Button("🔍 KIỂM TRA & XUẤT FILE MASTER DATABASE", variant="primary")
                out_db_info = gr.Textbox(label="Thông Tin Master Database Hiện Tại", lines=10)
                dl_master_file = gr.DownloadButton("📥 BẤM VÀO ĐÂY ĐỂ TẢI MASTER DATABASE (.XLSX)", variant="primary", visible=False)
                
                def check_master():
                    f = Config.MASTER_DB_FILE
                    if os.path.exists(f):
                        df = pd.read_excel(f)
                        ticks = df['Ticker'].unique().tolist() if 'Ticker' in df.columns else []
                        return f"✅ Master DB tồn tại ({len(df):,} dòng).\n📌 Danh mục mã: {', '.join(ticks)}", gr.update(value=f, visible=True)
                    return "🛑 Chưa có file Master DB.", gr.update(visible=False)

                btn_check_db.click(check_master, inputs=[], outputs=[out_db_info, dl_master_file])

            # TAB 3: TRẠM BƠM VÀ CẬP NHẬT DỮ LIỆU LŨY TIẾN HẰNG NGÀY
            with gr.TabItem("🌐 3. TRẠM BƠM & CẬP NHẬT DATABASE LŨY TIẾN"):
                gr.Markdown("### 🕸️ KẾT NỐI API -> NẠP LŨY TIẾN VÀO FILE MASTER DATABASE")
                gr.Markdown("**Hướng dẫn:** Nhập danh mục mã mục tiêu. Mỗi ngày sau 15:00 giờ VN, mày chỉ cần bấm nút, bot sẽ tự cào nến mới nhất và **BƠM NỐI ĐUÔI** vào file `Master_Stock_Database.xlsx`.")
                
                ticker_targets = gr.Textbox(
                    label="Danh sách Mã Cổ Phiếu Mụa Tiêu Cần Cào/Cập Nhật", 
                    value="SSI, HPG, TCB, FPT, DIG, MWG, VND, MBB, HSG, STB, VCI, VHM, NVL, PDR, VCB"
                )
                days_slider = gr.Slider(minimum=30, maximum=365, value=180, step=10, label="Số ngày cào lịch sử (Nếu tạo mới)")
                
                btn_update_db = gr.Button("🔄 CHẠY BƠM/CẬP NHẬT DỮ LIỆU VÀO MASTER DATABASE", variant="primary")
                out_pump_log = gr.Textbox(label="Nhật Ký Bơm Dữ Liệu Lũy Tiến", lines=15)
                dl_pump_file = gr.DownloadButton("📥 TẢI MASTER DATABASE MỚI NHẤT VỀ MÁY", variant="primary", visible=False)
                
                btn_update_db.click(
                    StockQuantEngine.create_or_update_master_db,
                    inputs=[ticker_targets, days_slider],
                    outputs=[out_pump_log, dl_pump_file]
                )

    return demo

if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, share=False)
