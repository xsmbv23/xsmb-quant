import os
import pandas as pd
import numpy as np
import glob
import requests
from datetime import datetime, timedelta
import gradio as gr

# ==============================================================================
# CẤU HÌNH HỆ THỐNG
# ==============================================================================
class Config:
    MASTER_DB_FILE = "Master_Stock_Database.xlsx"
    VERSION = "V7.5 (STABLE RELEASE)"

def get_vn_time(): return datetime.utcnow() + timedelta(hours=7)

# ==============================================================================
# ENGINE XỬ LÝ DỮ LIỆU & PHÂN TÍCH
# ==============================================================================
class StockEngine:
    @staticmethod
    def fetch_data(ticker, days=180):
        try:
            end = get_vn_time()
            start = end - timedelta(days=days + 60)
            url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?resolution=D&symbol={ticker.upper()}&from={int(start.timestamp())}&to={int(end.timestamp())}"
            res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7)
            if res.status_code == 200:
                data = res.json()
                if 't' in data and len(data['t']) >= 20:
                    df = pd.DataFrame({'Ticker': ticker.upper(), 'timestamp': data['t'], 'Close': data['c'], 'Volume': data['v']})
                    df['Date'] = (pd.to_datetime(df['timestamp'], unit='s') + timedelta(hours=7)).dt.strftime('%d/%m/%Y')
                    return df[['Ticker', 'Date', 'Close', 'Volume']], "DNSE API"
        except: pass
        return None, "Lỗi API"

    @staticmethod
    def analyze(df):
        df = df.copy()
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        # Cảm biến
        df['MA20_Vol'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['MA20_Vol']
        df['MA20_Price'] = df['Close'].rolling(20).mean()
        df['Std20'] = df['Close'].rolling(20).std()
        df['Z_Score'] = (df['Close'] - df['MA20_Price']) / df['Std20']
        
        latest = df.iloc[-1]
        score = 50
        signals = []
        
        if latest['Vol_Ratio'] > 2.0: score += 20; signals.append("🟢 Nổ Vol")
        if latest['Z_Score'] < -2.0: score += 25; signals.append("🟣 Quá Bán")
        
        return {
            'Score': min(100, max(0, score)),
            'Signals': " | ".join(signals) if signals else "Bình thường",
            'Close': latest['Close']
        }

    @staticmethod
    def update_master_db(tickers_str, days=180):
        tickers = [t.strip().upper() for t in tickers_str.replace(',', ' ').split() if t.strip()]
        if not tickers: return "🛑 Nhập mã!", ""
        
        # Load cũ
        if os.path.exists(Config.MASTER_DB_FILE):
            master_df = pd.read_excel(Config.MASTER_DB_FILE)
        else: master_df = pd.DataFrame()

        new_data = []
        for t in tickers:
            df, _ = StockEngine.fetch_data(t, days)
            if df is not None: new_data.append(df)
            
        if new_data:
            combined = pd.concat(new_data, ignore_index=True)
            master_df = pd.concat([master_df, combined], ignore_index=True).drop_duplicates(subset=['Ticker', 'Date'], keep='last')
            master_df.to_excel(Config.MASTER_DB_FILE, index=False)
            return f"✅ Cập nhật {len(tickers)} mã vào Database.", Config.MASTER_DB_FILE
        return "🛑 Lỗi cào dữ liệu.", ""

    @staticmethod
    def run_radar():
        if not os.path.exists(Config.MASTER_DB_FILE): return "🛑 Database trống."
        df = pd.read_excel(Config.MASTER_DB_FILE)
        results = []
        for t in df['Ticker'].unique():
            m = StockEngine.analyze(df[df['Ticker'] == t])
            results.append({'Mã': t, 'Điểm': m['Score'], 'Tín Hiệu': m['Signals']})
        return pd.DataFrame(results).sort_values('Điểm', ascending=False).to_string()

# ==============================================================================
# UI LAUNCHER
# ==============================================================================
with gr.Blocks(title="Stock Quant", theme=gr.themes.Default(primary_hue="orange")) as demo:
    gr.Markdown("### 📈 STOCK QUANT DASHBOARD V7.5")
    
    with gr.Tabs():
        with gr.TabItem("📡 QUÉT RADAR"):
            btn = gr.Button("🚀 CHẠY SIÊU CẢM BIẾN TOÀN BỘ DANH MỤC")
            out = gr.Textbox(label="Kết quả quét", lines=15)
            btn.click(StockEngine.run_radar, outputs=out)
            
        with gr.TabItem("🌐 TRẠM BƠM DỮ LIỆU"):
            inp = gr.Textbox(label="Nhập mã (cách nhau dấu phẩy)", value="SSI, HPG, TCB")
            btn_pump = gr.Button("🔄 CẬP NHẬT DATABASE", variant="primary")
            out_pump = gr.Textbox(label="Kết quả cập nhật")
            btn_pump.click(StockEngine.update_master_db, inputs=inp, outputs=out_pump)

demo.launch(server_name='0.0.0.0', server_port=10000, show_api=False)
