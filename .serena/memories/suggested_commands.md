# TraceRule — Commands

## Dev server
```bash
uv run uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
```

## Dependencies
```bash
uv sync                  # install all
uv add <package>         # add production dep
uv add --dev <package>   # add dev dep
```

## Tests
```bash
uv run pytest            # all tests
uv run pytest -v         # verbose
uv run pytest tests/test_rules.py::test_list_rules_empty  # single test
```

## Database
```bash
createdb tracerule
# Tables auto-created via Base.metadata.create_all() in lifespan
```

## Linting (no config file)
```bash
uv run ruff check app/ tests/
uv run ruff format app/ tests/
```

## Docker
```bash
cp .env.example .env
export ANTHROPIC_API_KEY=your_key
docker compose up --build
# API: http://localhost:8000/docs
```

## Environment
```bash
cp .env.example .env
# Set ANTHROPIC_API_KEY in .env
```


## Demo data utilities (2026-02-22)
```bash
# Extract capped subset from 8GB AML zip (~1.1GB output)
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5

# Load AML demo CSVs into Postgres (creates transactions/accounts tables)
uv run python scripts/load_aml_demo_to_db.py

# Load smaller sample for quick iteration
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 50000 --max-account-rows 50000

# Reset only internal app tables (policies/rules/violations)
uv run python scripts/reset_db.py --yes

# Reset all public tables (including employees/transactions/accounts)
uv run python scripts/reset_db.py --all-public --yes

# Verify extracted subset size
du -sh data/aml_demo
ls -lh data/aml_demo
```