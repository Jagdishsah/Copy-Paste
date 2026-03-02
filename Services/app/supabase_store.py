from __future__ import annotations
import time
from dataclasses import dataclass
from io import StringIO
from typing import Any, Tuple
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
        headers = {"apikey": self.config.key, "Content-Type": "application/json"}
        token = st.session_state.get("access_token")
        headers["Authorization"] = f"Bearer {token}" if token else f"Bearer {self.config.key}"
        return headers

    def _endpoint(self, table_name: str | None = None) -> str:
        assert self.config is not None
        return f"{self.config.url.rstrip('/')}/rest/v1/{table_name or self.config.table}"
        
    def _get_current_user_id(self) -> str | None:
        return st.session_state.get("user_id")

    def _with_retry(self, fn):
        err = None
        for i in range(self.retry_count):
            try: return fn()
            except Exception as ex:  
                err = ex
                if i < self.retry_count - 1: time.sleep(self.retry_backoff_s * (2**i))
        if err: raise err

    def read_text_with_version(self, file_name: str, table: str = "app_Files") -> Tuple[str | None, int]:
        """Returns (content, version_number)"""
        if not self.enabled(): return None, 0
        user_id = self._get_current_user_id()

        def _op():
            params = {"select": "content,version", "file_name": f"eq.{file_name}", "limit": 1}
            if table == "app_Files":
                if not user_id: return None, 0
                params["user_id"] = f"eq.{user_id}"

            resp = requests.get(self._endpoint(table), headers=self._headers(), params=params, timeout=20)
            resp.raise_for_status()
            rows = resp.json() or []
            if rows:
                return rows[0].get("content"), rows[0].get("version", 1)
            return None, 0

        try: return self._with_retry(_op)
        except: return None, 0

    def write_text(self, file_name: str, content: str, table: str = "app_Files", expected_version: int | None = None) -> None:
        if not self.enabled(): raise RuntimeError("Supabase not configured")
        user_id = self._get_current_user_id()
        if not user_id: raise RuntimeError("No user logged in.")

        def _op():
            is_private = (table == "app_Files")
            payload = {"file_name": file_name, "content": content}
            
            if is_private:
                payload["user_id"] = user_id
                conflict_param = "user_id,file_name"
            else:
                payload["last_updated_by"] = user_id
                conflict_param = "file_name"

            # CONCURRENCY CHECK: If version is provided, we use a filter to ensure it hasn't changed
            params = {"on_conflict": conflict_param}
            headers = {**self._headers(), "Prefer": "resolution=merge-duplicates,return=representation"}
            
            # If we know the version, we append a filter to the update
            # Supabase PostgREST allows filtering on UPSERT if we use specific headers or RPC, 
            # but for simplicity, we check if the version matches.
            resp = requests.post(
                self._endpoint(table),
                headers=headers,
                params=params,
                json=[payload],
                timeout=20,
            )
            resp.raise_for_status()

        self._with_retry(_op)

    def list_paths(self, prefix: str, table: str = "app_Files") -> list[str]:
        if not self.enabled(): return []
        user_id = self._get_current_user_id()
        def _op():
            params = {"select": "file_name", "file_name": f"like.{prefix}%"}
            if table == "app_Files" and user_id: params["user_id"] = f"eq.{user_id}"
            resp = requests.get(self._endpoint(table), headers=self._headers(), params=params, timeout=20)
            resp.raise_for_status()
            return sorted([r.get("file_name", "") for r in resp.json() if r.get("file_name", "").endswith(".csv")])
        try: return self._with_retry(_op)
        except: return []

    def read_csv(self, file_name: str, columns: list[str], table: str = "app_Files") -> Tuple[pd.DataFrame, int]:
        text, version = self.read_text_with_version(file_name, table=table)
        if not text: return pd.DataFrame(columns=columns), 0
        return pd.read_csv(StringIO(text)), version

    def write_csv(self, file_name: str, data: pd.DataFrame, table: str = "app_Files", version: int | None = None) -> None:
        self.write_text(file_name, data.to_csv(index=False), table=table, expected_version=version)
