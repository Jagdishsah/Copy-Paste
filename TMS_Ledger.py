import importlib.util
from pathlib import Path

import streamlit as st

from Services.app.config import load_auth_config, load_storage_config, load_supabase_config
from Services.app.storage import DataStorage
from Services.app.ui import inject_css, render_sidebar_holdings


st.set_page_config(page_title="NEPSE TMS Pro Ledger", page_icon="💹", layout="wide", initial_sidebar_state="expanded")


TAB_ROUTES = {
    "🏠 Dashboard": Path("Tabs/1_Dashboard/portfolio_view.py"),
    "✍️ Transaction Center": Path("Tabs/2_Transaction_Center/transaction_view.py"),
    "📜 Ledger History": Path("Tabs/3_Ledger_History/history_view.py"),
    "📊 Analytics": Path("Tabs/4_Analytics/analytics_view.py"),
    "🖥️ Terminal Hub": Path("Tabs/5_Terminal_Hub/terminal_view.py"),
    "🧠 Research Hub": Path("Tabs/6_Research_Hub/research_view.py"),
    "🛠️ Manage Data": Path("Tabs/7_Manage_Data/manage_view.py"),
    "🔮 Market Predictor": Path("Tabs/8_Market_Predictor/market_predictor_view.py"),
    "♻️ Restore": Path("Tabs/9_Restore/restore_view.py"),
}


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


def run_tab(path: Path, storage: DataStorage) -> None:
    if not path.exists():
        st.error(f"Missing tab file: {path}")
        return
    spec = importlib.util.spec_from_file_location(f"tab_{path.stem}", path)
    if spec is None or spec.loader is None:
        st.error(f"Could not load tab: {path}")
        return
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if hasattr(module, "render"):
        module.render(storage)
    else:
        st.error(f"Tab missing render(storage): {path}")


if not check_login():
    st.stop()

inject_css()
storage = DataStorage(supabase_config=load_supabase_config(), local_root=Path("."), storage_config=load_storage_config())

with st.sidebar:
    st.title("💹 TMS Pro")
    selected = st.radio("Navigation", list(TAB_ROUTES.keys()))
    st.caption(f"Storage backend: {storage.active_backend()}")
    render_sidebar_holdings(storage, storage.get_holdings())

run_tab(TAB_ROUTES[selected], storage)
