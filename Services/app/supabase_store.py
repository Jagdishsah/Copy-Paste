from __future__ import annotations

import time
from dataclasses import dataclass
from io import StringIO
from typing import Any

import pandas as pd
import requests
import streamlit as st


@dataclass
class SupabaseConfig:
    url: str
    key: str
    table: str = "app_Files"


class SupabaseFileStore:
    def __init__(self, config: SupabaseConfig | None, retry_count: int = 3, retry_backoff_s: float = 0.4):
        self.config = config
        self.retry_count = max(1, retry_count)
        self.retry_backoff_s = max(0.0, retry_backoff_s)

    def enabled(self) -> bool:
        return bool(self.config and self.config.url and self.config.key)

    def _headers(self) -> dict[str, str]:
        assert self.config is not None
        
        headers = {
            "apikey": self.config.key,
            "Content-Type": "application/json",
        }
        
        # Send the User's JWT token to pass Row Level Security (RLS)
        if "access_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state['access_token']}"
        else:
            headers["Authorization"] = f"Bearer {self.config.key}"
            
        return headers

    def _endpoint(self, table_name: str | None = None) -> str:
        assert self.config is not None
        target = table_name or self.config.table
        return f"{self.config.url.rstrip('/')}/rest/v1/{target}"
        
    def _get_current_user_id(self) -> str | None:
        return st.session_state.get("user_id")

    def _with_retry(self, fn):
        err: Exception | None = None
        for i in range(self.retry_count):
            try:
                return fn()
            except Exception as ex:  
                err = ex
                if i < self.retry_count - 1:
                    time.sleep(self.retry_backoff_s * (2**i))
        if err:
            raise err
        return None

    def read_text(self, file_name: str, table: str = "app_Files") -> str | None:
        if not self.enabled():
            return None
            
        user_id = self._get_current_user_id()

        def _op():
            # Build query parameters
            params = {"select": "content", "file_name": f"eq.{file_name}", "limit": 1}
            
            # Only filter by user_id if we are accessing the private table
            if table == "app_Files":
                if not user_id: return None
                params["user_id"] = f"eq.{user_id}"

            resp = requests.get(
                self._endpoint(table),
                headers=self._headers(),
                params=params,
                timeout=20,
            )
            resp.raise_for_status()
            rows: list[dict[str, Any]] = resp.json() or []
            return rows[0].get("content") if rows else None

        try:
            return self._with_retry(_op)
        except Exception:
            return None

    def write_text(self, file_name: str, content: str, table: str = "app_Files") -> None:
        if not self.enabled():
            raise RuntimeError("Supabase is not configured")
            
        user_id = self._get_current_user_id()
        if not user_id:
            raise RuntimeError("Cannot save: No user logged in.")

        def _op():
            if table == "app_Files":
                payload = {"file_name": file_name, "content": content, "user_id": user_id}
                conflict_param = "user_id,file_name"
            else:
                # Public table uses file_name as PK, we track last_updated_by
                payload = {"file_name": file_name, "content": content, "last_updated_by": user_id}
                conflict_param = "file_name"
            
            resp = requests.post(
                self._endpoint(table),
                headers={**self._headers(), "Prefer": "resolution=merge-duplicates"},
                params={"on_conflict": conflict_param}, 
                json=[payload],
                timeout=20,
            )
            resp.raise_for_status()

        self._with_retry(_op)

    def list_paths(self, prefix: str, table: str = "app_Files") -> list[str]:
        if not self.enabled():
            return []
            
        user_id = self._get_current_user_id()

        def _op():
            params = {"select": "file_name", "file_name": f"like.{prefix}%"}
            if table == "app_Files":
                if not user_id: return []
                params["user_id"] = f"eq.{user_id}"

            resp = requests.get(
                self._endpoint(table),
                headers=self._headers(),
                params=params,
                timeout=20,
            )
            resp.raise_for_status()
            rows: list[dict[str, str]] = resp.json() or []
            return sorted([r.get("file_name", "") for r in rows if r.get("file_name", "").endswith(".csv")])

        try:
            return self._with_retry(_op)
        except Exception:
            return []

    def read_csv(self, file_name: str, columns: list[str], table: str = "app_Files") -> pd.DataFrame:
        text = self.read_text(file_name, table=table)
        if not text:
            return pd.DataFrame(columns=columns)
        return pd.read_csv(StringIO(text))

    def write_csv(self, file_name: str, data: pd.DataFrame, table: str = "app_Files") -> None:
        self.write_text(file_name, data.to_csv(index=False), table=table)
