# TraceRule — Task completion checklist

After any coding task, verify:

## 1. Type safety
- No `Any` types
- All functions have return type annotations
- ORM columns use `Mapped[T]` + `mapped_column()`

## 2. Tests
```bash
uv run pytest
```
Tests use in-memory SQLite (aiosqlite). JSONVariant TypeDecorator handles JSON compat across Postgres and SQLite.

## 3. Linting (no config file, run ad-hoc)
```bash
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
```

## 4. Pattern compliance
- PydanticAI agents use `@lru_cache` factory, `output_type=`, `result.output`
- Background tasks use `async_session_factory()`, not `Depends(get_db)`
- New routes registered in `app/main.py` with `/api/v1/` prefix
- ORM response schemas have `model_config = {"from_attributes": True}`
- No forbidden libraries (LangChain, Celery, Redis, Alembic, etc.)
- Flat folder structure, no nested DDD directories

## 5. Import order
stdlib → third-party → app-local. Inline imports OK to break circular deps (see routes/policies.py).

## 6. Smoke test (if applicable)
```bash
uv run uvicorn app.main:app --reload
# Check http://localhost:8000/docs loads
```
