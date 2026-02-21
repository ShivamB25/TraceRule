# TraceRule — Code style (supplements AGENTS.md)

Only conventions NOT already in AGENTS.md live here.

## General style

- No docstrings on functions or routes. CompiledRule schema has a one-line docstring; nothing else does.
- `str | None` union syntax, never `Optional[str]`.
- Logging: `logger = logging.getLogger(__name__)` at module level, %-style formatting in log calls.
- Naming: snake_case functions, PascalCase classes, underscore-prefixed private functions.
- Import order: stdlib, then third-party, then `from app.xxx import ...`.
- Inline imports in `routes/policies.py` avoid circular deps. Intentional.

## PydanticAI specifics

- Agent deps use plain `@dataclass`, not Pydantic BaseModel.
- Compiler agent: `anthropic_effort="high"`. Explainer agent: `anthropic_effort="medium"`.

## FastAPI specifics

- Routers use `APIRouter(tags=["tag_name"])`.
- 404 errors: `HTTPException(status_code=404, detail="...")`.
- List endpoints return `list[ResponseModel]` built with `.model_validate()` loop.

## Testing

- pytest + pytest-asyncio, `asyncio_mode = "auto"` in `pyproject.toml` (`[tool.pytest.ini_options]`).
- `pythonpath = "."` in `pyproject.toml`.
- `@pytest.mark.asyncio` on all async test functions.
- In-memory SQLite via aiosqlite + StaticPool.
- `app.dependency_overrides[get_db]` swaps the session.
- `autouse=True` fixture runs create_all/drop_all per test.
- httpx `AsyncClient` with `ASGITransport`.
