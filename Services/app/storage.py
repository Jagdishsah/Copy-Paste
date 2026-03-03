from __future__ import annotations
import hashlib
from pathlib import Path
import pandas as pd
import streamlit as st
from Services.app.config import StorageConfig
from Services.app.logger import log_event
from Services.app.supabase_store import SupabaseConfig, SupabaseFileStore
from Services.app.domain.models import LedgerEntry, HoldingEntry, TransactionEntry, ActivityLogEntry

# Mapping logical keys to Pydantic Models for Validation
MODEL_MAP = {
    "ledger": LedgerEntry,
    "holdings": HoldingEntry,
    "tms_trx": TransactionEntry,
    "activity_log": ActivityLogEntry
}

LEDGER_COLUMNS = ["Date", "Type", "Category", "Amount", "Status", "Due_Date", "Ref_ID", "Description", "Is_Non_Cash", "Dispute_Note", "Fiscal_Year"]
HOLDINGS_COLUMNS = ["Symbol", "Total_Qty", "Pledged_Qty", "LTP", "Haircut"]

PATHS = {
    "ledger": "Data/TMS_Data/tms_ledger_master.csv",
    "holdings": "Data/TMS_Data/tms_holdings.csv",
    "tms_trx": "Data/TMS_Data/tms_trx.csv",
    "portfolio": "Data/User_Data/portfolio.csv",
    "watchlist": "Data/User_Data/watchlist.csv",
    "history": "Data/User_Data/history.csv",
    "activity_log": "Data/Logs/activity_log.csv",
    "cache": "Data/Logs/cache.csv",
    "price_log": "Data/Logs/price_log.csv",
    "stock_data_dir": "Data/Market_Data/Stock_Data",
    "data_analysis_dir": "Data/Market_Data/Data_analysis",
}

PUBLIC_KEYS = {"cache", "price_log", "stock_data_dir", "data_analysis_dir"}

class DataStorage:
    def __init__(self, supabase_config: SupabaseConfig | None, local_root: Path, storage_config: StorageConfig | None = None):
        self.local_root = local_root
        self.storage_config = storage_config or StorageConfig()
        self.supabase = SupabaseFileStore(supabase_config)
        
        # Initialize version cache in session state
        if "version_cache" not in st.session_state:
            st.session_state["version_cache"] = {}
        if "last_storage_write_ok" not in st.session_state:
            st.session_state["last_storage_write_ok"] = True

    def active_backend(self) -> str:
        """Returns the current active storage backend name for the UI."""
        if self.supabase.enabled() and self.storage_config.backend == "supabase":
            return "Supabase Cloud"
        return "Local Filesystem"
        return "supabase" if self.supabase.enabled() else "csv"

    def last_write_ok(self) -> bool:
        return bool(st.session_state.get("last_storage_write_ok", True))

    def _get_target_table(self, logical_key: str, rel_path: str) -> str:
        is_public = logical_key in PUBLIC_KEYS or any(rel_path.startswith(PATHS.get(k, "NONE")) for k in ["stock_data_dir", "data_analysis_dir"])
        return "public_Files" if is_public else "app_Files"

    def _read(self, logical_key: str, columns: list[str]) -> pd.DataFrame:
        rel_path = PATHS.get(logical_key, logical_key)
        target_table = self._get_target_table(logical_key, rel_path)
        # Add this decorator to your read methods
        @st.cache_data(ttl=300) # Cache for 5 minutes
        def get_cached_prices(self):
            return self._read("cache", ["Symbol", "LTP", "Change"])

        if self.supabase.enabled():
            df, version = self.supabase.read_csv(rel_path, columns, table=target_table)
            try:
                read_result = self.supabase.read_csv(rel_path, columns, table=target_table)
            except TypeError:
                read_result = self.supabase.read_csv(rel_path, columns)
            if isinstance(read_result, tuple):
                df, version = read_result
            else:
                df, version = read_result, 0
            st.session_state["version_cache"][rel_path] = version
            return df
        
        # Fallback to local if needed (optional based on your setup)
        return pd.DataFrame(columns=columns)

    def _save(self, logical_key: str, data: pd.DataFrame, message: str) -> None:
        rel_path = PATHS.get(logical_key, logical_key)
        target_table = self._get_target_table(logical_key, rel_path)
        
        # Validation
        if logical_key in MODEL_MAP:
            model = MODEL_MAP[logical_key]
            try:
                records = data.to_dict('records')
                for rec in records:
                    model(**rec)
            except Exception as e:
                raise ValueError(f"Data Validation Error for {logical_key}: {e}")

        if self.supabase.enabled():
            version = st.session_state["version_cache"].get(rel_path)
            try:
                self.supabase.write_csv(rel_path, data, table=target_table, version=version)
                try:
                    self.supabase.write_csv(rel_path, data, table=target_table, version=version)
                except TypeError:
                    # Compatibility fallback for test doubles / legacy adapters.
                    self.supabase.write_csv(rel_path, data)
                log_event("storage_write", {"path": rel_path, "ok": True})
                st.session_state["last_storage_write_ok"] = True
            except Exception as ex:
                log_event("storage_error", {"path": rel_path, "error": str(ex)})
                st.session_state["last_storage_write_ok"] = False
                raise RuntimeError(f"Cloud Save Failed: {ex}")

    def get_ledger(self) -> pd.DataFrame:
        df = self._read("ledger", LEDGER_COLUMNS)
        if df.empty: return pd.DataFrame(columns=LEDGER_COLUMNS)
        for c in ["Date", "Due_Date"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors='coerce').dt.date
        return df[LEDGER_COLUMNS]

    def save_ledger(self, data: pd.DataFrame) -> None:
        df = data.copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        df["Due_Date"] = pd.to_datetime(df["Due_Date"]).dt.strftime("%Y-%m-%d")
        self._save("ledger", df, "Update Ledger")

    def get_holdings(self) -> pd.DataFrame:
        return self._read("holdings", HOLDINGS_COLUMNS)

    def save_holdings(self, data: pd.DataFrame) -> None:
        self._save("holdings", data, "Update Holdings")

    def import_legacy_csv(self, path: str, df: pd.DataFrame, skip_if_same: bool = False) -> bool:
        """Helper to migrate old local data to the new cloud system."""
        if skip_if_same and self.supabase.enabled():
            existing = self._read(path, columns=list(df.columns))
            if self._frame_digest(existing) == self._frame_digest(df):
                return False
        self._save(path, df, f"Imported legacy data to {path}")
        return True

    @staticmethod
    def _frame_digest(df: pd.DataFrame) -> str:
        normalized = df.fillna("").sort_index(axis=1)
        payload = normalized.to_csv(index=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
