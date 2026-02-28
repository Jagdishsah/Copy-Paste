from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
from github import Auth, Github

from app.config import GitHubConfig

LEDGER_FILE = "tms_ledger_master.csv"
HOLDINGS_FILE = "tms_holdings.csv"
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


class DataStorage:
    def __init__(self, github_config: GitHubConfig | None, local_root: Path):
        self.github_config = github_config
        self.local_root = local_root

    def _repo(self):
        if not self.github_config:
            return None
        auth = Auth.Token(self.github_config.token)
        return Github(auth=auth).get_repo(self.github_config.repo_name)

    def _read_csv(self, filename: str, columns: list[str]) -> pd.DataFrame:
        repo = self._repo()
        if repo:
            try:
                file = repo.get_contents(filename)
                return pd.read_csv(StringIO(file.decoded_content.decode()))
            except Exception:
                pass

        path = self.local_root / filename
        if path.exists():
            return pd.read_csv(path)
        return pd.DataFrame(columns=columns)

    def _save_csv(self, filename: str, data: pd.DataFrame, message: str) -> None:
        csv_content = data.to_csv(index=False)
        repo = self._repo()
        if repo:
            try:
                file = repo.get_contents(filename)
                repo.update_file(file.path, message, csv_content, file.sha)
            except Exception:
                repo.create_file(filename, f"Create {filename}", csv_content)
        (self.local_root / filename).write_text(csv_content, encoding="utf-8")

    def get_ledger(self) -> pd.DataFrame:
        df = self._read_csv(LEDGER_FILE, LEDGER_COLUMNS)
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
        save_df["Date"] = pd.to_datetime(save_df["Date"]).dt.strftime("%Y-%m-%d")
        save_df["Due_Date"] = pd.to_datetime(save_df["Due_Date"]).dt.strftime("%Y-%m-%d")
        self._save_csv(LEDGER_FILE, save_df[LEDGER_COLUMNS], "Update Ledger Master")

    def get_holdings(self) -> pd.DataFrame:
        df = self._read_csv(HOLDINGS_FILE, HOLDINGS_COLUMNS)
        for col in HOLDINGS_COLUMNS:
            if col not in df.columns:
                df[col] = 0 if col != "Symbol" else ""
        return df[HOLDINGS_COLUMNS]

    def save_holdings(self, data: pd.DataFrame) -> None:
        self._save_csv(HOLDINGS_FILE, data[HOLDINGS_COLUMNS], "Update Holdings")
