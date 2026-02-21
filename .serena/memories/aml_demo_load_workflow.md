# AML demo load workflow (2026-02-22)

## 1) Extract capped subset (avoid full unzip)

```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
```

Output: `data/aml_demo` (~1.1GB for small profile)

## 2) Load into Postgres

```bash
uv run python scripts/load_aml_demo_to_db.py
```

Default loader behavior:
- creates `transactions` and `accounts` tables if missing
- truncates those tables before loading
- loads up to 250000 transaction rows
- loads all account rows

## 3) Useful overrides

```bash
# Larger demo set
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 800000

# Load all extracted rows
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 0

# Keep existing rows and append
uv run python scripts/load_aml_demo_to_db.py --no-truncate
```

## 4) Quick reset if needed

```bash
uv run python scripts/reset_db.py --yes
```
