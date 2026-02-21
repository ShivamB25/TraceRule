# TraceRule — Suggested Commands

## Development
```bash
# Start dev server (auto-reload)
uv run uvicorn app.main:app --reload

# API docs
open http://localhost:8000/docs
```

## Dependency Management
```bash
# Install all deps (including dev)
uv sync

# Add production dependency
uv add <package>

# Add dev dependency
uv add --dev <package>
```

## Testing
```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_rules.py

# Run specific test
uv run pytest tests/test_rules.py::test_list_rules_empty
```

## Database
```bash
# Create PostgreSQL database
createdb tracerule

# Tables are auto-created via Base.metadata.create_all() in lifespan — no migrations needed
```

## Linting (Ruff — no config file, run ad-hoc)
```bash
uv run ruff check app/
uv run ruff format app/
```

## Environment Setup
```bash
cp .env.example .env
# Then set ANTHROPIC_API_KEY in .env
```

## System Utils (macOS/Darwin)
```bash
git status / git diff / git log
ls -la
find . -name "*.py"
grep -r "pattern" app/
```
