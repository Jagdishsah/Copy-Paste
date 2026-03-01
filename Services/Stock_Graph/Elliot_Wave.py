from pathlib import Path
import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage

st.markdown("### 🌊 Institutional Elliott Wave Engine")
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())


def run_ew_analysis(df_full, replay_date, sensitivity):
    df = df_full[df_full["Date"].dt.date <= replay_date].copy().reset_index(drop=True)
    if len(df) < 50:
        st.warning("Need at least 50 rows.")
        return
    highs = df["High"].rolling(sensitivity, min_periods=1).max()
    lows = df["Low"].rolling(sensitivity, min_periods=1).min()
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"))
    fig.add_trace(go.Scatter(x=df["Date"], y=highs, name="Rolling High"))
    fig.add_trace(go.Scatter(x=df["Date"], y=lows, name="Rolling Low"))
    st.plotly_chart(fig, use_container_width=True)


saved_stocks = [f.replace(".csv", "") for f in storage.list_stock_data_files()]
if saved_stocks:
    c_stock, c_sens = st.columns([2, 1])
    selected_stock = c_stock.selectbox("Select Stock:", saved_stocks)
    sensitivity = c_sens.number_input("Degree (Sensitivity)", 2, 20, 4)
    df_master = storage.get_stock_data(selected_stock)
    if not df_master.empty:
        df_master["Date"] = pd.to_datetime(df_master["Date"])
        min_d = df_master["Date"].min().date()
        max_d = df_master["Date"].max().date()
        replay_date = st.slider("Select Replay Date", min_value=min_d, max_value=max_d, value=max_d - datetime.timedelta(days=30), step=datetime.timedelta(days=1))
        run_ew_analysis(df_master, replay_date, sensitivity)
else:
    st.info("No stock files available.")
