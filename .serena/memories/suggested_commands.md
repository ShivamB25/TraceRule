# TraceRule — Commands

## Dev server
```bash
uv run uvicorn app.main:app --reload
# API docs: http://localhost:8000/docs
# V1 endpoints: /api/v1/
# V3 endpoints: /api/v3/
```

## Dependencies
```bash
uv sync                  # install all
uv add <package>         # add production dep
uv add --dev <package>   # add dev dep
```

## Tests (78 total)
```bash
uv run pytest            # all tests
uv run pytest -v         # verbose
uv run pytest tests/test_ast_compiler.py  # single file
uv run pytest tests/test_v3_scanner.py::test_v3_scan_deterministic_finds_violations  # single test
```

## Linting (no config file)
```bash
uv run ruff check app/ tests/ --ignore E402
uv run ruff format app/ tests/
uv run ruff format --check app/ tests/  # dry-run
```

## Database
```bash
createdb tracerule
# Tables auto-created via Base.metadata.create_all() in lifespan
```

## Docker
```bash
cp .env.example .env
export ANTHROPIC_API_KEY=your_key
docker compose up --build
```

## Demo data
```bash
uv run python scripts/extract_aml_demo.py --profile small --budget-gb 1.5
uv run python scripts/load_aml_demo_to_db.py
uv run python scripts/load_aml_demo_to_db.py --max-trans-rows 50000
uv run python scripts/reset_db.py --yes
uv run python scripts/reset_db.py --all-public --yes
```
