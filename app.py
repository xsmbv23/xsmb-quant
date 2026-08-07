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
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG V12 QUANT ENGINE
# ==============================================================================
class Config:
    VERSION = "V7.7 OMNI V12 BI-TURBO QUANT ENGINE (7 ADVANCED SENSORS)" 
    MASTER_DB_FILE = "Master_Stock_Database.xlsx"

class Utils:
    @staticmethod
    def get_vn_time():
        return datetime.utcnow() + timedelta(hours=7)

# ==============================================================================
# 📈 BLOCK 2: ĐỘNG CƠ V12 ADVANCED QUANT SENSORS
# ==============================================================================
class StockQuantEngine:
    @staticmethod
    def fetch_stock_data(ticker, days=180):
        # 1. THỬ DNSE ENTRADE OPEN API
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

        # 2. THỬ YAHOO FINANCE GLOBAL
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
    def run_v12_sensors(df):
        if len(df) < 25: return None
        
        df = df.copy()
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Open'] = df['Open'].astype(float)

        # ----------------------------------------------------------------------
        # CẢM BIẾN 1: CHAIKIN MONEY FLOW (CMF 20) - ĐO DÒNG TIỀN THẬT NẠP VÀO
        # ----------------------------------------------------------------------
        mf_multiplier = np.where((df['High'] - df['Low']) != 0, ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / (df['High'] - df['Low']), 0)
        mf_volume = mf_multiplier * df['Volume']
        df['CMF'] = mf_volume.rolling(20).sum() / df['Volume'].rolling(20).sum()

        # ----------------------------------------------------------------------
        # CẢM BIẾN 2: SMART MONEY VOLATILITY Z-SCORE
        # ----------------------------------------------------------------------
        df['MA20_Vol'] = df['Volume'].rolling(20).mean()
        df['Std20_Vol'] = df['Volume'].rolling(20).std()
        df['Vol_ZScore'] = (df['Volume'] - df['MA20_Vol']) / df['Std20_Vol']
        df['Vol_Ratio'] = df['Volume'] / df['MA20_Vol']

        # ----------------------------------------------------------------------
        # CẢM BIẾN 3: Z-SCORE PRICE MULTI-FRAME (MA20 & EMA50)
        # ----------------------------------------------------------------------
        df['MA20_Price'] = df['Close'].rolling(20).mean()
        df['Std20_Price'] = df['Close'].rolling(20).std()
        df['Z_Score_20'] = (df['Close'] - df['MA20_Price']) / df['Std20_Price']

        # ----------------------------------------------------------------------
        # CẢM BIẾN 4: STOCHASTIC RSI HYBRID (ĐỌC ĐIỂM ĐẢO CHIỀU TỪNG PHIÊN)
        # ----------------------------------------------------------------------
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))
        
        rsi_min = df['RSI'].rolling(14).min()
        rsi_max = df['RSI'].rolling(14).max()
        df['Stoch_RSI'] = np.where((rsi_max - rsi_min) != 0, (df['RSI'] - rsi_min) / (rsi_max - rsi_min), 0) * 100

        # ----------------------------------------------------------------------
        # CẢM BIẾN 5: ATR & KELTNER CHANNEL SQUEEZE (NÉN NĂNG LƯỢNG)
        # ----------------------------------------------------------------------
        tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = tr.rolling(14).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['KC_Upper'] = df['EMA20'] + (1.5 * df['ATR'])
        df['KC_Lower'] = df['EMA20'] - (1.5 * df['ATR'])
        df['BB_Upper'] = df['MA20_Price'] + (2.0 * df['Std20_Price'])
        df['BB_Lower'] = df['MA20_Price'] - (2.0 * df['Std20_Price'])
        
        # Squeeze = BB nằm hoàn toàn trong Keltner Channel
        df['KC_Squeeze'] = (df['BB_Upper'] < df['KC_Upper']) & (df['BB_Lower'] > df['KC_Lower'])

        # ----------------------------------------------------------------------
        # CẢM BIẾN 6: MACD HISTOGRAM VELOCITY (TỐC ĐỘ TĂNG TỐC ĐỘNG LƯỢNG)
        # ----------------------------------------------------------------------
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        df['Hist_Accel'] = df['MACD_Hist'] - df['MACD_Hist'].shift(1)

        # ----------------------------------------------------------------------
        # CẢM BIẾN 7: DYNAMIC EMA TREND (EMA50 vs EMA200)
        # ----------------------------------------------------------------------
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # ==============================================================================
        # 🧠 CHẤM ĐIỂM TỔNG HỢP LÕI V12 (0 - 100 ĐIỂM)
        # ==============================================================================
        score = 50.0
        signals = []

        # CMF Check (Cực kỳ quan trọng về Dòng tiền)
        if latest['CMF'] > 0.15:
            score += 20; signals.append("🔥 CMF Tiền Vào Cực Mạnh (>0.15)")
        elif latest['CMF'] < -0.15:
            score -= 20; signals.append("🔴 CMF Áp Lực Xả Hàng")

        # Smart Money Vol Z-Score Check
        if latest['Vol_ZScore'] > 2.0 and latest['Close'] > prev['Close']:
            score += 15; signals.append("🟢 Smart Money Gom Hàng (Vol Z > +2)")
        elif latest['Vol_ZScore'] > 2.0 and latest['Close'] < prev['Close']:
            score -= 15; signals.append("🔴 Cá Mập Xả Hàng (Vol Z > +2)")

        # Z-Score Price Check
        if latest['Z_Score_20'] < -2.0:
            score += 25; signals.append("🟣 Bắt Đáy Lệch Chuẩn Z-Score (< -2.0)")
        elif latest['Z_Score_20'] > 2.0:
            score -= 20; signals.append("🔴 Rủi Ro Quá Mua Z-Score (> +2.0)")

        # Stoch RSI Check
        if latest['Stoch_RSI'] < 20 and latest['Stoch_RSI'] > prev['Stoch_RSI']:
            score += 15; signals.append("🟢 Stoch RSI Đảo Chiều Đáy")

        # KC Squeeze Check (Nén dồn nổ sóng)
        if latest['KC_Squeeze']:
            score += 10; signals.append("⚡ Keltner Squeeze (Nén Tích Lũy Bùng Nổ)")

        # MACD Acceleration Check
        if latest['Hist_Accel'] > 0 and prev['Hist_Accel'] <= 0:
            score += 10; signals.append("🚀 MACD Tăng Tốc Động Lượng")

        # Trend Check
        if latest['Close'] > latest['EMA50'] and latest['EMA50'] > latest['EMA200']:
            score += 10; signals.append("📈 Cấu Trúc Uptrend Vững Chắc")

        final_score = min(100, max(0, score))
        atr_val = latest['ATR'] if pd.notna(latest['ATR']) else latest['Close'] * 0.03
        entry_price = latest['Close']

        # Risk Engine ATR & Kelly
        stop_loss = entry_price - (1.5 * atr_val)
        take_profit = entry_price + (3.0 * atr_val)

        if final_score >= 80: kelly_alloc = "35% - 40% NAV (Tối Đa Lệnh)"
        elif final_score >= 65: kelly_alloc = "20% - 25% NAV (Trung Bình)"
        elif final_score >= 50: kelly_alloc = "10% - 15% NAV (Thăm Dò)"
        else: kelly_alloc = "0% (Đứng Ngoài Quản Trị Rủi Ro)"

        return {
            'Date': latest['Date'], 'Close': entry_price, 'Volume': latest['Volume'],
            'Z_Score': latest['Z_Score_20'], 'Vol_Ratio': latest['Vol_Ratio'],
            'CMF': latest['CMF'], 'Stoch_RSI': latest['Stoch_RSI'], 'ATR': atr_val,
            'Score': final_score, 'Signals': " | ".join(signals) if signals else "Dòng tiền bình ổn",
            'SL': stop_loss, 'TP': take_profit, 'Kelly': kelly_alloc
        }

    # ==============================================================================
    # 🗄️ MASTER DATABASE LOGIC
    # ==============================================================================
    @staticmethod
    def create_or_update_master_db(raw_ticker_list, days_history=180):
        input_tickers = [t.strip().upper() for t in raw_ticker_list.replace(',', ' ').split() if t.strip()]
        if not input_tickers: 
            return "🛑 Vui lòng nhập ít nhất 1 mã cổ phiếu.", "", "", gr.update(visible=False)

        master_file = Config.MASTER_DB_FILE
        existing_df = pd.DataFrame()
        old_tickers = []
        
        if os.path.exists(master_file):
            try:
                existing_df = pd.read_excel(master_file)
                if 'Ticker' in existing_df.columns:
                    old_tickers = existing_df['Ticker'].unique().tolist()
            except Exception: pass

        new_dfs = []
        log_msgs = []
        successfully_fetched_tickers = []

        for t in input_tickers:
            df_new, src = StockQuantEngine.fetch_stock_data(t, days_history)
            if df_new is not None and not df_new.empty:
                new_dfs.append(df_new)
                successfully_fetched_tickers.append(t)
                log_msgs.append(f"✅ {t}: Nạp thành công {len(df_new)} phiên từ {src}")
            else:
                log_msgs.append(f"❌ {t}: Lỗi kết nối API")

        if not new_dfs:
            return "🛑 KHÔNG LẤY ĐƯỢC DỮ LIỆU MÃ NÀO.\n" + "\n".join(log_msgs), "", "", gr.update(visible=False)

        combined_new = pd.concat(new_dfs, ignore_index=True)

        if not existing_df.empty:
            final_df = pd.concat([existing_df, combined_new], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
        else:
            final_df = combined_new

        final_df['dt_temp'] = pd.to_datetime(final_df['Date'], format='%d/%m/%Y')
        final_df = final_df.sort_values(by=['Ticker', 'dt_temp'], ascending=[True, True]).drop(columns=['dt_temp'])
        final_df.to_excel(master_file, index=False)

        all_current_tickers = final_df['Ticker'].unique().tolist()
        newly_added_tickers = [t for t in successfully_fetched_tickers if t not in old_tickers]

        str_old = ", ".join(old_tickers) if old_tickers else "Chưa có (Lần đầu khởi tạo)"
        str_new = ", ".join(newly_added_tickers) if newly_added_tickers else "Không có mã mới"

        summary_log = (
            f"📑 BÁO CÁO BƠM DỮ LIỆU ĐỘNG CƠ V12 VÀO MASTER DATABASE\n"
            f"=========================================================\n"
            f"⏱️ Múi giờ thực thi (GMT+7 Hà Nội) : {Utils.get_vn_time().strftime('%d/%m/%Y %H:%M:%S')}\n"
            f"💾 File Master Database             : {master_file}\n"
            f"📊 Quy mô Database                 : {len(final_df):,} dòng dữ liệu ({len(all_current_tickers)} mã)\n"
            f"=========================================================\n"
            f"CHI TIẾT TIẾN TRÌNH CÀO:\n" + "\n".join(log_msgs)
        )

        return summary_log, str_old, str_new, gr.update(value=master_file, visible=True)

    @staticmethod
    def run_omni_radar_scanner():
        master_file = Config.MASTER_DB_FILE
        if not os.path.exists(master_file):
            return "🛑 CHƯA CÓ MASTER DATABASE TRÊN SERVER. Vui lòng sang Tab 3 bấm nạp dữ liệu trước."

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
                    m = StockQuantEngine.run_v12_sensors(df_t)
                    if m:
                        results.append({
                            'Mã': t, 'Giá': m['Close'], 'Z-Score': m['Z_Score'],
                            'Vol Ratio': m['Vol_Ratio'], 'CMF': m['CMF'], 'Stoch RSI': m['Stoch_RSI'],
                            'Điểm Quant': m['Score'], 'Tín Hiệu': m['Signals'],
                            'SL': m['SL'], 'TP': m['TP'], 'Kelly': m['Kelly'], 'Date': m['Date']
                        })

            if not results: return "🛑 KHÔNG ĐỦ DỮ LIỆU PHÂN TÍCH (Cần ít nhất 20 phiên/mã)."

            res_df = pd.DataFrame(results).sort_values(by='Điểm Quant', ascending=False).reset_index(drop=True)

            lines = [
                "📑 BÁO CÁO QUÉT CẢM BIẾN V12 BI-TURBO TỪ MASTER DATABASE (OMNI-QUANT RADAR)",
                "======================================================================================================",
                f"⏱️ Thời gian quét (GMT+7 Hà Nội) : {Utils.get_vn_time().strftime('%d/%m/%Y %H:%M:%S')}",
                f"🎯 Danh mục đã quét             : {len(results)} mã từ File Master Database",
                "======================================================================================================",
                f"{'TOP':<3} | {'MÃ':<5} | {'GIÁ (k)':<8} | {'Z-SCORE':<8} | {'VOL RATIO':<9} | {'CMF':<6} | {'STOCH_RSI':<9} | {'ĐIỂM':<5} | TÍN HIỆU CẢM BIẾN V12 KÍCH HOẠT",
                "------------------------------------------------------------------------------------------------------"
            ]

            for idx, r in res_df.iterrows():
                lines.append(
                    f"#{idx+1:<2} | {r['Mã']:<5} | {r['Giá']/1000:>8,.1f} | {r['Z-Score']:>+8.2f} | x{r['Vol Ratio']:>7.2f} | {r['CMF']:>+6.2f} | {r['Stoch RSI']:>9.1f} | {r['Điểm Quant']:>5.0f} | {r['Tín Hiệu']}"
                )

            top1 = res_df.iloc[0]
            lines.extend([
                "======================================================================================================",
                f"🚀 KHUYẾN NGHỊ LỆNH TÁC CHIẾN TỐI ƯU NHẤT: MÃ [{top1['Mã']}] (ĐIỂM QUANT V12: {top1['Điểm Quant']:.0f}/100)",
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
    with gr.Blocks(title="STOCK QUANT ENGINE V7.7 V12", theme=gr.themes.Default(primary_hue="orange")) as demo:
        gr.Markdown(f"# 🚀 PRO STOCK QUANT ENGINE {Config.VERSION}")
        gr.Markdown(f"**Trạng thái Múi Giờ:** GMT+7 (Hà Nội) | **Động Cơ:** V12 Bi-Turbo Advanced Analytics")

        with gr.Tabs():
            # TAB 1: OMNI QUANT RADAR
            with gr.TabItem("🔥 1. OMNI QUANT RADAR (Quét Cảm Biến V12 Master DB)"):
                gr.Markdown("### 📡 CHẠY 7 SIÊU CẢM BIẾN V12 TRÊN TOÀN BỘ MASTER DATABASE")
                gr.Markdown("Bấm nút để quét toàn bộ các mã đang lưu trong file Database tổng (`Master_Stock_Database.xlsx`).")
                
                btn_run_omni_radar = gr.Button("🚀 CHẠY CẢM BIẾN V12 QUÉT MASTER DATABASE", variant="primary")
                out_omni_report = gr.Textbox(label="Báo Cáo Siêu Phân Tích Quant V12 & Lệnh Tác Chiến Tối Ưu", lines=20)
                
                btn_run_omni_radar.click(
                    StockQuantEngine.run_omni_radar_scanner,
                    inputs=[],
                    outputs=[out_omni_report]
                )

            # TAB 2: QUẢN LÝ MASTER DATABASE & KIỂM TRA MÃ CŨ / MỚI
            with gr.TabItem("📊 2. XEM & TẢI MASTER DATABASE SERVER"):
                gr.Markdown("### 💾 QUẢN LÝ TỆP DATABASE TỔNG (`Master_Stock_Database.xlsx`)")
                
                btn_check_db = gr.Button("🔍 KIỂM TRA QUY MÔ DATABASE SERVER", variant="primary")
                with gr.Row():
                    out_old_tickers_db = gr.Textbox(label="📌 Danh Mục Mã Cũ Đã Có Trong DB", lines=2)
                    out_new_tickers_db = gr.Textbox(label="🆕 Mã Mới Vừa Được Thêm Gần Đây", lines=2)
                out_db_info = gr.Textbox(label="Thông Tin Master Database Hiện Tại", lines=8)
                dl_master_file = gr.DownloadButton("📥 BẤM VÀO ĐÂY ĐỂ TẢI MASTER DATABASE (.XLSX)", variant="primary", visible=False)
                
                def check_master():
                    f = Config.MASTER_DB_FILE
                    if os.path.exists(f):
                        df = pd.read_excel(f)
                        ticks = df['Ticker'].unique().tolist() if 'Ticker' in df.columns else []
                        return ", ".join(ticks), "Bấm Tab 3 để xem mã mới thêm", f"✅ Master DB tồn tại ({len(df):,} dòng dữ liệu).\n📌 Tổng cộng: {len(ticks)} mã cổ phiếu.", gr.update(value=f, visible=True)
                    return "Chưa có", "Chưa có", "🛑 Chưa có file Master DB.", gr.update(visible=False)

                btn_check_db.click(check_master, inputs=[], outputs=[out_old_tickers_db, out_new_tickers_db, out_db_info, dl_master_file])

            # TAB 3: TRẠM BƠM DATABASE & PHÂN BIỆT MÃ MỚI / MÃ CŨ
            with gr.TabItem("🌐 3. TRẠM BƠM & CẬP NHẬT DATABASE LŨY TIẾN"):
                gr.Markdown("### 🕸️ KẾT NỐI API -> NẠP LŨY TIẾN VÀO FILE MASTER DATABASE")
                gr.Markdown("Nhập danh sách mã cổ phiếu. Bot sẽ tự đối soát: **Mã cũ** sẽ được cập nhật phiên mới, **Mã mới** sẽ được tạo lịch sử và nộp gộp vào Database.")
                
                ticker_targets = gr.Textbox(
                    label="Danh sách Mã Cổ Phiếu Cần Cào/Cập Nhật (Cách nhau bằng dấu phẩy)", 
                    value="SSI, HPG, TCB, FPT, DIG, MWG, VND, MBB, HSG, STB, VCI, VHM, NVL, PDR, VCB"
                )
                days_slider = gr.Slider(minimum=30, maximum=365, value=180, step=10, label="Số ngày cào lịch sử (Dành cho mã mới)")
                
                btn_update_db = gr.Button("🔄 CHẠY BƠM/CẬP NHẬT DỮ LIỆU VÀO MASTER DATABASE", variant="primary")
                
                with gr.Row():
                    out_old_tickers_pump = gr.Textbox(label="📌 Danh Mục Mã Cũ Đã Có Trong DB", lines=2)
                    out_new_tickers_pump = gr.Textbox(label="🆕 Danh Sách Mã MỚI VỪA BỔ SUNG LẦN ĐẦU", lines=2)
                    
                out_pump_log = gr.Textbox(label="Nhật Ký Tiến Trình Bơm Dữ Liệu Lũy Tiến", lines=12)
                dl_pump_file = gr.DownloadButton("📥 TẢI MASTER DATABASE MỚI NHẤT VỀ MÁY", variant="primary", visible=False)
                
                btn_update_db.click(
                    StockQuantEngine.create_or_update_master_db,
                    inputs=[ticker_targets, days_slider],
                    outputs=[out_pump_log, out_old_tickers_pump, out_new_tickers_pump, dl_pump_file]
                )

    return demo

if __name__ == '__main__':
    demo = create_ui()
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, show_api=False)
