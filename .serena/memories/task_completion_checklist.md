# TraceRule — Task Completion Checklist

After completing any coding task, verify the following:

## 1. Type Safety
- [ ] No `Any` types, no `@ts-ignore` equivalents
- [ ] All functions have return type annotations
- [ ] ORM columns use `Mapped[T]` + `mapped_column()`

## 2. Run Tests
```bash
uv run pytest
```
- Tests use in-memory SQLite (aiosqlite) — no PostgreSQL needed
- JSONVariant TypeDecorator ensures JSON compat across both databases

## 3. Linting (ad-hoc, no config)
```bash
uv run ruff check app/ tests/
uv run ruff format --check app/ tests/
```

## 4. Pattern Compliance
- [ ] PydanticAI agents use `@lru_cache` factory, `output_type=`, `result.output`
- [ ] Background tasks use `async_session_factory()` (not `Depends(get_db)`)
- [ ] New routes registered in `app/main.py` with `/api/v1/` prefix
- [ ] ORM response schemas have `model_config = {"from_attributes": True}`
- [ ] No forbidden libraries (LangChain, Celery, Redis, Alembic, etc.)
- [ ] Flat folder structure (no nested DDD directories)

## 5. Import Style
- [ ] stdlib → third-party → app-local ordering
- [ ] Use inline imports if needed to avoid circular deps (see routes/policies.py pattern)

## 6. Server Smoke Test (if applicable)
```bash
uv run uvicorn app.main:app --reload
# Verify http://localhost:8000/docs loads
```
