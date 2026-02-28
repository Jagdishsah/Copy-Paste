# Copy-Paste → TMS Ledger Rebuild

This repository now contains a full TMS Ledger implementation inspired by and imported from:
- https://github.com/Jagdishsah/TMS_Ledger

## What was done
- Migrated core features from `TMS_Ledger` into this repository.
- Refactored the main app into smaller modules and functions under `app/`.
- Preserved all major pages/features:
  - Dashboard
  - New Entry
  - Ledger History
  - Analytics
  - Manage Data
  - Data Analysis
  - AI Advisor
  - Stock Graph
  - Elliott Wave Scanner
- Included supporting scripts/data folders from source project.

## Run
```bash
pip install -r requirements.txt
streamlit run TMS_Ledger.py
```

## Optional Secrets
`.streamlit/secrets.toml`

```toml
[auth]
username = "your_user"
password = "your_password"

[github]
token = "ghp_xxx"
repo_name = "owner/repo"
```

If secrets are not set, app works in local mode with CSV files.
