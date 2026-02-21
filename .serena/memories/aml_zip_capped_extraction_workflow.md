# IBM AML zip capped extraction workflow (2026-02-22)

Zip file:
- `ibm-transactions-for-anti-money-laundering-aml.zip` (~8GB compressed, ~41GB uncompressed)

Do NOT fully unzip. Use:

```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
```

This extracts only selected small files into `data/aml_demo` and keeps output around ~1.1GB.

Profiles:
- `tiny` (smaller output)
- `small` (both HI/LI small transaction CSVs + accounts + patterns)

Script writes `data/aml_demo/manifest.json` so selected files and budget are tracked.

Quick verify:

```bash
du -sh data/aml_demo
ls -lh data/aml_demo
```

To reset DB before fresh demo:

```bash
uv run python scripts/reset_db.py --yes
```