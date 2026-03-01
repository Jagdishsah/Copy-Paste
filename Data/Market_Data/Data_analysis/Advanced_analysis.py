from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage

st.subheader("🚀 Advanced Quantitative Analysis")
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())

saved_files = storage.list_analysis_files()
if not saved_files:
    st.info("No analysis CSV files found.")
else:
    selected_file = st.selectbox("Select Broker Data to Analyze:", saved_files, key="advanced_broker_source")
    raw_df = storage.get_analysis_data(selected_file)
    if raw_df.empty:
        st.warning("Selected file is empty.")
    else:
        raw_df["Date"] = pd.to_datetime(raw_df["Date"])
        min_date, max_date = raw_df["Date"].min().date(), raw_df["Date"].max().date()
        date_range = st.date_input("🗓️ Select Range", value=(min_date, max_date), min_value=min_date, max_value=max_date, key="advanced_date_range")
        if len(date_range) == 2:
            mask = (raw_df["Date"].dt.date >= date_range[0]) & (raw_df["Date"].dt.date <= date_range[1])
            df = raw_df.loc[mask].copy().reset_index(drop=True)
            if not df.empty:
                df["Net_Qty"] = df["Buy_Qty"] - df["Sell_Qty"]
                df["Cum_Net_Qty"] = df["Net_Qty"].cumsum()
                buy_wacc = (df["Buy_Amount"].sum() / max(df["Buy_Qty"].sum(), 1))
                sell_wacc = (df["Sell_Amount"].sum() / max(df["Sell_Qty"].sum(), 1))
                st.metric("Average Buy WACC", f"Rs {buy_wacc:,.2f}")
                st.metric("Average Sell WACC", f"Rs {sell_wacc:,.2f}")
                df_h = df.copy()
                df_h["Day"] = pd.Categorical(df_h["Date"].dt.day_name(), categories=["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"], ordered=True)
                df_h["Month"] = df_h["Date"].dt.strftime("%b %Y")
                heat_pivot = df_h.groupby(["Month", "Day"], observed=False)["Net_Qty"].sum().unstack().fillna(0)
                st.plotly_chart(px.imshow(heat_pivot, color_continuous_scale="RdYlGn", aspect="auto", title="Net Qty Heatmap"), use_container_width=True)
