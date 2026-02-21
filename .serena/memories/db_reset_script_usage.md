# Repeat cleanup workflow (2026-02-21)

Use script in `scripts/reset_db.py` from project root.

## Internal reset (recommended for normal demo reset)

```bash
uv run python scripts/reset_db.py --yes
```

Truncates only:
- policies
- rules
- violations

## Full reset (use when you need to wipe everything)

```bash
uv run python scripts/reset_db.py --all-public --yes
```

Truncates all tables in public schema, including business/demo tables (e.g., employees, transactions).

## Notes
- Without `--yes`, script asks for interactive confirmation.
- Script prints row counts after reset so you can verify immediately.