# TraceRule — Code Style & Conventions

## General

- `str | None` union syntax, never `Optional[str]`
- `logger = logging.getLogger(__name__)` at module level, %-style formatting
- snake_case functions, PascalCase classes, underscore-prefixed privates
- Import order: stdlib → third-party → `from app.xxx`
- Inline imports to break circular deps (routes/policies.py, api/router.py)
- No unnecessary docstrings/comments. Section dividers (---) for V1/V3 separation in shared files.

## PydanticAI (v1.0.5+)

- Constructor: `output_type=` (NEVER `result_type=`)
- Results: `result.output` (NEVER `result.data`)
- Validators: `@agent.output_validator` (NEVER `@result_validator`)
- Agent deps: plain `@dataclass`, not Pydantic BaseModel
- Agent factories: `@lru_cache(maxsize=1)` — agent validates API key at construction
- Dynamic prompts: `@agent.system_prompt` with `RunContext[DepsType]`
- Thinking config: `AnthropicModelSettings(anthropic_thinking={...})`
  - Compiler: `{"type": "adaptive"}`, `anthropic_effort="high"`
  - Extractor: `{"type": "enabled", "budget_tokens": 16000}`
  - Courtroom Prosecutor/Defender: `{"type": "enabled", "budget_tokens": 8000}`
  - Courtroom Chief Justice: `{"type": "enabled", "budget_tokens": 16000}`
  - Explainer: `{"type": "adaptive"}`, `anthropic_effort="medium"`
- Self-healing: `@output_validator` + `ModelRetry` with Postgres stack trace (extractor.py)

## SQLAlchemy 2.x async

- `DeclarativeBase` + `AsyncAttrs` mixin
- `Mapped[T]` + `mapped_column()` for all columns
- `async_sessionmaker(engine, expire_on_commit=False)`
- Routes: `Depends(get_db)` | Background tasks: `async_session_factory()` directly
- TypeDecorators for SQLite test compat: `JSONVariant`, `TSVectorVariant`

## FastAPI

- Routers: `APIRouter(tags=["tag_name"])`
- V1 prefix: `/api/v1/` | V3 prefix: `/api/v3/`
- 404: `HTTPException(status_code=404, detail="...")`
- List endpoints: `list[ResponseModel]` built with `.model_validate()` loop
- ORM responses: `model_config = {"from_attributes": True}`
- Policy ingestion: `BackgroundTasks.add_task()`
- Lifespan context manager (NOT `@app.on_event("startup")`)

## Testing

- pytest + pytest-asyncio, `asyncio_mode = "auto"` in pyproject.toml
- `pythonpath = "."` in pyproject.toml
- `@pytest.mark.asyncio` on all async test functions
- In-memory SQLite via aiosqlite + StaticPool
- `app.dependency_overrides[get_db]` swaps session
- `autouse=True` fixture: create_all/drop_all per test
- httpx AsyncClient with ASGITransport
- Mock pattern for upload tests: `@patch("app.services.ingestion.ingest_policy_v3")`

## Forbidden

| Don't | Do Instead |
|-------|------------|
| `Agent(..., result_type=X)` | `Agent(..., output_type=X)` |
| `result.data` | `result.output` |
| Module-level `Agent(...)` | `@lru_cache` factory |
| `Any` type hints | Explicit types |
| `Depends(get_db)` in background | `async_session_factory()` |
| `@app.on_event("startup")` | Lifespan context manager |
| Alembic migrations | `Base.metadata.create_all()` |
| pgvector / numpy | BM25 (ts_rank) for text search |
| LangChain/LangGraph/Instructor | PydanticAI |
