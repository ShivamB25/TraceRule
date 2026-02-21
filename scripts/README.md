# Scripts

## Reset Database Quickly

Use `reset_db.py` to clean demo data without manually running SQL.

From project root:

```bash
uv run python scripts/reset_db.py --yes
```

This clears only internal TraceRule tables:

- `policies`
- `rules`
- `violations`

To wipe every table in `public` schema (including business/demo tables like `employees`):

```bash
uv run python scripts/reset_db.py --all-public --yes
```

Without `--yes`, the script asks for confirmation.
