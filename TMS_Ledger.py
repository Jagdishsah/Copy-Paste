import importlib.util
from pathlib import Path

import streamlit as st

from Services.app.config import load_auth_config, load_storage_config, load_supabase_config
from Services.app.storage import DataStorage
from Services.app.ui import inject_css, render_sidebar_holdings
from supabase import create_client, Client



# --- 1. SUPABASE INITIALIZATION ---
# Make sure you have your secrets set in .streamlit/secrets.toml
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- 2. AUTHENTICATION WALL ---
if "user" not in st.session_state:
    st.set_page_config(page_title="Codex Login", page_icon="🔐", layout="centered")
    
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
            st.rerun()
        except Exception as e:
            st.error(f"Login Failed: Invalid email or password.")
            
    if signup_btn:
        try:
            res = supabase.auth.sign_up({"email": email, "password": password})
            st.success("Account created successfully! You can now log in.")
        except Exception as e:
            st.error(f"Signup Failed: {e}")
            
    st.stop() # 🛑 This completely stops the rest of TMS_Ledger.py from loading!

# --- 3. CODEX TERMINAL (User is Logged In) ---
# (If the code reaches here, the user successfully logged in)
current_user = st.session_state["user"]
st.sidebar.success(f"👤 Logged in as: \n{current_user.email}")

if st.sidebar.button("Log Out", use_container_width=True):
    supabase.auth.sign_out()
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

# !!! YOUR EXISTING TMS_Ledger.py CODE STARTS HERE !!!
# e.g., st.set_page_config(...), rendering tabs, etc.
# (Just remove any duplicate st.set_page_config if you have one below)

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
