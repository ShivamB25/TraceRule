import pytest

from app.models import CompanyRecord, Policy, V3Rule, V3Violation


_VIO_COUNTER = 0


async def _seed_v3_violation(db_session, **overrides):
    global _VIO_COUNTER
    _VIO_COUNTER += 1

    policy = Policy(filename="test.pdf", markdown_text="Test", status="completed")
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
        rule_id=f"VIO-{_VIO_COUNTER}",
        title="Must be 18",
        source_quote="Employees must be 18.",
        target_table="company_records",
        logic_tree_json=logic_tree,
        compiled_sql="SELECT id FROM company_records WHERE 1=0",
        status="approved",
    )
    db_session.add(rule)
    await db_session.flush()

    record = CompanyRecord(
        table_name="employees",
        data_payload={"id": 42, "age": 16, "name": "Jane"},
        search_text="Jane 16 employee",
    )
    db_session.add(record)
    await db_session.flush()

    defaults = dict(
        v3_rule_id=rule.id,
        record_id=record.id,
        violation_data={"id": 42, "age": 16, "name": "Jane"},
        verdict_reasoning="Deterministic SQL match",
        confidence_score=1.0,
        status="open",
    )
    defaults.update(overrides)
    violation = V3Violation(**defaults)
    db_session.add(violation)
    await db_session.commit()
    return violation, rule, record


@pytest.mark.asyncio
async def test_list_v3_violations_empty(async_client):
    response = await async_client.get("/api/v3/violations")
    assert response.status_code == 200
    data = response.json()
    assert data == {"items": [], "total_count": 0, "limit": 50, "offset": 0}


@pytest.mark.asyncio
async def test_list_v3_violations_returns_seeded(async_client, db_session):
    await _seed_v3_violation(db_session)
    response = await async_client.get("/api/v3/violations")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert data["items"][0]["violation_data"]["age"] == 16
    assert data["items"][0]["confidence_score"] == 1.0


@pytest.mark.asyncio
async def test_list_v3_violations_filter_by_rule_id(async_client, db_session):
    violation, rule, _ = await _seed_v3_violation(db_session)
    response = await async_client.get(f"/api/v3/violations?v3_rule_id={rule.id}")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1

    response = await async_client.get("/api/v3/violations?v3_rule_id=9999")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_list_v3_violations_filter_by_status(async_client, db_session):
    await _seed_v3_violation(db_session, status="open")
    response = await async_client.get("/api/v3/violations?status=open")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1

    response = await async_client.get("/api/v3/violations?status=resolved")
    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_list_v3_violations_pagination(async_client, db_session):
    await _seed_v3_violation(db_session)
    await _seed_v3_violation(db_session)
    await _seed_v3_violation(db_session)

    response = await async_client.get("/api/v3/violations?limit=2&offset=1")
    assert response.status_code == 200

    data = response.json()
    assert data["total_count"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_v3_violation_by_id(async_client, db_session):
    violation, _, _ = await _seed_v3_violation(db_session)
    response = await async_client.get(f"/api/v3/violations/{violation.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == violation.id
    assert data["verdict_reasoning"] is not None


@pytest.mark.asyncio
async def test_get_v3_violation_not_found(async_client):
    response = await async_client.get("/api/v3/violations/9999")
    assert response.status_code == 404
