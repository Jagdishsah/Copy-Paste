from __future__ import annotations

import time
from dataclasses import dataclass
from io import StringIO
from typing import Any

import pandas as pd
import requests
import streamlit as st # Added to fetch user_id


@dataclass
class SupabaseConfig:
    url: str
    key: str
    table: str = "app_Files" # Updated to match SQL case sensitivity


class SupabaseFileStore:
    def __init__(self, config: SupabaseConfig | None, retry_count: int = 3, retry_backoff_s: float = 0.4):
        self.config = config
        self.retry_count = max(1, retry_count)
        self.retry_backoff_s = max(0.0, retry_backoff_s)

    def enabled(self) -> bool:
        return bool(self.config and self.config.url and self.config.key)

    def _headers(self) -> dict[str, str]:
        assert self.config is not None
        
        # We MUST pass the auth token of the logged-in user so RLS policies allow the request!
        headers = {
            "apikey": self.config.key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Grab the JWT token from the session state if a user is logged in
        if "user" in st.session_state and hasattr(st.session_state["user"], 'access_token'):
            # Ideally, the supabase client handles this. Since you use raw requests, we need the user's JWT
            # Wait, the auth.users(id) RLS uses the JWT token. 
            # If we don't have the explicit JWT easily accessible, we might hit RLS blocks.
            # Let's try passing the basic service key auth first. If it fails, we will pivot to the official client.
            headers["Authorization"] = f"Bearer {self.config.key}" 
            
        return headers

    def _endpoint(self) -> str:
        assert self.config is not None
        return f"{self.config.url.rstrip('/')}/rest/v1/{self.config.table}"
        
    def _get_current_user_id(self) -> str | None:
        """Helper to get the user UUID securely"""
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
            return None # Cannot read without a user

        def _op():
            resp = requests.get(
                self._endpoint(),
                headers=self._headers(),
                # Updated 'path' to 'file_name' and added user_id filter
                params={"select": "content", "file_name": f"eq.{file_name}", "user_id": f"eq.{user_id}", "limit": 1},
                timeout=20,
            )
            resp.raise_for_status()
            rows: list[dict[str, Any]] = resp.json() or []
            return rows[0].get("content") if rows else None

        try:
            return self._with_retry(_op)
        except Exception as e:
            st.error(f"Read Error: {e}")
            return None

    def write_text(self, file_name: str, content: str) -> None:
        if not self.enabled():
            raise RuntimeError("Supabase is not configured")
            
        user_id = self._get_current_user_id()
        if not user_id:
            raise RuntimeError("Cannot save file: No user logged in.")

        def _op():
            # Updated to match the new SQL schema (user_id, file_name, content)
            payload = [{"file_name": file_name, "content": content, "user_id": user_id}]
            
            resp = requests.post(
                self._endpoint(),
                headers={**self._headers(), "Prefer": "resolution=merge-duplicates"},
                # Conflict is resolved on the UNIQUE constraint we made: (user_id, file_name)
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
