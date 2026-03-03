import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date

# --- NEW IMPORTS TO FIX THE ERROR ---
from Services.app.storage import DataStorage
from Services.app.config import load_storage_config, load_supabase_config

# 1. Initialize Storage (This defines the 'storage' variable that was missing)
storage = DataStorage(
    supabase_config=load_supabase_config(),
    local_root=Path("."),
    storage_config=load_storage_config()
)

st.set_page_config(page_title="NEPSE TMS Ledger", layout="wide")

st.title("📂 TMS Ledger & Portfolio Manager")

# 2. Setup Session State
if "ledger_df" not in st.session_state:
    try:
        # Now 'storage' is defined, so this line won't crash
        st.session_state.ledger_df = storage.get_ledger()
    except Exception as e:
        st.error(f"Failed to load ledger: {e}")
        st.session_state.ledger_df = pd.DataFrame()

# --- THE REST OF YOUR LEDGER LOGIC ---
tab1, tab2 = st.tabs(["View Ledger", "Add Transaction"])

with tab1:
    if not st.session_state.ledger_df.empty:
        st.dataframe(st.session_state.ledger_df, use_container_width=True)
        
        # Simple Calculation for Manipulation Tracking
        total_buy = st.session_state.ledger_df[st.session_state.ledger_df['Type'] == 'BUY']['Amount'].sum()
        total_sell = st.session_state.ledger_df[st.session_state.ledger_df['Type'] == 'SELL']['Amount'].sum()
        st.metric("Net Cash Flow", f"Rs {total_buy - total_sell:,.2f}")
    else:
        st.info("No ledger data found. Add a transaction to begin.")

with tab2:
    with st.form("add_txn"):
        c1, c2, c3 = st.columns(3)
        t_date = c1.date_input("Date", date.today())
        t_type = c2.selectbox("Type", ["BUY", "SELL"])
        t_symbol = c3.text_input("Symbol").upper()
        
        c4, c5 = st.columns(2)
        t_qty = c4.number_input("Quantity", min_value=1)
        t_price = c5.number_input("Price", min_value=1.0)
        
        if st.form_submit_button("Add to Ledger"):
            new_data = {
                "Date": t_date.strftime("%Y-%m-%d"),
                "Type": t_type,
                "Symbol": t_symbol,
                "Qty": t_qty,
                "Price": t_price,
                "Amount": t_qty * t_price
            }
            # Logic to save via storage
            new_df = pd.concat([st.session_state.ledger_df, pd.DataFrame([new_data])], ignore_index=True)
            storage.save_ledger(new_df)
            st.session_state.ledger_df = new_df
            st.success("Transaction Saved!")
            st.rerun()
