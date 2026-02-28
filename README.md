# Copy-Paste — NEPSE Unified Intelligence Terminal

A fully integrated Streamlit platform for NEPSE that combines TMS ledger operations, holdings synchronization, research tools, and Nepse_Terminal data workflows in one modular app.

## Major redesign
- **Transaction Center** with Smart Entry that updates **ledger + holdings together**.
- **Terminal Hub** absorbed from Nepse_Terminal data model:
  - Portfolio, Watchlist, History, Diary, Cache, Activity, Wealth Curve
  - Unified activity stream merges terminal logs + ledger events.
  - Wealth snapshot derives from integrated ledger/holdings/history state.
- **Research Hub** groups advanced pages into subtabs:
  - Data Studio
  - AI Advisor
  - Advanced Analysis
  - Visual Analysis
  - Stock Graph
  - Elliott Scanner

## Run
```bash
pip install -r requirements.txt
streamlit run TMS_Ledger.py
```

## Secrets (supported)
```toml
app_username = "your_user"
app_password = "your_password"

[github]
token = "ghp_xxx"
repo_name = "Jagdishsah/Copy-Paste"

[gemini]
api_key = "your_gemini_key"
```

Legacy auth format also works:
```toml
[auth]
username = "your_user"
password = "your_password"
```

## Included integrated datasets
- Ledger and holdings: `tms_ledger_master.csv`, `tms_holdings.csv`
- Terminal datasets: `portfolio.csv`, `watchlist.csv`, `activity_log.csv`, `history.csv`, `diary.csv`, `cache.csv`, `wealth.csv`, `price_log.csv`, `Data.csv`, `error_log.csv`, `tms/tms_trx.csv`
