import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import text

from app.models import Policy, Rule, Violation
from app.services.scanner import _explain_new_violations, run_deterministic_scan


async def _seed_approved_rule(db_session, compiled_sql="SELECT 1 AS id WHERE 1=0"):
    policy = Policy(filename="scan.pdf", markdown_text="Scan test", status="completed")
    db_session.add(policy)
    await db_session.flush()

    rule = Rule(
        policy_id=policy.id,
        title="Test Rule",
        source_quote="Test quote.",
        compiled_sql=compiled_sql,
        is_deterministic=True,
        status="approved",
    )
    db_session.add(rule)
    await db_session.commit()
    return rule


@pytest.mark.asyncio
async def test_scan_no_rules(db_session):
    count = await run_deterministic_scan(db_session)
    assert count == 0


@pytest.mark.asyncio
@patch("app.services.scanner._explain_new_violations", new_callable=AsyncMock)
async def test_scan_bad_sql_does_not_crash(mock_explain, db_session):
    await _seed_approved_rule(db_session, compiled_sql="THIS IS NOT VALID SQL")
    count = await run_deterministic_scan(db_session)
    assert count == 0


@pytest.mark.asyncio
async def test_scan_empty_result_set(db_session):
    await _seed_approved_rule(db_session, compiled_sql="SELECT 1 AS id WHERE 1=0")
    count = await run_deterministic_scan(db_session)
    assert count == 0


class _FakeResult:
    def __init__(self, output: str):
        self.output = output


@pytest.mark.asyncio
async def test_explanation_limit_uses_fallback_for_overflow(db_session):
    rule = await _seed_approved_rule(db_session, compiled_sql="SELECT 1 AS id")
    db_session.add(
        Violation(
            rule_id=rule.id,
            record_pk="1",
            violating_data={"id": 1},
            ai_explanation=None,
        )
    )
    db_session.add(
        Violation(
            rule_id=rule.id,
            record_pk="2",
            violating_data={"id": 2},
            ai_explanation=None,
        )
    )
    await db_session.commit()

    fake_agent = AsyncMock()
    fake_agent.run = AsyncMock(return_value=_FakeResult("model explanation"))

    with patch("app.services.scanner.get_explainer_agent", return_value=fake_agent):
        await _explain_new_violations(db_session, max_model_calls=1)

    rows = (
        (
            await db_session.execute(
                text("SELECT ai_explanation FROM violations ORDER BY id ASC")
            )
        )
        .scalars()
        .all()
    )
    assert rows[0] == "model explanation"
    assert rows[1] is not None
    assert "Matched approved deterministic rule" in rows[1]
