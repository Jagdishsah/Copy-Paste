from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Any

import pandas as pd
import requests


@dataclass
class SupabaseConfig:
    url: str
    key: str
    table: str = "app_files"


class SupabaseFileStore:
    def __init__(self, config: SupabaseConfig | None):
        self.config = config

    def enabled(self) -> bool:
        return bool(self.config and self.config.url and self.config.key)

    def _headers(self) -> dict[str, str]:
        assert self.config is not None
        return {
            "apikey": self.config.key,
            "Authorization": f"Bearer {self.config.key}",
            "Content-Type": "application/json",
        }

    def _endpoint(self) -> str:
        assert self.config is not None
        return f"{self.config.url.rstrip('/')}/rest/v1/{self.config.table}"

    def read_text(self, path: str) -> str | None:
        if not self.enabled():
            return None
        resp = requests.get(
            self._endpoint(),
            headers=self._headers(),
            params={"select": "content", "path": f"eq.{path}", "limit": 1},
            timeout=20,
        )
        if resp.status_code >= 300:
            return None
        rows: list[dict[str, Any]] = resp.json() or []
        if not rows:
            return None
        return rows[0].get("content")

    def write_text(self, path: str, content: str) -> None:
        if not self.enabled():
            return
        payload = [{"path": path, "content": content}]
        requests.post(
            self._endpoint(),
            headers={**self._headers(), "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "path"},
            json=payload,
            timeout=20,
        ).raise_for_status()

    def list_paths(self, prefix: str) -> list[str]:
        if not self.enabled():
            return []
        resp = requests.get(
            self._endpoint(),
            headers=self._headers(),
            params={"select": "path", "path": f"like.{prefix}%"},
            timeout=20,
        )
        if resp.status_code >= 300:
            return []
        rows: list[dict[str, str]] = resp.json() or []
        return sorted([r.get("path", "") for r in rows if r.get("path", "").endswith(".csv")])

    def read_csv(self, path: str, columns: list[str]) -> pd.DataFrame:
        text = self.read_text(path)
        if not text:
            return pd.DataFrame(columns=columns)
        return pd.read_csv(StringIO(text))

    def write_csv(self, path: str, data: pd.DataFrame) -> None:
        self.write_text(path, data.to_csv(index=False))
