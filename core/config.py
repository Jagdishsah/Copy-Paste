from dataclasses import dataclass
from typing import Optional

import streamlit as st


NEPSE_TRADING_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]


@dataclass
class GitHubConfig:
    token: str
    repo_name: str


@dataclass
class AuthConfig:
    username: str
    password: str


def load_github_config() -> Optional[GitHubConfig]:
    try:
        return GitHubConfig(
            token=st.secrets["github"]["token"],
            repo_name=st.secrets["github"]["repo_name"],
        )
    except Exception:
        return None


def load_auth_config() -> Optional[AuthConfig]:
    try:
        return AuthConfig(
            username=st.secrets["auth"]["username"],
            password=st.secrets["auth"]["password"],
        )
    except Exception:
        return None
