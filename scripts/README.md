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

## Extract AML Demo Subset (1-2 GB)

Use `extract_aml_demo.py` to extract only a capped subset from the IBM AML zip.

Default command (about 1.1 GB output):

```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
```

Output folder:

- `data/aml_demo/`
- includes a `manifest.json` with selected files and size

Profiles:

- `tiny` -> one small transaction file + accounts + patterns
- `small` -> both small transaction files + accounts + patterns

Examples:

```bash
# Keep it around ~0.6 GB
uv run python scripts/extract_aml_demo.py --profile tiny --budget-gb 0.8

# Try full small profile but cap to 1.2 GB
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.2
```
