# Demo data playbook (IBM AML)

## Why this exists
Full unzip of the IBM AML archive is too large. Use capped extraction.

## 1) Extract a capped subset
```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
```
- Output folder: `data/aml_demo`
- Typical size: ~1.1GB
- Includes `manifest.json`

## 2) Load into Postgres
```bash
uv run python scripts/load_aml_demo_to_db.py
```
Default loader behavior:
- creates `transactions` and `accounts` if missing
- truncates those tables first
- loads up to 250k transaction rows
- loads all account rows

## Useful variants
```bash
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 50000 --max-account-rows 50000
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 800000
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 0
uv run python scripts/load_aml_demo_to_db.py --no-truncate
```

## Reset commands
```bash
uv run python scripts/reset_db.py --yes
uv run python scripts/reset_db.py --all-public --yes
```

## Quick verify
```bash
du -sh data/aml_demo
ls -lh data/aml_demo
```
