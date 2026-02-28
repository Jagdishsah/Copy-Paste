from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd
from github import Auth, Github
from github.Repository import Repository

from core.config import GitHubConfig


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

HOLDING_COLUMNS = ["Symbol", "Total_Qty", "Pledged_Qty", "LTP", "Haircut"]


@dataclass
class LedgerStorage:
    github_config: Optional[GitHubConfig]
    local_root: Path

    def _repo(self) -> Optional[Repository]:
        if not self.github_config:
            return None
        auth = Auth.Token(self.github_config.token)
        client = Github(auth=auth)
        return client.get_repo(self.github_config.repo_name)

    def _read_local_csv(self, path: str, columns: list[str]) -> pd.DataFrame:
        full = self.local_root / path
        if not full.exists():
            return pd.DataFrame(columns=columns)
        return pd.read_csv(full)

    def _write_local_csv(self, path: str, df: pd.DataFrame) -> None:
        full = self.local_root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(full, index=False)

    def read_csv(self, path: str, columns: list[str]) -> pd.DataFrame:
        repo = self._repo()
        if repo is None:
            return self._read_local_csv(path, columns)

        try:
            file = repo.get_contents(path)
            return pd.read_csv(StringIO(file.decoded_content.decode("utf-8")))
        except Exception:
            return self._read_local_csv(path, columns)

    def upsert_csv(self, path: str, df: pd.DataFrame, message: str) -> None:
        self._write_local_csv(path, df)
        repo = self._repo()
        if repo is None:
            return

        csv_data = df.to_csv(index=False)
        try:
            file = repo.get_contents(path)
            repo.update_file(file.path, message, csv_data, file.sha)
        except Exception:
            repo.create_file(path, message, csv_data)

    def get_ledger(self) -> pd.DataFrame:
        df = self.read_csv("tms_ledger_master.csv", LEDGER_COLUMNS)
        if df.empty:
            return pd.DataFrame(columns=LEDGER_COLUMNS)

        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
        df["Due_Date"] = pd.to_datetime(df["Due_Date"], errors="coerce").dt.date
        df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0.0)
        if "Is_Non_Cash" in df.columns:
            df["Is_Non_Cash"] = df["Is_Non_Cash"].fillna(False).astype(bool)
        return df

    def save_ledger(self, df: pd.DataFrame) -> None:
        save_df = df.copy()
        save_df["Date"] = pd.to_datetime(save_df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        save_df["Due_Date"] = pd.to_datetime(save_df["Due_Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        self.upsert_csv("tms_ledger_master.csv", save_df, "Update ledger from v2")

    def get_holdings(self) -> pd.DataFrame:
        df = self.read_csv("tms_holdings.csv", HOLDING_COLUMNS)
        if df.empty:
            return pd.DataFrame(columns=HOLDING_COLUMNS)
        df["Pledged_Qty"] = pd.to_numeric(df["Pledged_Qty"], errors="coerce").fillna(0)
        df["LTP"] = pd.to_numeric(df["LTP"], errors="coerce").fillna(0.0)
        df["Haircut"] = pd.to_numeric(df["Haircut"], errors="coerce").fillna(25)
        return df

    def save_holdings(self, df: pd.DataFrame) -> None:
        self.upsert_csv("tms_holdings.csv", df, "Update holdings from v2")
