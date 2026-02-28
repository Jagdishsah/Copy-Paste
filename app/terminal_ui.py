from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from app.storage import DataStorage


def _now_np() -> str:
    return (datetime.utcnow() + pd.Timedelta(hours=5, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")


def _compute_integrated_metrics(ledger_df: pd.DataFrame, holdings_df: pd.DataFrame, cache_df: pd.DataFrame, history_df: pd.DataFrame) -> dict:
    data = holdings_df.copy()
    if data.empty:
        return {"invested": 0.0, "market": 0.0, "unrealized": 0.0, "realized": 0.0}

    data = pd.merge(data, cache_df[["Symbol", "LTP"]] if "Symbol" in cache_df.columns else pd.DataFrame(columns=["Symbol", "LTP"]), on="Symbol", how="left", suffixes=("", "_cache"))
    data["LTP"] = pd.to_numeric(data.get("LTP_cache", data.get("LTP", 0)), errors="coerce").fillna(pd.to_numeric(data.get("LTP", 0), errors="coerce").fillna(0))

    payables = ledger_df[ledger_df["Category"] == "PAYABLE"]["Amount"].sum() if not ledger_df.empty else 0.0
    receivables = ledger_df[ledger_df["Category"] == "RECEIVABLE"]["Amount"].sum() if not ledger_df.empty else 0.0
    invested = max(float(payables - receivables), 0.0)

    market = float((pd.to_numeric(data["Total_Qty"], errors="coerce").fillna(0) * pd.to_numeric(data["LTP"], errors="coerce").fillna(0)).sum())
    unrealized = market - invested
    realized = float(history_df["Net_PL"].sum()) if (not history_df.empty and "Net_PL" in history_df.columns) else 0.0
    return {"invested": invested, "market": market, "unrealized": unrealized, "realized": realized}


def render_terminal_hub(storage: DataStorage, ledger_df: pd.DataFrame, holdings_df: pd.DataFrame) -> None:
    st.header("🖥️ NEPSE Terminal Hub")
    st.caption("Absorbed from Nepse_Terminal and integrated with your ledger + holdings.")

    portfolio_df = storage.get_terminal_data("portfolio.csv")
    watchlist_df = storage.get_terminal_data("watchlist.csv")
    history_df = storage.get_terminal_data("history.csv")
    diary_df = storage.get_terminal_data("diary.csv")
    cache_df = storage.get_terminal_data("cache.csv")
    activity_df = storage.get_terminal_data("activity_log.csv")
    wealth_df = storage.get_terminal_data("wealth.csv")

    metrics = _compute_integrated_metrics(ledger_df, holdings_df, cache_df, history_df)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Integrated Invested", f"Rs {metrics['invested']:,.2f}")
    m2.metric("Integrated Market Value", f"Rs {metrics['market']:,.2f}")
    m3.metric("Unrealized P/L", f"Rs {metrics['unrealized']:,.2f}")
    m4.metric("Realized P/L", f"Rs {metrics['realized']:,.2f}")

    tabs = st.tabs(["Portfolio", "Watchlist", "History", "Diary", "Cache", "Activity", "Wealth Curve"])

    with tabs[0]:
        st.subheader("Portfolio (editable)")
        edited = st.data_editor(portfolio_df, width="stretch", num_rows="dynamic")
        if st.button("Save Portfolio"):
            storage.save_terminal_data("portfolio.csv", edited)
            st.success("Portfolio saved")

    with tabs[1]:
        st.subheader("Watchlist (editable)")
        edited = st.data_editor(watchlist_df, width="stretch", num_rows="dynamic")
        if st.button("Save Watchlist"):
            storage.save_terminal_data("watchlist.csv", edited)
            st.success("Watchlist saved")

    with tabs[2]:
        st.subheader("Trade History")
        st.dataframe(history_df.sort_values("Date", ascending=False) if "Date" in history_df.columns else history_df, width="stretch")

    with tabs[3]:
        st.subheader("Trading Diary")
        edited = st.data_editor(diary_df, width="stretch", num_rows="dynamic")
        if st.button("Save Diary"):
            storage.save_terminal_data("diary.csv", edited)
            st.success("Diary saved")

    with tabs[4]:
        st.subheader("Price Cache")
        edited = st.data_editor(cache_df, width="stretch", num_rows="dynamic")
        if st.button("Save Cache"):
            storage.save_terminal_data("cache.csv", edited)
            st.success("Cache saved")

    with tabs[5]:
        st.subheader("Unified Activity")
        led = ledger_df[["Date", "Category", "Description", "Amount"]].copy() if not ledger_df.empty else pd.DataFrame(columns=["Date", "Category", "Description", "Amount"])
        if not led.empty:
            led["Timestamp"] = pd.to_datetime(led["Date"]).astype(str)
            led["Action"] = "LEDGER"
            led["Symbol"] = led["Description"].astype(str).str.split("|").str[0].str.strip()
            led["Details"] = led["Description"]
            led = led[["Timestamp", "Category", "Symbol", "Action", "Details", "Amount"]]

        merged = pd.concat([activity_df, led], ignore_index=True) if not led.empty else activity_df
        st.dataframe(merged.sort_values("Timestamp", ascending=False) if "Timestamp" in merged.columns else merged, width="stretch", height=420)

        if st.button("Snapshot activity from ledger"):
            storage.save_terminal_data("activity_log.csv", merged)
            st.success("Activity log synced")

    with tabs[6]:
        st.subheader("Wealth Curve")
        if wealth_df.empty:
            wealth_df = pd.DataFrame(columns=["Date", "Total_Investment", "Current_Value", "Total_PL", "Day_Change", "Sold_Volume"])

        today = _now_np().split(" ")[0]
        new_row = pd.DataFrame([
            {
                "Date": today,
                "Total_Investment": round(metrics["invested"], 2),
                "Current_Value": round(metrics["market"], 2),
                "Total_PL": round(metrics["unrealized"] + metrics["realized"], 2),
                "Day_Change": 0.0,
                "Sold_Volume": float(history_df["Received_Amount"].sum()) if (not history_df.empty and "Received_Amount" in history_df.columns) else 0.0,
            }
        ])
        wealth_df = wealth_df[wealth_df["Date"] != today] if "Date" in wealth_df.columns else wealth_df
        wealth_df = pd.concat([wealth_df, new_row], ignore_index=True)

        if st.button("Update Wealth Snapshot"):
            storage.save_terminal_data("wealth.csv", wealth_df)
            st.success("Wealth snapshot saved")

        if not wealth_df.empty:
            plot_df = wealth_df.copy()
            plot_df["Date"] = pd.to_datetime(plot_df["Date"], errors="coerce")
            st.plotly_chart(px.line(plot_df.sort_values("Date"), x="Date", y="Total_PL", markers=True, title="Total P/L Trajectory"), width="stretch")
            st.dataframe(plot_df.sort_values("Date", ascending=False), width="stretch")
