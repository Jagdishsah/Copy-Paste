from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from datetime import timedelta


@dataclass
class LedgerSummary:
    tms_cash_balance: float
    net_cash_invested: float
    collateral_value: float
    trading_power: float
    utilization_rate: float
    today_due: float
    tomorrow_due: float
    day_after_due: float


def fiscal_year_for_nepal(d: date) -> str:
    if d.month >= 7:
        return f"{d.year}/{d.year+1}"
    return f"{d.year-1}/{d.year}"


def calculate_collateral_value(holdings: pd.DataFrame) -> float:
    if holdings.empty:
        return 0.0
    eligible = holdings.copy()
    eligible["NetCollateral"] = (
        eligible["Pledged_Qty"] * eligible["LTP"] * (1 - eligible["Haircut"] / 100)
    )
    return float(eligible["NetCollateral"].sum())


def _calc_due(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    receivable = df[df["Category"] == "RECEIVABLE"]["Amount"].sum()
    payable = df[df["Category"] == "PAYABLE"]["Amount"].sum()
    return float(receivable - payable)


def summarize_ledger(ledger: pd.DataFrame, holdings: pd.DataFrame, today: date) -> LedgerSummary:
    if ledger.empty:
        return LedgerSummary(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    out_categories = ["DEPOSIT", "DIRECT_PAY", "PRIMARY_INVEST", "EXPENSE"]
    money_out = ledger[(ledger["Category"].isin(out_categories)) & (~ledger["Is_Non_Cash"])]["Amount"].sum()
    money_in = ledger[ledger["Category"] == "WITHDRAW"]["Amount"].sum()
    net_cash_invested = float(money_out - money_in)

    tms_credits = ledger[ledger["Category"].isin(["DEPOSIT", "RECEIVABLE", "DIRECT_PAY"])]["Amount"].sum()
    tms_debits = ledger[ledger["Category"].isin(["WITHDRAW", "PAYABLE", "EXPENSE"])]["Amount"].sum()
    tms_cash_balance = float(tms_credits - tms_debits)

    collateral = calculate_collateral_value(holdings)
    trading_power = float(tms_cash_balance + collateral)
    utilization_rate = 0.0
    if trading_power > 0 and tms_cash_balance < 0:
        utilization_rate = min(abs(tms_cash_balance) / trading_power * 100, 100)

    due_col = pd.to_datetime(ledger["Due_Date"], errors="coerce").dt.date
    today_df = ledger[due_col == today]
    tomorrow_df = ledger[due_col == (today + timedelta(days=1))]
    day_after_df = ledger[due_col == (today + timedelta(days=2))]

    return LedgerSummary(
        tms_cash_balance=tms_cash_balance,
        net_cash_invested=net_cash_invested,
        collateral_value=collateral,
        trading_power=trading_power,
        utilization_rate=utilization_rate,
        today_due=_calc_due(today_df),
        tomorrow_due=_calc_due(tomorrow_df),
        day_after_due=_calc_due(day_after_df),
    )
