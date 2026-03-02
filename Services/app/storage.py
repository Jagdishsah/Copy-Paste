from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from Services.app.config import StorageConfig
from Services.app.logger import log_event
from Services.app.supabase_store import SupabaseConfig, SupabaseFileStore

LEDGER_COLUMNS = [
    "Date", "Type", "Category", "Amount", "Status", "Due_Date",
    "Ref_ID", "Description", "Is_Non_Cash", "Dispute_Note", "Fiscal_Year",
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

# 🚀 PUBLIC ROUTING: These keys go to 'public_Files' table
PUBLIC_KEYS = {
    "cache", 
    "price_log", 
    "stock_data_dir", 
    "data_analysis_dir"
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
    def __init__(self, supabase_config: SupabaseConfig | None, local_root: Path, storage_config: StorageConfig | None = None):
        self.local_root = local_root
        self.storage_config = storage_config or StorageConfig()
        self.supabase = SupabaseFileStore(supabase_config)
        self.last_write_status: dict[str, str | bool] = {
            "ok": True,
            "backend": self.active_backend(),
            "path": "",
            "remote_ok": True,
            "local_ok": False,
            "error": "",
        }

    def _use_supabase(self) -> bool:
        return self.supabase.enabled()

    def _resolve(self, logical_key: str) -> str:
        return PATHS.get(logical_key, logical_key)

    def _get_target_table(self, logical_key: str, rel_path: str) -> str:
        # Check if key is explicitly public or lives in a public directory
        is_public = (
            logical_key in PUBLIC_KEYS or 
            any(rel_path.startswith(PATHS[k]) for k in ["stock_data_dir", "data_analysis_dir"])
        )
        return "public_Files" if is_public else "app_Files"

    def _read(self, logical_key: str, columns: list[str]) -> pd.DataFrame:
        rel_path = self._resolve(logical_key)
        target_table = self._get_target_table(logical_key, rel_path)

        if self._use_supabase():
            df = self.supabase.read_csv(rel_path, columns, table=target_table)
            if not df.empty:
                return df
                
        return pd.DataFrame(columns=columns)

    def _save(self, logical_key: str, data: pd.DataFrame, message: str) -> None:
        rel_path = self._resolve(logical_key)
        target_table = self._get_target_table(logical_key, rel_path)
        remote_ok = True
        err = ""

        if self._use_supabase():
            try:
                self.supabase.write_csv(rel_path, data, table=target_table)
            except Exception as ex:
                remote_ok = False
                err = f"Supabase write failed: {ex}"
        else:
            remote_ok = False
            err = "Cloud Storage Error: Supabase is not configured."

        self.last_write_status.update({"ok": remote_ok, "path": rel_path, "error": err})

        log_event("storage_write", {"path": rel_path, "table": target_table, "ok": remote_ok, "error": err})

        if not remote_ok:
            raise RuntimeError(err)

    def active_backend(self) -> str:
        return "supabase" if self._use_supabase() else "none_configured"

    def get_ledger(self) -> pd.DataFrame:
        df = self._read("ledger", LEDGER_COLUMNS)
        if df.empty: return pd.DataFrame(columns=LEDGER_COLUMNS)
        for c in ["Date", "Due_Date"]:
            if c in df.columns: df[c] = pd.to_datetime(df[c], errors="coerce").dt.date
        return df

    def save_ledger(self, data: pd.DataFrame) -> None:
        save_df = data.copy()
        save_df["Date"] = pd.to_datetime(save_df["Date"]).dt.strftime("%Y-%m-%d")
        save_df["Due_Date"] = pd.to_datetime(save_df["Due_Date"]).dt.strftime("%Y-%m-%d")
        self._save("ledger", save_df, "Update Ledger")

    def get_holdings(self) -> pd.DataFrame:
        return self._read("holdings", HOLDINGS_COLUMNS)

    def save_holdings(self, data: pd.DataFrame) -> None:
        self._save("holdings", data, "Update Holdings")

    def get_terminal_data(self, logical_key: str) -> pd.DataFrame:
        cols = TERMINAL_SCHEMAS.get(logical_key, [])
        return self._read(logical_key, cols)

    def save_terminal_data(self, logical_key: str, data: pd.DataFrame) -> None:
        self._save(logical_key, data, f"Update {logical_key}")

    def list_stock_data_files(self) -> list[str]:
        rel_dir = PATHS["stock_data_dir"]
        if self._use_supabase():
            # Public routing
            files = self.supabase.list_paths(rel_dir + "/", table="public_Files")
            return sorted([Path(p).name for p in files])
        return []

    def get_stock_data(self, filename: str) -> pd.DataFrame:
        safe = filename if filename.endswith(".csv") else f"{filename}.csv"
        return self._read(f"{PATHS['stock_data_dir']}/{safe}", ["Date", "Open", "High", "Low", "Close", "Volume"])

    def save_stock_data(self, filename: str, data: pd.DataFrame) -> None:
        safe = filename if filename.endswith(".csv") else f"{filename}.csv"
        self._save(f"{PATHS['stock_data_dir']}/{safe}", data, f"Update stock data {safe}")

    def list_analysis_files(self) -> list[str]:
        rel_dir = PATHS["data_analysis_dir"]
        if self._use_supabase():
            # Public routing
            files = self.supabase.list_paths(rel_dir + "/", table="public_Files")
            return sorted([Path(p).name for p in files])
        return []

    def get_analysis_data(self, filename: str) -> pd.DataFrame:
        safe = filename if filename.endswith(".csv") else f"{filename}.csv"
        return self._read(f"{PATHS['data_analysis_dir']}/{safe}", [])

    def save_analysis_data(self, filename: str, data: pd.DataFrame) -> None:
        safe = filename if filename.endswith(".csv") else f"{filename}.csv"
        self._save(f"{PATHS['data_analysis_dir']}/{safe}", data, f"Update analysis data {safe}")
