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


def load_auth_config() -> AuthConfig | None:
    try:
        return AuthConfig(
            username=st.secrets["auth"]["username"],
            password=st.secrets["auth"]["password"],
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
