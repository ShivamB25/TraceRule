import pytest

from app.models import Policy, Rule


async def _seed_rule(db_session, **overrides):
    policy = Policy(filename="test.pdf", markdown_text="Test", status="completed")
    db_session.add(policy)
    await db_session.flush()

    defaults = dict(
        policy_id=policy.id,
        title="Must be 18",
        source_quote="Employees must be 18.",
        compiled_sql="SELECT id FROM employees WHERE age < 18",
        status="pending_review",
    )
    defaults.update(overrides)
    rule = Rule(**defaults)
    db_session.add(rule)
    await db_session.commit()
    return rule


@pytest.mark.asyncio
async def test_list_rules_empty(async_client):
    response = await async_client.get("/api/v1/rules")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_rules_returns_seeded(async_client, db_session):
    await _seed_rule(db_session)
    response = await async_client.get("/api/v1/rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Must be 18"


@pytest.mark.asyncio
async def test_list_rules_filter_by_status(async_client, db_session):
    await _seed_rule(db_session, status="approved", title="Approved Rule")
    await _seed_rule(db_session, status="pending_review", title="Pending Rule")

    response = await async_client.get("/api/v1/rules?status=approved")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Approved Rule"


@pytest.mark.asyncio
async def test_get_rule_by_id(async_client, db_session):
    rule = await _seed_rule(db_session)
    response = await async_client.get(f"/api/v1/rules/{rule.id}")
    assert response.status_code == 200
    assert response.json()["id"] == rule.id


@pytest.mark.asyncio
async def test_get_rule_not_found(async_client):
    response = await async_client.get("/api/v1/rules/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_rule(async_client, db_session):
    rule = await _seed_rule(db_session)
    response = await async_client.patch(f"/api/v1/rules/{rule.id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rule.id
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_rule(async_client, db_session):
    rule = await _seed_rule(db_session)
    response = await async_client.patch(f"/api/v1/rules/{rule.id}/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_approve_nonexistent_rule(async_client):
    response = await async_client.patch("/api/v1/rules/9999/approve")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_rule_status_via_patch(async_client, db_session):
    rule = await _seed_rule(db_session)
    response = await async_client.patch(
        f"/api/v1/rules/{rule.id}/status",
        json={"status": "approved"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_update_rule_status_invalid(async_client, db_session):
    rule = await _seed_rule(db_session)
    response = await async_client.patch(
        f"/api/v1/rules/{rule.id}/status",
        json={"status": "bogus"},
    )
    assert response.status_code == 400
