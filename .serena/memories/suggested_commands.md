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
