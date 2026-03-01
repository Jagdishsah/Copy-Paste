from dataclasses import dataclass

import streamlit as st


@dataclass
class AuthConfig:
    username: str
    password: str


@dataclass
class GitHubConfig:
    token: str
    repo_name: str


@dataclass
class StorageConfig:
    backend: str = "csv"  # csv | sqlite
    sqlite_path: str = "data/terminal.db"


def load_auth_config() -> AuthConfig | None:
    try:
        if "auth" in st.secrets:
            return AuthConfig(
                username=st.secrets["auth"]["username"],
                password=st.secrets["auth"]["password"],
            )
        return AuthConfig(
            username=st.secrets["app_username"],
            password=st.secrets["app_password"],
        )
    except Exception:
        return None


def load_github_config() -> GitHubConfig | None:
    try:
        return GitHubConfig(
            token=st.secrets["github"]["token"],
            repo_name=st.secrets["github"]["repo_name"],
        )
    except Exception:
        return None


def load_storage_config() -> StorageConfig:
    try:
        cfg = st.secrets.get("storage", {})
        return StorageConfig(
            backend=str(cfg.get("backend", "csv")).lower(),
            sqlite_path=str(cfg.get("sqlite_path", "data/terminal.db")),
        )
    except Exception:
        return StorageConfig()
