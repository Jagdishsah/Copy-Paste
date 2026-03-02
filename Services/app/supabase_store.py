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
            "Prefer": "return=representation"
        }
        
        # 🛡️ THE FIX: Send the User's JWT token to pass Row Level Security (RLS)!
        if "access_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state['access_token']}"
        else:
            # Fallback to anon key (API Gateway requires an Authorization header)
            headers["Authorization"] = f"Bearer {self.config.key}"
            
        return headers

    def _endpoint(self) -> str:
        assert self.config is not None
        return f"{self.config.url.rstrip('/')}/rest/v1/{self.config.table}"
        
    def _get_current_user_id(self) -> str | None:
        if "user_id" in st.session_state:
            return st.session_state["user_id"]
        return None

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

    def read_text(self, file_name: str) -> str | None:
        if not self.enabled():
            return None
            
        user_id = self._get_current_user_id()
        if not user_id:
            return None 

        def _op():
            resp = requests.get(
                self._endpoint(),
                headers=self._headers(),
                params={"select": "content", "file_name": f"eq.{file_name}", "user_id": f"eq.{user_id}", "limit": 1},
                timeout=20,
            )
            resp.raise_for_status()
            rows: list[dict[str, Any]] = resp.json() or []
            return rows[0].get("content") if rows else None

        try:
            return self._with_retry(_op)
        except Exception:
            return None

    def write_text(self, file_name: str, content: str) -> None:
        if not self.enabled():
            raise RuntimeError("Supabase is not configured")
            
        user_id = self._get_current_user_id()
        if not user_id:
            raise RuntimeError("Cannot save file: No user logged in.")

        def _op():
            payload = [{"file_name": file_name, "content": content, "user_id": user_id}]
            
            resp = requests.post(
                self._endpoint(),
                # Merge Prefer headers safely
                headers={**self._headers(), "Prefer": "resolution=merge-duplicates"},
                params={"on_conflict": "user_id,file_name"}, 
                json=payload,
                timeout=20,
            )
            resp.raise_for_status()

        self._with_retry(_op)

    def list_paths(self, prefix: str) -> list[str]:
        if not self.enabled():
            return []
            
        user_id = self._get_current_user_id()
        if not user_id:
            return []

        def _op():
            resp = requests.get(
                self._endpoint(),
                headers=self._headers(),
                params={"select": "file_name", "file_name": f"like.{prefix}%", "user_id": f"eq.{user_id}"},
                timeout=20,
            )
            resp.raise_for_status()
            rows: list[dict[str, str]] = resp.json() or []
            return sorted([r.get("file_name", "") for r in rows if r.get("file_name", "").endswith(".csv")])

        try:
            return self._with_retry(_op)
        except Exception:
            return []

    def read_csv(self, file_name: str, columns: list[str]) -> pd.DataFrame:
        text = self.read_text(file_name)
        if not text:
            return pd.DataFrame(columns=columns)
        return pd.read_csv(StringIO(text))

    def write_csv(self, file_name: str, data: pd.DataFrame) -> None:
        self.write_text(file_name, data.to_csv(index=False))
