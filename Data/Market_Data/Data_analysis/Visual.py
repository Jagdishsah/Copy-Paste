from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage

st.subheader("📊 Visual Data Analysis")
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())

saved_files = storage.list_analysis_files()
if not saved_files:
    st.info("No saved analysis files found.")
else:
    selected_file = st.selectbox("Select file:", saved_files, key="visual_file")
    df = storage.get_analysis_data(selected_file)
    if df.empty:
        st.warning("No rows found in this file.")
    else:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Net_Qty"] = pd.to_numeric(df.get("Buy_Qty", 0), errors="coerce").fillna(0) - pd.to_numeric(df.get("Sell_Qty", 0), errors="coerce").fillna(0)
        st.plotly_chart(px.line(df.sort_values("Date"), x="Date", y="Net_Qty", title="Net Quantity Trend"), use_container_width=True)
        st.dataframe(df.tail(200), use_container_width=True)
