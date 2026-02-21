# TraceRule — Code Style & Conventions

## General Style
- **No docstrings** on functions/routes (except CompiledRule schema which has a one-line docstring)
- **Type hints everywhere** — return types on all functions, `Mapped[T]` for ORM columns, `str | None` union syntax (not Optional)
- **No `Any`** type hints — explicit types only
- **Logging**: `logger = logging.getLogger(__name__)` at module level, `logger.info/error` with %-style formatting
- **Naming**: snake_case functions, PascalCase classes, _prefixed private functions
- **Imports**: stdlib first, then third-party, then app-local (`from app.xxx import ...`)
- **Inline imports** used in routes/policies.py to avoid circular deps — intentional pattern

## PydanticAI Conventions (CRITICAL)
- Constructor: `output_type=` — **NEVER** `result_type=` (deprecated)
- Results: `result.output` — **NEVER** `result.data` (deprecated)
- Extended thinking: `AnthropicModelSettings(anthropic_thinking={"type": "enabled", "budget_tokens": 4000})`
- Dynamic prompts: `@agent.system_prompt` decorator with `RunContext[DepsType]`
- Agent initialization: **MUST** use `@lru_cache(maxsize=1)` factory function — agent validates API key at construction, crashes if missing at import time
- Agent deps: plain `@dataclass`, not Pydantic BaseModel

## SQLAlchemy Conventions
- `DeclarativeBase` + `AsyncAttrs` mixin for Base
- `Mapped[T]` + `mapped_column()` for all columns — no legacy Column()
- `async_sessionmaker(engine, expire_on_commit=False)` — module-level singleton
- Routes use `Depends(get_db)` for session injection
- Background tasks use `async_session_factory()` directly (NOT Depends)
- JSON columns: custom `JSONVariant` TypeDecorator (JSONB on Postgres, JSON on SQLite for test compat)
- Raw SQL via `text()` in scanner — wrapped in try/except
- ORM queries via `select()` in routes

## FastAPI Conventions
- All routes under `/api/v1/` prefix
- Routers: `APIRouter(tags=["tag_name"])`
- Router registration in main.py: `app.include_router(r, prefix="/api/v1")`
- ORM response models: `model_config = {"from_attributes": True}`
- PDF upload: `BackgroundTasks.add_task()` for async processing
- 404 errors: `HTTPException(status_code=404, detail="...")`
- List endpoints return `list[ResponseModel]` with `.model_validate()` loop

## APScheduler Conventions (v3.x, NOT v4)
- `AsyncIOScheduler(timezone="UTC")`
- `scheduler.add_job(fn, IntervalTrigger(minutes=N))`
- Lifecycle managed in FastAPI lifespan context manager
- Job function creates its own DB session via `async_session_factory()`

## Testing Conventions
- pytest + pytest-asyncio with `asyncio_mode = "auto"`
- In-memory SQLite via aiosqlite + StaticPool
- `app.dependency_overrides[get_db]` for DB injection
- `autouse=True` fixture for create_all/drop_all per test
- httpx AsyncClient with ASGITransport for API tests
- `@pytest.mark.asyncio` on all test functions
- `pythonpath = .` in pytest.ini

## Anti-Patterns (FORBIDDEN)
| Don't | Do Instead |
|-------|------------|
| `Agent(..., result_type=X)` | `Agent(..., output_type=X)` |
| `result.data` | `result.output` |
| Module-level `Agent(...)` | `@lru_cache` factory function |
| `Any` type hints | Explicit types |
| Bare `db.execute(text(...))` in scanner | Wrap in try/except |
| `Depends(get_db)` in background tasks | `async_session_factory()` directly |
| Nested DDD directories | Flat folder structure |
| `@app.on_event("startup")` | Lifespan context manager |
| Alembic migrations | `Base.metadata.create_all()` in lifespan |
| LangChain/LangGraph/Instructor/Celery/Redis/Docling | PydanticAI + APScheduler + pymupdf4llm |
