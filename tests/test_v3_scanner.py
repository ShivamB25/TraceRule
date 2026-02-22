import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace

from app.models import CompanyRecord, Policy, V3Rule
from app.services.scanner import run_v3_scan


_SCAN_COUNTER = 0


async def _seed_v3_approved_rule(
    db_session,
    compiled_sql="SELECT id FROM company_records WHERE 1=0",
    requires_semantic=False,
):
    global _SCAN_COUNTER
    _SCAN_COUNTER += 1

    policy = Policy(filename="scan.pdf", markdown_text="Scan test", status="completed")
    db_session.add(policy)
    await db_session.flush()

    logic_tree = {
        "logic_type": "AND",
        "children": [
            {"subject_column": "age", "operator": "<", "value": 18},
        ],
    }

    rule = V3Rule(
        policy_id=policy.id,
        rule_id=f"SCAN-{_SCAN_COUNTER}",
        title="Test V3 Rule",
        source_quote="Test quote.",
        target_table="company_records",
        logic_tree_json=logic_tree,
        requires_semantic_scan=requires_semantic,
        compiled_sql=compiled_sql,
        status="approved",
    )
    db_session.add(rule)
    await db_session.commit()
    return rule


async def _seed_company_record(db_session, table_name="employees", **payload_overrides):
    defaults = {"id": 1, "age": 16, "name": "Jane"}
    defaults.update(payload_overrides)
    record = CompanyRecord(
        table_name=table_name,
        data_payload=defaults,
        search_text=" ".join(str(v) for v in defaults.values()),
    )
    db_session.add(record)
    await db_session.commit()
    return record


@pytest.mark.asyncio
async def test_v3_scan_no_rules(db_session):
    mock_factory = AsyncMock()
    result = await run_v3_scan(db_session, mock_factory)
    assert result["deterministic_violations"] == 0
    assert result["semantic_violations"] == 0
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_v3_scan_bad_sql_does_not_crash(db_session):
    await _seed_v3_approved_rule(db_session, compiled_sql="THIS IS NOT VALID SQL")
    mock_factory = AsyncMock()
    result = await run_v3_scan(db_session, mock_factory)
    assert result["deterministic_violations"] == 0


@pytest.mark.asyncio
async def test_v3_scan_empty_result_set(db_session):
    await _seed_v3_approved_rule(
        db_session, compiled_sql="SELECT id FROM company_records WHERE 1=0"
    )
    mock_factory = AsyncMock()
    result = await run_v3_scan(db_session, mock_factory)
    assert result["deterministic_violations"] == 0
    assert result["total"] == 0


@pytest.mark.asyncio
async def test_v3_scan_deterministic_finds_violations(db_session):
    await _seed_company_record(db_session, table_name="employees", age=16, name="Jane")
    await _seed_v3_approved_rule(
        db_session,
        compiled_sql="SELECT id FROM company_records WHERE table_name = 'employees'",
    )
    mock_factory = AsyncMock()
    result = await run_v3_scan(db_session, mock_factory)
    assert result["deterministic_violations"] == 1
    assert result["total"] == 1


@pytest.mark.asyncio
async def test_v3_scan_deterministic_deduplicates(db_session):
    await _seed_company_record(db_session, table_name="employees", age=16, name="Jane")
    await _seed_v3_approved_rule(
        db_session,
        compiled_sql="SELECT id FROM company_records WHERE table_name = 'employees'",
    )
    mock_factory = AsyncMock()

    result1 = await run_v3_scan(db_session, mock_factory)
    assert result1["deterministic_violations"] == 1

    result2 = await run_v3_scan(db_session, mock_factory)
    assert result2["deterministic_violations"] == 0


@pytest.mark.asyncio
async def test_v3_scan_no_compiled_sql_skips(db_session):
    await _seed_v3_approved_rule(db_session, compiled_sql=None)
    mock_factory = AsyncMock()
    result = await run_v3_scan(db_session, mock_factory)
    assert result["deterministic_violations"] == 0


@pytest.mark.asyncio
async def test_v3_scan_endpoint_returns_structure(async_client):
    response = await async_client.post("/api/v3/scan")
    assert response.status_code == 200
    data = response.json()
    assert "deterministic_violations" in data
    assert "semantic_violations" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_v3_scan_semantic_candidates_are_capped(db_session, monkeypatch):
    policy = Policy(
        filename="semantic.pdf", markdown_text="Semantic test", status="completed"
    )
    db_session.add(policy)
    await db_session.flush()

    rule = V3Rule(
        policy_id=policy.id,
        rule_id="SEM-CAP-1",
        title="Semantic Candidate Cap Rule",
        source_quote="Subjective AML clause.",
        target_table="company_records",
        logic_tree_json={
            "logic_type": "AND",
            "children": [
                {
                    "subject_column": "name",
                    "operator": "IS_VAGUE",
                    "value": None,
                    "semantic_rubric": "Potentially suspicious narrative.",
                }
            ],
        },
        requires_semantic_scan=True,
        compiled_sql="SELECT id FROM company_records ORDER BY id",
        status="approved",
    )
    db_session.add(rule)
    await db_session.commit()

    for i in range(5):
        await _seed_company_record(db_session, table_name="company_records", id=100 + i)

    monkeypatch.setattr(
        "app.services.scanner.settings.semantic_candidate_limit_per_rule", 2
    )

    async def _fake_semantic_debate(*args, **kwargs):
        return SimpleNamespace(
            is_violation=True,
            confidence_score=0.91,
            chief_justice_reasoning="Capped semantic verdict",
        )

    monkeypatch.setattr(
        "app.services.scanner.run_semantic_debate", _fake_semantic_debate
    )

    mock_factory = AsyncMock()
    result = await run_v3_scan(db_session, mock_factory)

    assert result["semantic_violations"] == 2
    assert result["total"] == 2
