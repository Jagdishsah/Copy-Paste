from __future__ import annotations

from io import StringIO

import pandas as pd
import requests
import streamlit as st

from Services.app.config import load_github_config
from Services.app.storage import DataStorage, PATHS


def _github_get_csv(repo: str, token: str, path: str) -> pd.DataFrame | None:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    resp = requests.get(url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.raw+json"}, timeout=30)
    if resp.status_code >= 300:
        return None
    return pd.read_csv(StringIO(resp.text))


def _github_list_dir(repo: str, token: str, path: str) -> list[str]:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    resp = requests.get(url, headers={"Authorization": f"token {token}"}, timeout=30)
    if resp.status_code >= 300:
        return []
    rows = resp.json() or []
    return [item["name"] for item in rows if item.get("name", "").endswith(".csv")]


def render_restore(storage: DataStorage) -> None:
    st.header("♻️ GitHub to Supabase Restore")
    st.caption("One-click migration tool for legacy GitHub CSV files.")

    gh = load_github_config()
    if not gh:
        st.warning("GitHub credentials not configured in Streamlit secrets.")
        return

    if st.button("Restore all GitHub CSV data into Supabase", type="primary"):
        migrated = 0
        failed: list[str] = []
        token = gh["token"]
        repo = gh["repo_name"]

        for key, rel_path in PATHS.items():
            if key.endswith("_dir"):
                continue
            df = _github_get_csv(repo, token, rel_path)
            if df is None:
                failed.append(rel_path)
                continue
            storage._save(rel_path, df, "restore")
            migrated += 1

        for name in _github_list_dir(repo, token, PATHS["stock_data_dir"]):
            rel = f"{PATHS['stock_data_dir']}/{name}"
            df = _github_get_csv(repo, token, rel)
            if df is None:
                failed.append(rel)
                continue
            storage._save(rel, df, "restore")
            migrated += 1

        for name in _github_list_dir(repo, token, PATHS["data_analysis_dir"]):
            rel = f"{PATHS['data_analysis_dir']}/{name}"
            df = _github_get_csv(repo, token, rel)
            if df is None:
                failed.append(rel)
                continue
            storage._save(rel, df, "restore")
            migrated += 1

        st.success(f"Migrated {migrated} CSV files to Supabase/local mirror.")
        if failed:
            st.warning(f"Failed to migrate {len(failed)} files: {', '.join(failed[:8])}")
