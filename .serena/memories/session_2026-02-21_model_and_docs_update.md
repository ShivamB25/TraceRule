Session summary (2026-02-21):

## Model updates
- Compiler agent: `anthropic:claude-sonnet-4-6` with `AnthropicModelSettings(anthropic_thinking={"type":"adaptive"}, anthropic_effort="high")`.
- Explainer agent: same model, `anthropic_effort="medium"`.
- Docs updated (AGENTS.md, README.md, ARCHITECTURE_RESEARCH.md).

## Tests
- 23 tests across 4 files, all passing.
- Files: test_rules.py (10), test_violations.py (8), test_scanner.py (3), test_policies.py (3).

## Live E2E verification
- Full pipeline tested with real Anthropic API + PostgreSQL with 7 employee records.
- PDF upload → 3 rules compiled → approved → scan found 6 violations → AI explanations generated.
- Dedup re-scan confirmed 0 new violations.
- Edge cases (404, 422, 400, filters) all passing.

## Bugs fixed
- API key bridging: pydantic-settings → os.environ for PydanticAI.
- Decimal serialization: `_make_json_safe()` for JSONB insert.
- /scan endpoint: switched from `async_session_factory()` to `Depends(get_db)` for test isolation.
- pytest.ini removed, config consolidated into pyproject.toml.
- Dockerfile rewritten as multi-stage build per uv-docker-example best practices.
- Python version constraint relaxed from >=3.14 to >=3.13.

## Status
Project is feature-complete. No active in-progress changes.