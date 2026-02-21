import pytest

from app.models import Policy, Rule, Violation


async def _seed_violation(db_session, **overrides):
    policy = Policy(filename="test.pdf", markdown_text="Test", status="completed")
    db_session.add(policy)
    await db_session.flush()

    rule = Rule(
        policy_id=policy.id,
        title="Must be 18",
        source_quote="Employees must be 18.",
        compiled_sql="SELECT id FROM employees WHERE age < 18",
        status="approved",
    )
    db_session.add(rule)
    await db_session.flush()

    defaults = dict(
        rule_id=rule.id,
        record_pk="42",
        violating_data={"id": 42, "age": 16, "name": "Jane"},
        ai_explanation="Jane is 16, below the minimum age of 18.",
        status="open",
    )
    defaults.update(overrides)
    violation = Violation(**defaults)
    db_session.add(violation)
    await db_session.commit()
    return violation, rule


@pytest.mark.asyncio
async def test_list_violations_empty(async_client):
    response = await async_client.get("/api/v1/violations")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_violations_returns_seeded(async_client, db_session):
    await _seed_violation(db_session)
    response = await async_client.get("/api/v1/violations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["record_pk"] == "42"
    assert data[0]["violating_data"]["age"] == 16


@pytest.mark.asyncio
async def test_list_violations_filter_by_rule_id(async_client, db_session):
    violation, rule = await _seed_violation(db_session)
    response = await async_client.get(f"/api/v1/violations?rule_id={rule.id}")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await async_client.get("/api/v1/violations?rule_id=9999")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_violations_filter_by_status(async_client, db_session):
    await _seed_violation(db_session, status="open")
    response = await async_client.get("/api/v1/violations?status=open")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await async_client.get("/api/v1/violations?status=resolved")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_violation_by_id(async_client, db_session):
    violation, _ = await _seed_violation(db_session)
    response = await async_client.get(f"/api/v1/violations/{violation.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == violation.id
    assert data["ai_explanation"] is not None


@pytest.mark.asyncio
async def test_get_violation_not_found(async_client):
    response = await async_client.get("/api/v1/violations/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_scan_no_approved_rules(async_client):
    response = await async_client.post("/api/v1/scan")
    assert response.status_code == 200
    assert response.json()["violations_found"] == 0
