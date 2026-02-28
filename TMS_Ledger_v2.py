from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from core.analytics import fiscal_year_for_nepal, summarize_ledger
from core.config import load_auth_config, load_github_config
from core.storage import LEDGER_COLUMNS, LedgerStorage


st.set_page_config(page_title="NEPSE TMS Ledger v2", page_icon="🇳🇵", layout="wide")


def check_login() -> bool:
    cfg = load_auth_config()
    if cfg is None:
        st.warning("Auth secret missing. Running in dev-open mode.")
        return True

    if st.session_state.get("auth_ok"):
        return True

    st.title("🔐 NEPSE TMS Ledger v2 Login")
    c1, c2 = st.columns(2)
    user = c1.text_input("Username")
    pwd = c2.text_input("Password", type="password")
    if st.button("Login", type="primary"):
        if user == cfg.username and pwd == cfg.password:
            st.session_state["auth_ok"] = True
            st.rerun()
        st.error("Incorrect credentials")
    return False


if not check_login():
    st.stop()


storage = LedgerStorage(github_config=load_github_config(), local_root=Path("."))

ledger = storage.get_ledger()
holdings = storage.get_holdings()
summary = summarize_ledger(ledger, holdings, date.today())

st.title("🇳🇵 NEPSE Trading Command Center — v2 (Isolated Sandbox)")
st.caption("This is a safer test environment (new app file) so you can validate changes before replacing the old app.")

k1, k2, k3, k4 = st.columns(4)
k1.metric("TMS Cash Balance", f"Rs {summary.tms_cash_balance:,.2f}")
k2.metric("Trading Power", f"Rs {summary.trading_power:,.2f}", delta=f"{summary.utilization_rate:.1f}% utilized")
k3.metric("Today's Net Settlement", f"Rs {summary.today_due:,.2f}")
k4.metric("Net Cash Invested", f"Rs {summary.net_cash_invested:,.2f}")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Ledger Entry", "Holdings", "Diagnostics"],
)

if page == "Dashboard":
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Settlement Outlook (T+2)")
        due_df = pd.DataFrame(
            {
                "Window": ["Today", "Tomorrow", "Day After"],
                "Net Amount": [summary.today_due, summary.tomorrow_due, summary.day_after_due],
            }
        )
        fig = px.bar(due_df, x="Window", y="Net Amount", color="Net Amount", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig, width="stretch")

        st.subheader("Recent Ledger")
        display_cols = ["Date", "Type", "Category", "Amount", "Status", "Due_Date", "Description"]
        st.dataframe(ledger[display_cols].sort_values("Date", ascending=False).head(30), width="stretch")

    with right:
        st.subheader("Risk Panel")
        if summary.tms_cash_balance < 0:
            st.error(f"Negative broker cash: Rs {abs(summary.tms_cash_balance):,.2f}. Add funds.")
        else:
            st.success("Broker cash is healthy.")

        if summary.today_due < 0:
            st.warning(f"Settlement payable today: Rs {abs(summary.today_due):,.2f}")
        else:
            st.info("No urgent settlement payable today.")

if page == "Ledger Entry":
    st.subheader("Add New Ledger Entry")
    with st.form("new_entry"):
        c1, c2, c3 = st.columns(3)
        entry_date = c1.date_input("Date", value=date.today())
        due_date = c2.date_input("Due Date", value=date.today())
        entry_type = c3.selectbox("Type", ["BUY", "SELL", "FUND", "CHARGE", "OTHER"])

        c4, c5, c6 = st.columns(3)
        category = c4.selectbox("Category", ["DEPOSIT", "WITHDRAW", "PAYABLE", "RECEIVABLE", "DIRECT_PAY", "EXPENSE", "PRIMARY_INVEST"])
        amount = c5.number_input("Amount", min_value=0.0, step=1000.0)
        status = c6.selectbox("Status", ["PENDING", "SETTLED", "DISPUTED"])

        desc = st.text_input("Description")
        ref_id = st.text_input("Reference ID")
        non_cash = st.checkbox("Non-cash collateral transaction")

        submitted = st.form_submit_button("Save Entry", type="primary")

    if submitted:
        new_row = {
            "Date": entry_date,
            "Type": entry_type,
            "Category": category,
            "Amount": amount,
            "Status": status,
            "Due_Date": due_date,
            "Ref_ID": ref_id,
            "Description": desc,
            "Is_Non_Cash": non_cash,
            "Dispute_Note": "",
            "Fiscal_Year": fiscal_year_for_nepal(entry_date),
        }
        ledger = pd.concat([ledger, pd.DataFrame([new_row])], ignore_index=True)
        ledger = ledger[LEDGER_COLUMNS]
        storage.save_ledger(ledger)
        st.success("Entry saved to local + GitHub (if configured).")
        st.rerun()

if page == "Holdings":
    st.subheader("Collateral Holdings")
    st.dataframe(holdings, width="stretch")

    with st.form("holding_upsert"):
        c1, c2, c3, c4 = st.columns(4)
        symbol = c1.text_input("Symbol", value="").upper().strip()
        qty = c2.number_input("Pledged Qty", min_value=0.0, step=10.0)
        ltp = c3.number_input("LTP", min_value=0.0, step=1.0)
        haircut = c4.number_input("Haircut %", min_value=0.0, max_value=100.0, value=25.0)
        save_h = st.form_submit_button("Upsert Holding", type="primary")

    if save_h and symbol:
        holdings = holdings[holdings["Symbol"] != symbol]
        holdings = pd.concat(
            [
                holdings,
                pd.DataFrame(
                    [
                        {
                            "Symbol": symbol,
                            "Total_Qty": qty,
                            "Pledged_Qty": qty,
                            "LTP": ltp,
                            "Haircut": haircut,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        storage.save_holdings(holdings)
        st.success(f"Updated {symbol}")
        st.rerun()

if page == "Diagnostics":
    st.subheader("System Diagnostics")
    st.write("GitHub configured:" , "Yes" if load_github_config() else "No (local mode)")
    st.write("Ledger rows:", len(ledger))
    st.write("Holdings rows:", len(holdings))
    st.code("streamlit run TMS_Ledger_v2.py")
