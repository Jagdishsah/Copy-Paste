diff --git a/README.md b/README.md
index f5f79157af50c1afcdf6e8cd9b8328fb09891413..91ed40c4b05108bdbfa667abd160f79e48f2edef 100644
--- a/README.md
+++ b/README.md
@@ -1,2 +1,36 @@
-# TMS_Ledger
-this Github Is Made To Make New Project that will track my all Money Movement and other Aspects In My TMS
+# TMS Ledger (NEPSE)
+
+A Streamlit-based personal trading operations platform for NEPSE (Nepal Stock Exchange) workflows:
+- Cash movement and broker ledger tracking
+- T+2 settlement monitoring
+- Collateral/pledge tracking
+- Broker data analysis and charting tools
+
+## What is new
+This repo now includes an **isolated V2 app** for safer testing:
+- `TMS_Ledger_v2.py` (new testable command center)
+- `core/` modules for cleaner architecture (`config`, `storage`, `analytics`)
+
+Your old app (`TMS_Ledger.py`) is still present, so you can compare and migrate gradually.
+
+## Quick Start
+```bash
+pip install -r requirements.txt
+streamlit run TMS_Ledger_v2.py
+```
+
+## Optional Secrets (`.streamlit/secrets.toml`)
+```toml
+[auth]
+username = "your_user"
+password = "your_password"
+
+[github]
+token = "ghp_xxx"
+repo_name = "owner/repo"
+```
+
+If GitHub config is missing, V2 runs in **local fallback mode** and writes CSV files directly in the project directory.
+
+## Why isolated V2?
+You asked for full freedom to redesign while keeping risk low. So V2 is delivered as a separate runtime target where you can test everything first before replacing old pages.


 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index f5f79157af50c1afcdf6e8cd9b8328fb09891413..91ed40c4b05108bdbfa667abd160f79e48f2edef 100644
--- a/README.md
+++ b/README.md
@@ -1,2 +1,36 @@
-# TMS_Ledger
-this Github Is Made To Make New Project that will track my all Money Movement and other Aspects In My TMS
+# TMS Ledger (NEPSE)
+
+A Streamlit-based personal trading operations platform for NEPSE (Nepal Stock Exchange) workflows:
+- Cash movement and broker ledger tracking
+- T+2 settlement monitoring
+- Collateral/pledge tracking
+- Broker data analysis and charting tools
+
+## What is new
+This repo now includes an **isolated V2 app** for safer testing:
+- `TMS_Ledger_v2.py` (new testable command center)
+- `core/` modules for cleaner architecture (`config`, `storage`, `analytics`)
+
+Your old app (`TMS_Ledger.py`) is still present, so you can compare and migrate gradually.
+
+## Quick Start
+```bash
+pip install -r requirements.txt
+streamlit run TMS_Ledger_v2.py
+```
+
+## Optional Secrets (`.streamlit/secrets.toml`)
+```toml
+[auth]
+username = "your_user"
+password = "your_password"
+
+[github]
+token = "ghp_xxx"
+repo_name = "owner/repo"
+```
+
+If GitHub config is missing, V2 runs in **local fallback mode** and writes CSV files directly in the project directory.
+
+## Why isolated V2?
+You asked for full freedom to redesign while keeping risk low. So V2 is delivered as a separate runtime target where you can test everything first before replacing old pages.





