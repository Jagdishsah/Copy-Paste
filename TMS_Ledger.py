import importlib.util
from pathlib import Path
from datetime import datetime # Added missing import

import streamlit as st
from supabase import create_client, Client

# MUST BE THE FIRST STREAMLIT COMMAND!
st.set_page_config(
    page_title="NEPSE TMS Pro Ledger", 
    page_icon="💹", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

from Services.app.config import load_storage_config, load_supabase_config
from Services.app.storage import DataStorage
from Services.app.ui import inject_css, render_sidebar_holdings

# --- 1. SUPABASE INITIALIZATION ---
# Using project config helpers for consistency
supabase_cfg = load_supabase_config()
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. AUTHENTICATION WALL ---
if "user" not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🔐 Project Codex</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Login or create an account to access your secure terminal.</p>", unsafe_allow_html=True)
    
    with st.form("auth_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        
        c1, c2 = st.columns(2)
        with c1:
            login_btn = st.form_submit_button("Log In", use_container_width=True)
        with c2:
            signup_btn = st.form_submit_button("Sign Up", use_container_width=True)

    if login_btn:
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["user"] = res.user
            st.session_state["access_token"] = res.session.access_token 
            st.rerun()
        except Exception as e:
            st.error("Login Failed: Invalid email or password.")
            
    if signup_btn:
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            st.success("Account created successfully! You can now log in.")
        except Exception as e:
            st.error(f"Signup Failed: {e}")
            
    st.stop() # 🛑 Blocks execution until logged in

# --- 3. CODEX TERMINAL (User is Logged In) ---
# Initialize Storage AFTER login [cite: 425]
storage = DataStorage(
    supabase_config=supabase_cfg, 
    local_root=Path("."), 
    storage_config=load_storage_config()
)

# Caching and Initial Sync logic moved here [cite: 33, 263]
if "ledger_df" not in st.session_state:
    with st.spinner("Syncing with Cloud..."):
        try:
            st.session_state.ledger_df = storage.get_ledger()
            st.session_state.holdings_df = storage.get_holdings()
            st.session_state.last_sync = datetime.now()
        except Exception as e:
            st.error(f"Sync failed: {e}")
            st.session_state.ledger_df = None

inject_css()

# --- 4. NAVIGATION & ROUTING ---
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

# Sidebar UI
with st.sidebar:
    st.title("💹 TMS Pro")
    st.caption(f"👤 {st.session_state['user'].email}")
    
    selected = st.radio("Navigation", list(TAB_ROUTES.keys()))
    st.caption(f"Storage backend: {storage.active_backend()}") [cite: 353]
    
    # Use cached holdings if available
    holdings = st.session_state.get("holdings_df", storage.get_holdings())
    render_sidebar_holdings(storage, holdings)
    
    st.divider()
    if st.button("Log Out", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()

# Execute selected tab
run_tab(TAB_ROUTES[selected], storage) [cite: 424]
