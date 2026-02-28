# Copy-Paste — NEPSE Integrated Terminal

A modular Streamlit platform for NEPSE with fully connected data flows between ledger, smart transaction entry, holdings, analytics, and research tools.

## What's improved
- **Integrated Transaction Center**: Smart entry updates ledger + holdings together.
- **Research Hub**: Data Studio, AI Advisor, Advanced Analysis, Stock Graph, and Elliott Scanner merged under one unified tab with subtabs.
- **Flexible secrets auth**: supports both old (`[auth]`) and new (`app_username`, `app_password`) secret formats.
- **GitHub-backed or local mode** persistence.

## Run locally
```bash
pip install -r requirements.txt
streamlit run TMS_Ledger.py
```

## Streamlit secrets format
```toml
app_username = "your_user"
app_password = "your_password"

[github]
token = "ghp_xxx"
repo_name = "Jagdishsah/Copy-Paste"

[gemini]
api_key = "your_gemini_key"
```

(Older auth format still supported)
```toml
[auth]
username = "your_user"
password = "your_password"
```
