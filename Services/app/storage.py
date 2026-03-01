from __future__ import annotations

import sqlite3
from io import StringIO
from pathlib import Path

import pandas as pd
from github import Auth, Github

from Services.app.config import GitHubConfig, StorageConfig

LEDGER_COLUMNS = [
    "Date",
    "Type",
    "Category",
    "Amount",
    "Status",
    "Due_Date",
    "Ref_ID",
    "Description",
    "Is_Non_Cash",
    "Dispute_Note",
    "Fiscal_Year",
]
HOLDINGS_COLUMNS = ["Symbol", "Total_Qty", "Pledged_Qty", "LTP", "Haircut"]

PATHS = {
    "ledger": "Data/TMS_Data/tms_ledger_master.csv",
    "holdings": "Data/TMS_Data/tms_holdings.csv",
    "tms_trx": "Data/TMS_Data/tms_trx.csv",
    "portfolio": "Data/User_Data/portfolio.csv",
    "watchlist": "Data/User_Data/watchlist.csv",
    "history": "Data/User_Data/history.csv",
    "diary": "Data/User_Data/diary.csv",
    "wealth": "Data/User_Data/wealth.csv",
    "data_metrics": "Data/User_Data/Data.csv",
    "activity_log": "Data/Logs/activity_log.csv",
    "cache": "Data/Logs/cache.csv",
    "price_log": "Data/Logs/price_log.csv",
    "error_log": "Data/Logs/error_log.csv",
    "stock_data_dir": "Data/Market_Data/Stock_Data",
    "data_analysis_dir": "Data/Market_Data/Data_analysis",
}

TERMINAL_SCHEMAS = {
    "portfolio": ["Symbol", "Sector", "Units", "Total_Cost", "WACC", "Buy_Date", "Stop_Loss", "Notes"],
    "watchlist": ["Symbol", "Target", "Remark"],
    "activity_log": ["Timestamp", "Category", "Symbol", "Action", "Details", "Amount"],
    "history": ["Date", "Buy_Date", "Symbol", "Units", "Buy_Price", "Sell_Price", "Invested_Amount", "Received_Amount", "Net_PL", "PL_Pct", "Reason"],
    "diary": ["Date", "Symbol", "Note", "Emotion", "Mistake", "Strategy"],
    "cache": ["Symbol", "LTP", "Change", "High52", "Low52", "LastUpdated"],
    "wealth": ["Date", "Total_Investment", "Current_Value", "Total_PL", "Day_Change", "Sold_Volume"],
    "price_log": ["Date", "Symbol", "LTP"],
    "data_metrics": ["Date", "Realized_PL", "Realized_PL_Pct", "Unrealized_PL", "Unrealized_PL_Pct"],
    "error_log": ["Date", "Time", "Context", "Error_Message", "Traceback"],
    "tms_trx": ["Date", "Stock", "Type", "Medium", "Amount", "Charge", "Remark", "Reference"],
}


class DataStorage:
    def __init__(self, github_config: GitHubConfig | None, local_root: Path, storage_config: StorageConfig | None = None):
        self.github_config = github_config
        self.local_root = local_root
        self.storage_config = storage_config or StorageConfig()
        self.sqlite_path = (local_root / self.storage_config.sqlite_path).resolve()
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    def _repo(self):
        if not self.github_config:
            return None
        auth = Auth.Token(self.github_config.token)
        return Github(auth=auth).get_repo(self.github_config.repo_name)

    def _table_name(self, logical_key: str) -> str:
        return logical_key.replace("/", "__")

    def _resolve(self, logical_key: str) -> str:
        return PATHS.get(logical_key, logical_key)

    def _read_sqlite(self, logical_key: str, columns: list[str]) -> pd.DataFrame:
        table = self._table_name(logical_key)
        if not self.sqlite_path.exists():
            return pd.DataFrame(columns=columns)
        try:
            with sqlite3.connect(self.sqlite_path) as conn:
                return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)
        except Exception:
            return pd.DataFrame(columns=columns)

    def _save_sqlite(self, logical_key: str, data: pd.DataFrame) -> None:
        table = self._table_name(logical_key)
        with sqlite3.connect(self.sqlite_path) as conn:
            data.to_sql(table, conn, if_exists="replace", index=False)

    def _read(self, logical_key: str, columns: list[str]) -> pd.DataFrame:
        rel_path = self._resolve(logical_key)
        if self.storage_config.backend == "sqlite":
            return self._read_sqlite(logical_key, columns)

        repo = self._repo()
        if repo:
            try:
                file = repo.get_contents(rel_path)
                return pd.read_csv(StringIO(file.decoded_content.decode()))
            except Exception:
                pass

        path = self.local_root / rel_path
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame(columns=columns)

    def _save(self, logical_key: str, data: pd.DataFrame, message: str) -> None:
        rel_path = self._resolve(logical_key)
        if self.storage_config.backend == "sqlite":
            self._save_sqlite(logical_key, data)

        csv_content = data.to_csv(index=False)
        repo = self._repo()
        if repo:
            try:
                file = repo.get_contents(rel_path)
                repo.update_file(file.path, message, csv_content, file.sha)
            except Exception:
                repo.create_file(rel_path, f"Create {rel_path}", csv_content)

        path = self.local_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(csv_content, encoding="utf-8")

    def get_ledger(self) -> pd.DataFrame:
        df = self._read("ledger", LEDGER_COLUMNS)
        if df.empty:
            return pd.DataFrame(columns=LEDGER_COLUMNS)
        for c in ["Date", "Due_Date"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
        for col in LEDGER_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[LEDGER_COLUMNS]

    def save_ledger(self, data: pd.DataFrame) -> None:
        save_df = data.copy()
        save_df["Date"] = pd.to_datetime(save_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        save_df["Due_Date"] = pd.to_datetime(save_df["Due_Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        self._save("ledger", save_df[LEDGER_COLUMNS], "Update Ledger Master")

    def get_holdings(self) -> pd.DataFrame:
        df = self._read("holdings", HOLDINGS_COLUMNS)
        for col in HOLDINGS_COLUMNS:
            if col not in df.columns:
                df[col] = 0 if col != "Symbol" else ""
        return df[HOLDINGS_COLUMNS]

    def save_holdings(self, data: pd.DataFrame) -> None:
        self._save("holdings", data[HOLDINGS_COLUMNS], "Update Holdings")

    def get_terminal_data(self, logical_key: str) -> pd.DataFrame:
        cols = TERMINAL_SCHEMAS.get(logical_key, [])
        df = self._read(logical_key, cols)
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        return df[cols] if cols else df

    def save_terminal_data(self, logical_key: str, data: pd.DataFrame) -> None:
        cols = TERMINAL_SCHEMAS.get(logical_key)
        if cols:
            for col in cols:
                if col not in data.columns:
                    data[col] = ""
            data = data[cols]
        self._save(logical_key, data, f"Update {logical_key}")

    def list_stock_data_files(self) -> list[str]:
        repo = self._repo()
        rel_dir = PATHS["stock_data_dir"]
        if repo:
            try:
                files = repo.get_contents(rel_dir)
                return sorted([f.name for f in files if f.name.endswith(".csv")])
            except Exception:
                pass
        local_dir = self.local_root / rel_dir
        if local_dir.exists():
            return sorted([f.name for f in local_dir.glob("*.csv")])
        return []

    def get_stock_data(self, filename: str) -> pd.DataFrame:
        safe = filename if filename.endswith(".csv") else f"{filename}.csv"
        return self._read(f"{PATHS['stock_data_dir']}/{safe}", ["Date", "Open", "High", "Low", "Close", "Volume"])
