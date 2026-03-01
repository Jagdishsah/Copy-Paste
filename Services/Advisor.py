from pathlib import Path

import google.generativeai as genai
import pandas as pd
import streamlit as st

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage

st.header("🤖 AI Quantitative Advisor")
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())

try:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    model = genai.GenerativeModel("gemini-2.0-flash")
except Exception as e:
    st.error(f"Gemini setup failed: {e}")
    st.stop()

files = storage.list_analysis_files()
if not files:
    st.info("No saved data found.")
else:
    selected_file = st.selectbox("Select Broker Data for AI Analysis:", files)
    df = storage.get_analysis_data(selected_file)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        net_inventory = (pd.to_numeric(df["Buy_Qty"], errors="coerce").fillna(0) - pd.to_numeric(df["Sell_Qty"], errors="coerce").fillna(0)).sum()
        user_question = st.text_input("Ask AI", placeholder="Accumulation vs distribution?")
        if st.button("🧠 Generate AI Analysis", type="primary"):
            prompt = f"Analyze file {selected_file}. Net inventory: {net_inventory}. Question: {user_question or 'General analysis'}"
            response = model.generate_content(prompt)
            st.markdown(response.text)
