import os
import sys
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# 📦 BLOCK 1: CẤU HÌNH HỆ THỐNG VÀ MÚI GIỜ
# ==============================================================================
class Config:
    VERSION = "V9.0 REBORN QUANT TERMINAL (CLEAN ARCHITECTURE)"
    MASTER_DB_FILE = "Master_Stock_Database.xlsx"

def get_vn_time():
    # Ép chuẩn múi giờ GMT+7 Việt Nam (Hà Nội)
    return datetime.utcnow() + timedelta(hours=7)

# ==============================================================================
# 📈 BLOCK 2: LÕI THU THẬP & TÍNH TOÁN ĐỊNH LƯỢNG (QUANT ENGINE)
# ==============================================================================
class StockQuantEngine:
    @staticmethod
    def fetch_stock_data(ticker, days=180):
        # 1. DNSE ENTRADE OPEN API (Ưu tiên)
        try:
            end_date = get_vn_time()
            start_date = end_date - timedelta(days=days + 60)
            url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ticker.upper()}&from={int(start_date.timestamp())}&to={int(end_date.timestamp())}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
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
                    return df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']].dropna().reset_index(drop=True)
        except Exception:
            pass

        # 2. YAHOO FINANCE FALLBACK
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}.VN?range=1y&interval=1d"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=6)
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
                    return df[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']].reset_index(drop=True)
        except Exception:
            pass
            
        return None

    @staticmethod
    def run_v9_sensors(df):
        if len(df) < 20:
            return None
        
        try:
            df = df.copy()
            df['Close'] = df['Close'].astype(float)
            df['Volume'] = df['Volume'].astype(float)
            df['High'] = df['High'].astype(float)
            df['Low'] = df['Low'].astype(float)

            # 1. CMF (Chaikin Money Flow 20) - Đo Dòng Tiền Thật
            denom = (df['High'] - df['Low']).replace(0, np.nan)
            mf_mult = ((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / denom
            mf_mult = mf_mult.fillna(0)
            mf_vol = mf_mult * df['Volume']
            cmf_series = mf_vol.rolling(20).sum() / df['Volume'].rolling(20).sum().replace(0, np.nan)
            df['CMF'] = cmf_series.fillna(0)

            # 2. Vol Ratio & Z-Score Volume
            df['MA20_Vol'] = df['Volume'].rolling(20).mean().replace(0, np.nan)
            df['Vol_Ratio'] = (df['Volume'] / df['MA20_Vol']).fillna(1.0)
            
            # 3. Z-Score Mean Reversion Price
            df['MA20_Price'] = df['Close'].rolling(20).mean()
            df['Std20_Price'] = df['Close'].rolling(20).std().replace(0, np.nan)
            df['Z_Score'] = ((df['Close'] - df['MA20_Price']) / df['Std20_Price']).fillna(0)

            # 4. Stochastic RSI Dynamic
            delta = df['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
            rsi = 100 - (100 / (1 + (gain / loss)))
            df['RSI'] = rsi.fillna(50)
            
            rsi_min = df['RSI'].rolling(14).min()
            rsi_max = df['RSI'].rolling(14).max()
            stoch = ((df['RSI'] - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)) * 100
            df['Stoch_RSI'] = stoch.fillna(50)

            # 5. ATR 14 Dynamic Stop-Loss Engine
            tr = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))))
            df['ATR'] = tr.rolling(14).mean().fillna(df['Close'] * 0.03)

            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest

            score = 50.0
            signals = []

            if latest['CMF'] > 0.10: score += 20; signals.append("🟢 CMF Tiền Vào Mạnh")
            elif latest['CMF'] < -0.10: score -= 15; signals.append("🔴 CMF Áp Lực Xả")

            if latest['Vol_Ratio'] > 1.8 and latest['Close'] > prev['Close']:
                score += 15; signals.append("🟢 Smart Money Nổ Vol")

            if latest['Z_Score'] < -1.8: score += 20; signals.append("🟣 Bắt Đáy Z-Score (< -1.8)")
            elif latest['Z_Score'] > 2.0: score -= 20; signals.append("🔴 Rủi Ro Quá Mua (Z > +2.0)")

            if latest['Stoch_RSI'] < 20: score += 10; signals.append("🟢 Stoch RSI Đáy")

            final_score = int(min(100, max(0, score)))
            atr_val = latest['ATR'] if latest['ATR'] > 0 else latest['Close'] * 0.03
            entry_price = latest['Close']

            if final_score >= 80: kelly = "35% - 40% NAV (Tối Đa)"
            elif final_score >= 65: kelly = "20% - 25% NAV (Trung Bình)"
            elif final_score >= 50: kelly = "10% - 15% NAV (Thăm Dò)"
            else: kelly = "0% (Đứng Ngoài Quản Trị)"

            return {
                'Ticker': latest['Ticker'],
                'Date': latest['Date'],
                'Close': float(entry_price),
                'Vol_Ratio': round(float(latest['Vol_Ratio']), 2),
                'Z_Score': round(float(latest['Z_Score']), 2),
                'CMF': round(float(latest['CMF']), 2),
                'Stoch_RSI': round(float(latest['Stoch_RSI']), 1),
                'Score': final_score,
                'Signals': ", ".join(signals) if signals else "Tích lũy bình ổn",
                'SL': float(entry_price - (1.5 * atr_val)),
                'TP': float(entry_price + (3.0 * atr_val)),
                'Kelly': kelly
            }
        except Exception:
            return None

    @staticmethod
    def update_master_db(tickers_str, days=180):
        tickers = [t.strip().upper() for t in tickers_str.replace(',', ' ').split() if t.strip()]
        if not tickers:
            return "🛑 Vui lòng nhập ít nhất 1 mã cổ phiếu!", "", "", None

        master_file = Config.MASTER_DB_FILE
        existing_df = pd.DataFrame()
        old_tickers = []

        if os.path.exists(master_file):
            try:
                existing_df = pd.read_excel(master_file)
                if 'Ticker' in existing_df.columns:
                    old_tickers = existing_df['Ticker'].unique().tolist()
            except Exception:
                pass

        new_dfs = []
        logs = []
        fetched = []

        for t in tickers:
            df = StockQuantEngine.fetch_stock_data(t, days)
            if df is not None and not df.empty:
                new_dfs.append(df)
                fetched.append(t)
                logs.append(f"✅ {t}: Nạp thành công {len(df)} phiên")
            else:
                logs.append(f"❌ {t}: Lỗi kết nối API")

        if not new_dfs:
            return "🛑 Không cào được dữ liệu mã nào!\n" + "\n".join(logs), "", "", None

        combined = pd.concat(new_dfs, ignore_index=True)
        if not existing_df.empty:
            final_df = pd.concat([existing_df, combined], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=['Ticker', 'Date'], keep='last')
        else:
            final_df = combined

        final_df['dt_temp'] = pd.to_datetime(final_df['Date'], format='%d/%m/%Y')
        final_df = final_df.sort_values(by=['Ticker', 'dt_temp']).drop(columns=['dt_temp'])
        final_df.to_excel(master_file, index=False)

        new_tickers = [t for t in fetched if t not in old_tickers]

        summary = f"✅ BƠM DỮ LIỆU THÀNH CÔNG LÚC {get_vn_time().strftime('%H:%M:%S %d/%m/%Y')}\n" + "\n".join(logs)
        return summary, ", ".join(old_tickers), ", ".join(new_tickers) if new_tickers else "Không có mã mới", master_file

    @staticmethod
    def run_radar_analytics():
        master_file = Config.MASTER_DB_FILE
        if not os.path.exists(master_file):
            return pd.DataFrame(), "🛑 CHƯA CÓ MASTER DATABASE! Hãy sang Tab 3 bấm nạp dữ liệu trước."

        try:
            df = pd.read_excel(master_file)
            if df.empty or 'Ticker' not in df.columns:
                return pd.DataFrame(), "🛑 File Master Database rỗng."

            results = []
            for t in df['Ticker'].unique():
                df_t = df[df['Ticker'] == t].copy()
                df_t['dt_temp'] = pd.to_datetime(df_t['Date'], format='%d/%m/%Y')
                df_t = df_t.sort_values('dt_temp').reset_index(drop=True)
                
                res = StockQuantEngine.run_v9_sensors(df_t)
                if res:
                    results.append(res)

            if not results:
                return pd.DataFrame(), "🛑 Không đủ dữ liệu tính toán (Cần >= 20 phiên)."

            res_df = pd.DataFrame(results).sort_values(by='Score', ascending=False).reset_index(drop=True)

            top1 = res_df.iloc[0]
            top_info = (
                f"🏆 MÃ TỐI ƯU NHẤT THỜI ĐIỂM HIỆN TẠI: [{top1['Ticker']}] | Điểm Quant: {top1['Score']}/100\n"
                f"---------------------------------------------------------------------------------\n"
                f"• 💵 Vùng Giá Mua Giải Ngân : {top1['Close']:,.0f} VNĐ (Phiên {top1['Date']})\n"
                f"• 🎯 Mục tiêu Chốt Lời (TP) : {top1['TP']:,.0f} VNĐ (+{((top1['TP']-top1['Close'])/top1['Close']*100):.1f}%)\n"
                f"• 🛡️ Cắt Lỗ Tự Động (SL)   : {top1['SL']:,.0f} VNĐ (-{((top1['Close']-top1['SL'])/top1['Close']*100):.1f}%)\n"
                f"• 💰 Tỷ lệ Đi Tiền Kelly   : {top1['Kelly']}"
            )

            display_df = res_df[['Ticker', 'Score', 'Close', 'Z_Score', 'Vol_Ratio', 'CMF', 'Stoch_RSI', 'Signals']].copy()
            display_df.columns = ['Mã', 'Điểm Quant', 'Giá Đóng (VNĐ)', 'Z-Score', 'Vol Ratio', 'CMF', 'Stoch RSI', 'Tín Hiệu Kích Hoạt']

            return display_df, top_info
        except Exception as e:
            return pd.DataFrame(), f"🛑 Lỗi phân tích: {str(e)}"

# ==============================================================================
# 🎨 BLOCK 3: GIAO DIỆN TERMINAL CHUYÊN NGHIỆP (GRADIO NATIVE)
# ==============================================================================
def create_ui():
    with gr.Blocks(title="STOCK QUANT V9.0", theme=gr.themes.Soft(primary_hue="orange")) as demo:
        gr.Markdown("# 🚀 PRO STOCK QUANT TERMINAL V9.0 (REBORN)")
        gr.Markdown(f"**Hệ Thống Phân Tích Định Lượng & Quản Trị Vốn ATR/Kelly** | Múi giờ: GMT+7 (Hà Nội)")

        with gr.Tabs():
            # TAB 1: RADAR TERMINAL
            with gr.TabItem("🔥 1. OMNI QUANT RADAR (Quét Cảm Biến DB)"):
                btn_radar = gr.Button("🚀 KÍCH HOẠT CẢM BIẾN QUÉT MASTER DATABASE", variant="primary")
                top_highlight = gr.Textbox(label="🎯 Khuyến Nghị Lệnh Tác Chiến Tối Ưu Nhất", lines=6)
                radar_table = gr.Dataframe(label="Bảng Dữ Liệu Xếp Hạng Điểm Quant Toàn Danh Mục", interactive=False)

                btn_radar.click(
                    StockQuantEngine.run_radar_analytics,
                    inputs=[],
                    outputs=[radar_table, top_highlight]
                )

            # TAB 2: QUẢN LÝ DATABASE
            with gr.TabItem("📊 2. XEM & TẢI MASTER DATABASE SERVER"):
                btn_check = gr.Button("🔍 KIỂM TRA QUY MÔ MASTER DATABASE")
                with gr.Row():
                    out_old = gr.Textbox(label="📌 Danh Mục Mã Cũ Đã Có Trong DB", lines=2)
                    out_new = gr.Textbox(label="🆕 Danh Sách Mã Mới Thêm Gần Đây", lines=2)
                db_status = gr.Textbox(label="Trạng Thái File Master Database", lines=3)
                dl_file = gr.DownloadButton("📥 BẤM VÀO ĐÂY ĐỂ TẢI FILE EXCEL MASTER DATABASE (.XLSX)", visible=False)

                def check_db():
                    f = Config.MASTER_DB_FILE
                    if os.path.exists(f):
                        df = pd.read_excel(f)
                        ticks = df['Ticker'].unique().tolist() if 'Ticker' in df.columns else []
                        return ", ".join(ticks), "Xem nhật ký ở Tab 3", f"✅ DB Tồn tại: {len(df):,} dòng dữ liệu ({len(ticks)} mã cổ phiếu).", gr.update(value=f, visible=True)
                    return "Rỗng", "Rỗng", "🛑 Chưa có file Master DB.", gr.update(visible=False)

                btn_check.click(check_db, outputs=[out_old, out_new, db_status, dl_file])

            # TAB 3: TRẠM BƠM DỮ LIỆU LŨY TIẾN
            with gr.TabItem("🌐 3. TRẠM BƠM & CẬP NHẬT DATABASE LŨY TIẾN"):
                gr.Markdown("### 🕸️ KẾT NỐI API -> NẠP DỮ LIỆU LŨY TIẾN HẰNG NGÀY")
                gr.Markdown("Nhập danh sách mã. Sau 15:00 hằng ngày, bấm nút để bot **nạp nối đuôi phiên mới** vào file `Master_Stock_Database.xlsx`.")
                
                ticker_input = gr.Textbox(
                    label="Danh sách Mã Cổ Phiếu Cần Cào/Cập Nhật (Phân tách bằng dấu phẩy)",
                    value="SSI, HPG, TCB, FPT, DIG, MWG, VND, MBB, HSG, STB, VCI, VHM, NVL, PDR, VCB"
                )
                days_slider = gr.Slider(minimum=30, maximum=365, value=180, step=10, label="Số ngày cào lịch sử (Dành cho mã mới thêm lần đầu)")
                btn_pump = gr.Button("🔄 CHẠY BƠM / CẬP NHẬT DỮ LIỆU VÀO MASTER DB", variant="primary")

                with gr.Row():
                    pump_old = gr.Textbox(label="📌 Danh Mục Mã Cũ Đã Có", lines=2)
                    pump_new = gr.Textbox(label="🆕 Danh Sách Mã Mới Vừa Bổ Sung", lines=2)
                pump_log = gr.Textbox(label="Nhật Ký Tiến Trình Bơm Dữ Liệu Lũy Tiến", lines=10)
                pump_dl = gr.DownloadButton("📥 TẢI MASTER DATABASE MỚI NHẤT VỀ MÁY", visible=False)

                btn_pump.click(
                    StockQuantEngine.update_master_db,
                    inputs=[ticker_input, days_slider],
                    outputs=[pump_log, pump_old, pump_new, pump_dl]
                )

    return demo

if __name__ == '__main__':
    demo = create_ui()
    # Cấu hình Port Dynamic cho Render Deploy
    port = int(os.environ.get('PORT', 10000))
    demo.launch(server_name='0.0.0.0', server_port=port, show_api=False)
