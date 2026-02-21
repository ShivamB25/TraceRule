# TraceRule — Codebase Structure

## Directory Layout
```
app/
├── main.py              # FastAPI app + lifespan (scheduler + DB init)
├── config.py            # pydantic-settings BaseSettings (.env)
├── database.py          # async engine, session factory, get_db()
├── models.py            # Policy, Rule, Violation (SQLAlchemy async) + JSONVariant TypeDecorator
├── schemas.py           # CompiledRule, PolicyUploadResponse, RuleResponse, RuleStatusUpdate, ViolationResponse, ScanResult
├── agents/
│   ├── compiler.py      # CompilerDeps dataclass, _INSTRUCTIONS, get_compiler_agent() @lru_cache factory
│   └── explainer.py     # get_explainer_agent() @lru_cache factory
├── services/
│   ├── ingestion.py     # _introspect_db_schema(), ingest_policy() — PDF→markdown→compile→save
│   └── scanner.py       # run_deterministic_scan(), _explain_new_violations()
└── routes/
    ├── policies.py      # POST /policies/upload — _background_ingest + upload_policy
    ├── rules.py         # GET /rules, GET /rules/{id}, PATCH /rules/{id}/status, /approve, /reject
    └── violations.py    # GET /violations, GET /violations/{id}, POST /scan

tests/
├── conftest.py          # In-memory SQLite engine, TestingSessionLocal, fixtures (async_client, db_session)
└── test_rules.py        # test_list_rules_empty, test_approve_rule

docs/
└── ARCHITECTURE_RESEARCH.md
```

## Key Symbols

| Symbol | File | Type | Notes |
|--------|------|------|-------|
| `app` | main.py | FastAPI | Lifespan-managed, CORS enabled |
| `lifespan` | main.py | async context manager | DB create_all + APScheduler start/stop |
| `scheduled_scan` | main.py | async func | APScheduler job: creates own session via async_session_factory |
| `Settings` / `settings` | config.py | BaseSettings / instance | env_file=".env" |
| `engine` | database.py | AsyncEngine | Module-level singleton |
| `async_session_factory` | database.py | async_sessionmaker | Module-level singleton, expire_on_commit=False |
| `get_db` | database.py | async generator | FastAPI Depends injection |
| `Base` | models.py | DeclarativeBase + AsyncAttrs | ORM base |
| `JSONVariant` | models.py | TypeDecorator | JSONB on Postgres, JSON on SQLite |
| `Policy` | models.py | ORM | filename, markdown_text, status(processing/completed/failed) |
| `Rule` | models.py | ORM | title, source_quote, severity, compiled_sql, is_deterministic, status(pending_review/approved/rejected) |
| `Violation` | models.py | ORM | rule_id, record_pk, violating_data(JSONB), ai_explanation, status(open) |
| `CompiledRule` | schemas.py | Pydantic BaseModel | Agent output_type for compiler |
| `CompilerDeps` | agents/compiler.py | dataclass | db_schema_context: str |
| `get_compiler_agent` | agents/compiler.py | @lru_cache factory | Agent[CompilerDeps, list[CompiledRule]] with extended thinking |
| `get_explainer_agent` | agents/explainer.py | @lru_cache factory | Agent[None, str] — 2-sentence violation explanations |
| `ingest_policy` | services/ingestion.py | async func | Full pipeline: PDF bytes → markdown → compile → save rules |
| `_introspect_db_schema` | services/ingestion.py | async func | Queries information_schema.columns, skips internal tables |
| `run_deterministic_scan` | services/scanner.py | async func | Execute approved SQL, dedup by rule_id+record_pk, save violations |
| `_explain_new_violations` | services/scanner.py | async func | AI explanations for violations with NULL ai_explanation |

## API Routes (all prefixed /api/v1/)
| Method | Path | Handler | Router file |
|--------|------|---------|-------------|
| POST | /policies/upload | upload_policy | routes/policies.py |
| GET | /rules | list_rules | routes/rules.py |
| GET | /rules/{rule_id} | get_rule | routes/rules.py |
| PATCH | /rules/{rule_id}/status | update_rule_status | routes/rules.py |
| PATCH | /rules/{rule_id}/approve | approve_rule | routes/rules.py |
| PATCH | /rules/{rule_id}/reject | reject_rule | routes/rules.py |
| GET | /violations | list_violations | routes/violations.py |
| GET | /violations/{violation_id} | get_violation | routes/violations.py |
| POST | /scan | trigger_scan | routes/violations.py |
