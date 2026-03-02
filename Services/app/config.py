from dataclasses import dataclass

import streamlit as st

from Services.app.supabase_store import SupabaseConfig

@dataclass
class AuthConfig:
    username: str
    password: str

@dataclass
class StorageConfig:
    backend: str = "supabase"
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

def load_supabase_config() -> SupabaseConfig | None:
    # UPDATED: We now check the root SUPABASE_URL and SUPABASE_KEY 
    # that your login system in TMS_Ledger.py uses!
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        if not url or not key:
            # Fallback to check if it's nested in a [supabase] block just in case
            cfg = st.secrets.get("supabase", {})
            url = cfg.get("url")
            key = cfg.get("key") or cfg.get("service_key")
            
        if not url or not key:
            return None
            
        return SupabaseConfig(
            url=str(url),
            key=str(key),
            table="app_Files", # Keep this case-sensitive to match your SQL DB
        )
    except Exception:
        return None

def load_github_config() -> dict[str, str] | None:
    try:
        cfg = st.secrets.get("github", {})
        return {"token": str(cfg["token"]), "repo_name": str(cfg["repo_name"])}
    except Exception:
        return None

def load_storage_config() -> StorageConfig:
    try:
        cfg = st.secrets.get("storage", {})
        return StorageConfig(
            backend=str(cfg.get("backend", "supabase")).lower(),
            sqlite_path=str(cfg.get("sqlite_path", "data/terminal.db")),
        )
    except Exception:
        return StorageConfig()
