from datetime import date
from pathlib import Path

import streamlit as st

from app.config import load_auth_config, load_github_config
from app.logic import summarize_ledger
from app.storage import DataStorage
from app.ui import (
    exec_external_script,
    inject_css,
    render_analytics,
    render_dashboard,
    render_history,
    render_manage_data,
    render_new_entry,
    render_sidebar_holdings,
)


st.set_page_config(page_title="NEPSE TMS Pro Ledger", page_icon="💹", layout="wide", initial_sidebar_state="expanded")


def check_login() -> bool:
    cfg = load_auth_config()
    if cfg is None:
        st.warning("Secrets not configured. Running in open local mode.")
        return True
    if st.session_state.get("password_correct"):
        return True
    st.title("🔒 TMS Ledger Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == cfg.username and pwd == cfg.password:
            st.session_state["password_correct"] = True
            st.rerun()
        st.error("❌ Incorrect Username or Password")
    return False


if not check_login():
    st.stop()

inject_css()
storage = DataStorage(github_config=load_github_config(), local_root=Path("."))
df = storage.get_ledger()
holdings_df = storage.get_holdings()
summary = summarize_ledger(df, holdings_df, date.today())

with st.sidebar:
    st.title("💹 TMS Pro")
    menu = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "✍️ New Entry",
            "📜 Ledger History",
            "📊 Analytics",
            "🛠️ Manage Data",
            "📈 Data Analysis",
            "🤖 AI Advisor",
            "Stock Graph",
            "Elliott Wave Scanner",
        ],
    )
    render_sidebar_holdings(storage, holdings_df)

if menu == "🏠 Dashboard":
    render_dashboard(df, summary)
elif menu == "✍️ New Entry":
    render_new_entry(df, storage)
elif menu == "📜 Ledger History":
    render_history(df)
elif menu == "📊 Analytics":
    render_analytics(df)
elif menu == "🛠️ Manage Data":
    render_manage_data(df, storage)
elif menu == "📈 Data Analysis":
    exec_external_script("Data.py", "Data Analysis")
elif menu == "🤖 AI Advisor":
    exec_external_script("Advisor.py", "AI Advisor")
elif menu == "Stock Graph":
    exec_external_script("Stock_Graph/Graph.py", "Stock Graph")
elif menu == "Elliott Wave Scanner":
    exec_external_script("Stock_Graph/Elliot_Wave.py", "Elliott Wave Scanner")
