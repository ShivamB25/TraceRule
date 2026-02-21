import pytest
from unittest.mock import AsyncMock, patch

from app.models import Policy, Rule
from app.services.scanner import run_deterministic_scan


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
