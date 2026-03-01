from pathlib import Path
import json

import pandas as pd
import streamlit as st

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage

st.title("📈 Advanced Data Analysis Studio")
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 Upload & Analyze", "📂 Browse Saved Data", "🚀 Advanced Analysis", "📊 Visualization", "🤖 AI Advisor"])

with tab1:
    uploaded_file = st.file_uploader("Upload raw data file (JSON or TXT)", type=["txt", "json"])
    if uploaded_file is not None:
        raw_data = json.load(uploaded_file)
        df = pd.DataFrame(raw_data.get("data", raw_data))
        df["Date"] = pd.to_datetime(df.get("date"), errors="coerce")
        df = df.rename(columns={"b_qty": "Buy_Qty", "s_qty": "Sell_Qty", "b_amt": "Buy_Amount", "s_amt": "Sell_Amount"})
        st.dataframe(df.head(200), use_container_width=True)
        name = st.text_input("Filename (without .csv)")
        if st.button("Save to Supabase") and name:
            storage.save_analysis_data(name, df)
            st.success(f"Saved {name}.csv")

with tab2:
    files = storage.list_analysis_files()
    selected = st.selectbox("Select file", files) if files else None
    if selected:
        st.dataframe(storage.get_analysis_data(selected), use_container_width=True)

with tab3:
    namespace3 = globals().copy()
    namespace3["__name__"] = "advanced_analysis_module"
    with open("Data/Market_Data/Data_analysis/Advanced_analysis.py", encoding="utf-8") as f:
        exec(compile(f.read(), "Advanced_analysis.py", "exec"), namespace3)

with tab4:
    namespace4 = globals().copy()
    namespace4["__name__"] = "visual_analysis_module"
    with open("Data/Market_Data/Data_analysis/Visual.py", encoding="utf-8") as f:
        exec(compile(f.read(), "Visual.py", "exec"), namespace4)

with tab5:
    namespace5 = globals().copy()
    namespace5["__name__"] = "ai_advisor_module"
    with open("Services/Advisor.py", encoding="utf-8") as f:
        exec(compile(f.read(), "Advisor.py", "exec"), namespace5)
