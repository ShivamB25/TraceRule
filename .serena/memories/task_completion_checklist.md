# TraceRule — Task Completion Checklist

After any coding task, verify:

## 1. Tests (78 total)
```bash
uv run pytest -v
```
26 V1 + 50 V3 tests. In-memory SQLite via aiosqlite. No API key needed.

## 2. Lint + Format
```bash
uv run ruff check app/ tests/ --ignore E402
uv run ruff format --check app/ tests/
```

## 3. Type Safety
- No `Any` type hints (except schema field `value: Any | None`)
- All functions have return type annotations
- ORM columns use `Mapped[T]` + `mapped_column()`
- Bool check before numeric in ast_compiler.py (bool subclasses int)

## 4. Pattern Compliance

### PydanticAI
- `output_type=` not `result_type=`
- `result.output` not `result.data`
- `@output_validator` not `@result_validator`
- `@lru_cache(maxsize=1)` factory for agents

### FastAPI
- V1 routes: `/api/v1/` prefix (app/routes/)
- V3 routes: `/api/v3/` prefix (app/api/)
- Background tasks: `async_session_factory()` not `Depends(get_db)`
- ORM responses: `model_config = {"from_attributes": True}`
- Lifespan context manager, not `@app.on_event`

### Models
- TypeDecorators for Postgres/SQLite compat (JSONVariant, TSVectorVariant)
- No pgvector, no VectorVariant, no embedding columns
- No `CREATE EXTENSION vector` in lifespan

### Forbidden
LangChain, LangGraph, Instructor, Celery, Redis, Docling, Alembic, pgvector, numpy

## 5. Import Order
stdlib → third-party → app-local. Inline imports OK for circular deps.
