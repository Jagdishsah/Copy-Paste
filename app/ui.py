from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from app.logic import LedgerSummary, fiscal_year_for_nepal
from app.storage import DataStorage
from app.transactions import SmartTransaction, apply_smart_transaction


def inject_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {background-color:#f8f9fa; border:1px solid #e9ecef; padding:10px; border-radius:8px;}
        .risk-alert {background-color:#ffcccb; padding:15px; border-radius:8px; color:#8b0000; font-weight:bold; border-left:5px solid red;}
        .safe-zone {background-color:#d4edda; padding:15px; border-radius:8px; color:#155724; border-left:5px solid green;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_holdings(storage: DataStorage, holdings_df: pd.DataFrame) -> None:
    with st.sidebar.expander("📦 Portfolio & Collateral"):
        sym = st.text_input("Symbol", placeholder="NICA").upper().strip()
        c1, c2 = st.columns(2)
        qty = c1.number_input("Pledged Qty", min_value=0)
        ltp = c2.number_input("LTP", min_value=0.0)
        if st.button("Update Stock") and sym:
            curr_h = storage.get_holdings()
            curr_h = curr_h[curr_h["Symbol"] != sym]
            new_h = pd.DataFrame([{"Symbol": sym, "Total_Qty": qty, "Pledged_Qty": qty, "LTP": ltp, "Haircut": 25}])
            storage.save_holdings(pd.concat([curr_h, new_h], ignore_index=True))
            st.success(f"Updated {sym}")
            st.rerun()

        if not holdings_df.empty:
            st.dataframe(holdings_df[["Symbol", "Total_Qty", "Pledged_Qty", "LTP"]], height=170, width="stretch")


def render_dashboard(df: pd.DataFrame, summary: LedgerSummary) -> None:
    st.title("🏦 Financial Command Center")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📅 Today (Due)", f"Rs {abs(summary.t0_due):,.0f}", delta="Pay Now" if summary.t0_due < 0 else "Receive")
    k2.metric("📆 Tomorrow (T+1)", f"Rs {summary.t1_due:,.0f}")
    k3.metric("🔋 Trading Limit", f"Rs {summary.trading_power:,.0f}", delta=f"{summary.utilization_rate:.1f}% Used")
    k4.metric("⚖️ Net Pending", f"Rs {summary.net_due:,.0f}", delta=f"Pay: {summary.payable_due:,.0f} | Rec: {summary.receivable_due:,.0f}")

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("💵 Net Cash Invested", f"Rs {summary.net_cash_invested:,.0f}")
        st.metric("🏦 TMS Balance", f"Rs {summary.tms_cash_balance:,.0f}")
    with c2:
        if summary.tms_cash_balance < -50:
            st.markdown(f"<div class='risk-alert'>⚠️ Negative collateral of Rs {abs(summary.tms_cash_balance):,.2f}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='safe-zone'>✅ All Systems Green.</div>", unsafe_allow_html=True)

        if not summary.pending_df.empty:
            st.dataframe(summary.pending_df[["Date", "Type", "Category", "Amount", "Due_Date"]], height=220, width="stretch")

    if not df.empty:
        with st.expander("📈 Cashflow Curve"):
            cf = df.copy().sort_values("Date")
            cf["Flow"] = cf.apply(
                lambda x: -x["Amount"] if x["Category"] == "WITHDRAW" else (x["Amount"] if x["Category"] in ["DEPOSIT", "PRIMARY_INVEST", "DIRECT_PAY"] else 0),
                axis=1,
            )
            cf["Cumulative"] = cf["Flow"].cumsum()
            st.plotly_chart(px.line(cf, x="Date", y="Cumulative", markers=True), width="stretch")


def render_new_entry(df: pd.DataFrame, holdings_df: pd.DataFrame, storage: DataStorage) -> None:
    st.header("📝 Integrated Transaction Center")
    tab1, tab2 = st.tabs(["⚡ Smart Entry (syncs holdings)", "🧾 Manual Ledger Entry"])

    with tab1:
        st.caption("Use this mode for normal trading/deposit flows. It automatically updates both ledger and holdings.")
        with st.form("smart_entry_form"):
            c1, c2, c3 = st.columns(3)
            txn_date = c1.date_input("Date", value=date.today())
            mode = c2.selectbox("Mode", ["BUY", "SELL", "DEPOSIT", "WITHDRAW", "DIRECT_PAY", "PRIMARY_INVEST", "EXPENSE"])
            status = c3.selectbox("Status", ["Pending", "Cleared"], index=1)

            c4, c5, c6 = st.columns(3)
            symbol = c4.text_input("Symbol", value="").upper().strip()
            qty = c5.number_input("Qty", min_value=0.0, step=1.0)
            price = c6.number_input("Price", min_value=0.0, step=0.01)

            amount = st.number_input("Direct Amount (for deposit/withdraw/expense)", min_value=0.0, step=1.0)
            due_days = st.number_input("Due in days", min_value=0, value=2)
            ref_id = st.text_input("Reference ID")
            desc = st.text_input("Description")
            submit = st.form_submit_button("💾 Save Smart Transaction")

        if submit:
            txn = SmartTransaction(
                txn_date=txn_date,
                mode=mode,
                symbol=symbol,
                qty=qty,
                price=price,
                amount=amount,
                status=status,
                ref_id=ref_id,
                description=desc,
                due_days=int(due_days),
            )
            new_ledger, new_holdings = apply_smart_transaction(df, holdings_df, txn)
            storage.save_ledger(new_ledger)
            storage.save_holdings(new_holdings)
            st.success("Smart transaction saved. Ledger + holdings synced.")
            st.rerun()

    with tab2:
        with st.form("entry_form"):
            c1, c2, c3 = st.columns(3)
            txn_date = c1.date_input("Date", value=date.today(), key="m_date")
            txn_type = c2.selectbox("Type", ["BUY", "SELL", "CHARGE", "FUND", "OTHER"], key="m_type")
            category = c3.selectbox("Category", ["DEPOSIT", "WITHDRAW", "PAYABLE", "RECEIVABLE", "DIRECT_PAY", "EXPENSE", "PRIMARY_INVEST"], key="m_cat")

            c4, c5, c6 = st.columns(3)
            amount = c4.number_input("Amount", min_value=0.0, step=1000.0, key="m_amt")
            due_days = c5.number_input("Due in days", min_value=0, value=2, key="m_due")
            is_non_cash = c6.checkbox("Non-Cash", value=False, key="m_non_cash")

            ref_id = st.text_input("Reference ID", key="m_ref")
            desc = st.text_input("Description", key="m_desc")

            if st.form_submit_button("💾 Save Manual Ledger Entry"):
                new_row = pd.DataFrame([
                    {
                        "Date": txn_date,
                        "Type": txn_type,
                        "Category": category,
                        "Amount": amount,
                        "Status": "Pending",
                        "Due_Date": txn_date + timedelta(days=due_days),
                        "Ref_ID": ref_id,
                        "Description": desc,
                        "Is_Non_Cash": is_non_cash,
                        "Dispute_Note": "",
                        "Fiscal_Year": fiscal_year_for_nepal(txn_date),
                    }
                ])
                storage.save_ledger(pd.concat([df, new_row], ignore_index=True))
                st.success("Manual entry saved.")
                st.rerun()


def render_history(df: pd.DataFrame) -> None:
    st.header("📜 Transaction Ledger")
    if df.empty:
        st.info("No records found.")
        return
    search = st.text_input("Search Text")
    view_df = df.copy()
    if search:
        view_df = view_df[view_df["Description"].astype(str).str.contains(search, case=False, na=False)]
    st.dataframe(view_df.sort_values("Date", ascending=False), width="stretch", height=600)
    st.download_button("⬇️ Download CSV", view_df.to_csv(index=False).encode("utf-8"), "tms_ledger.csv", "text/csv")


def render_analytics(df: pd.DataFrame, holdings_df: pd.DataFrame) -> None:
    st.header("📊 Integrated Analytics")
    if df.empty:
        st.warning("No data available to visualize.")
        return
    tab1, tab2, tab3 = st.tabs(["📈 Cash Flow", "🍰 Category Mix", "📦 Holdings Snapshot"])
    with tab1:
        cf_df = df.copy().sort_values("Date")
        cf_df["Flow"] = cf_df.apply(lambda x: -x["Amount"] if x["Category"] == "WITHDRAW" else (x["Amount"] if x["Category"] in ["DEPOSIT", "PRIMARY_INVEST", "DIRECT_PAY"] else 0), axis=1)
        cf_df["Cumulative"] = cf_df["Flow"].cumsum()
        st.plotly_chart(px.line(cf_df, x="Date", y="Cumulative", markers=True), width="stretch")
    with tab2:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(df, values="Amount", names="Category", hole=0.4), width="stretch")
        exp_df = df[df["Category"] == "EXPENSE"]
        if not exp_df.empty:
            c2.plotly_chart(px.bar(exp_df, x="Type", y="Amount", color="Type"), width="stretch")
    with tab3:
        if holdings_df.empty:
            st.info("No holdings available.")
        else:
            view = holdings_df.copy()
            view["Gross_Value"] = view["Total_Qty"] * view["LTP"]
            st.dataframe(view, width="stretch")


def exec_external_script(path: str, label: str) -> None:
    try:
        namespace = globals().copy()
        namespace["__name__"] = f"{label}_module"
        with open(path, encoding="utf-8") as file:
            exec(compile(file.read(), path, "exec"), namespace)
    except FileNotFoundError:
        st.error(f"❌ Could not find `{path}`")
    except Exception as e:
        if type(e).__name__ not in ["StopException", "RerunException"]:
            st.error(f"❌ Error loading {label}: {e}")


def render_research_hub() -> None:
    st.header("🧠 Research Hub")
    st.caption("All advanced tools grouped into one place for faster workflow.")
    t1, t2, t3, t4, t5 = st.tabs(["Data Studio", "AI Advisor", "Advanced Analysis", "Stock Graph", "Elliott Scanner"])
    with t1:
        exec_external_script("Data.py", "Data Analysis")
    with t2:
        exec_external_script("Advisor.py", "AI Advisor")
    with t3:
        exec_external_script("Data_analysis/Advanced_analysis.py", "Advanced Analysis")
    with t4:
        exec_external_script("Stock_Graph/Graph.py", "Stock Graph")
    with t5:
        exec_external_script("Stock_Graph/Elliot_Wave.py", "Elliott Wave Scanner")


def render_manage_data(df: pd.DataFrame, storage: DataStorage) -> None:
    st.header("🛠️ Data Management")
    if df.empty:
        st.info("No data to manage.")
        return
    work_df = df.copy()
    work_df["Label"] = work_df.apply(lambda x: f"{x['Date']} | {x['Category']} | Rs {x['Amount']} | {x['Description']}", axis=1)
    selected = st.selectbox("Select Transaction", work_df["Label"].tolist())
    idx = work_df[work_df["Label"] == selected].index[0]

    note = st.text_input("Dispute note", value=str(work_df.at[idx, "Dispute_Note"]))
    c1, c2 = st.columns(2)
    if c1.button("Update Note"):
        work_df.at[idx, "Dispute_Note"] = note
        storage.save_ledger(work_df.drop(columns=["Label"]))
        st.success("Note updated")
        st.rerun()
    if c2.button("Delete Transaction"):
        work_df = work_df.drop(index=idx).drop(columns=["Label"])
        storage.save_ledger(work_df)
        st.error("Deleted")
        st.rerun()
