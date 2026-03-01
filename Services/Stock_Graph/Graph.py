from pathlib import Path
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage

st.markdown("### 📈 Pro Interactive Stock Chart")
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())

with st.expander("📁 Data Management (Upload & Save)", expanded=False):
    uploaded_file = st.file_uploader("Upload OHLCV Data (TXT/JSON)", type=["txt", "json"])
    if uploaded_file is not None:
        raw_data = json.load(uploaded_file)
        if raw_data.get("s") == "ok" and "t" in raw_data:
            up_df = pd.DataFrame({
                "Date": pd.to_datetime(raw_data["t"], unit="s"),
                "Open": raw_data["o"], "High": raw_data["h"], "Low": raw_data["l"], "Close": raw_data["c"], "Volume": raw_data["v"],
            })
            stock_symbol = st.text_input("Stock Symbol").upper().strip()
            if st.button("💾 Save to Supabase", use_container_width=True) and stock_symbol:
                try:
                    existing = storage.get_stock_data(stock_symbol)
                    if not existing.empty and "Date" in existing.columns:
                        existing["Date"] = pd.to_datetime(existing["Date"])
                    combined = pd.concat([existing, up_df], ignore_index=True).drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
                    storage.save_stock_data(stock_symbol, combined)
                    st.success(f"Saved {stock_symbol}.csv")
                except Exception as e:
                    st.error(f"Save failed: {e}")

saved_stocks = [f.replace(".csv", "") for f in storage.list_stock_data_files()]
selected_stock = st.selectbox("Select Stock to Chart:", ["-- Select --"] + saved_stocks)
if selected_stock != "-- Select --":
    df = storage.get_stock_data(selected_stock)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.sort_values("Date").reset_index(drop=True)
        df["SMA_20"] = df["Close"].rolling(20).mean()
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["SMA_20"], name="SMA 20"), row=1, col=1)
        fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume"), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=700)
        st.plotly_chart(fig, use_container_width=True)
