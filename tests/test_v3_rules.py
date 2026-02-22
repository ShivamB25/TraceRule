import pytest

from app.models import Policy, V3Rule


_RULE_COUNTER = 0


async def _seed_v3_rule(db_session, **overrides):
    global _RULE_COUNTER
    _RULE_COUNTER += 1

    policy = Policy(filename="test.pdf", markdown_text="Test", status="completed")
    db_session.add(policy)
    await db_session.flush()

    logic_tree = {
        "logic_type": "AND",
        "children": [
            {"subject_column": "age", "operator": "<", "value": 18},
        ],
    }

    defaults = dict(
        policy_id=policy.id,
        rule_id=f"TEST-{_RULE_COUNTER}",
        title="Must be 18",
        source_quote="Employees must be at least 18 years old.",
        target_table="company_records",
        logic_tree_json=logic_tree,
        compiled_sql="SELECT id FROM company_records WHERE 1=0",
        status="pending_review",
    )
    defaults.update(overrides)
    rule = V3Rule(**defaults)
    db_session.add(rule)
    await db_session.commit()
    return rule


@pytest.mark.asyncio
async def test_list_v3_rules_empty(async_client):
    response = await async_client.get("/api/v3/rules")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_v3_rules_returns_seeded(async_client, db_session):
    await _seed_v3_rule(db_session)
    response = await async_client.get("/api/v3/rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Must be 18"
    assert data[0]["target_table"] == "company_records"
    assert data[0]["logic_tree_json"] is not None


@pytest.mark.asyncio
async def test_list_v3_rules_filter_by_status(async_client, db_session):
    await _seed_v3_rule(db_session, status="approved", title="Approved V3")
    await _seed_v3_rule(db_session, status="pending_review", title="Pending V3")

    response = await async_client.get("/api/v3/rules?status=approved")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Approved V3"


@pytest.mark.asyncio
async def test_list_v3_rules_filter_by_policy_id(async_client, db_session):
    rule = await _seed_v3_rule(db_session)
    response = await async_client.get(f"/api/v3/rules?policy_id={rule.policy_id}")
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = await async_client.get("/api/v3/rules?policy_id=9999")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_v3_rule_by_id(async_client, db_session):
    rule = await _seed_v3_rule(db_session)
    response = await async_client.get(f"/api/v3/rules/{rule.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rule.id
    assert data["rule_id"] == rule.rule_id


@pytest.mark.asyncio
async def test_get_v3_rule_not_found(async_client):
    response = await async_client.get("/api/v3/rules/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_v3_rule(async_client, db_session):
    rule = await _seed_v3_rule(db_session)
    response = await async_client.patch(f"/api/v3/rules/{rule.id}/approve")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rule.id
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_v3_rule(async_client, db_session):
    rule = await _seed_v3_rule(db_session)
    response = await async_client.patch(f"/api/v3/rules/{rule.id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_approve_v3_rule_not_found(async_client):
    response = await async_client.patch("/api/v3/rules/9999/approve")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reject_v3_rule_not_found(async_client):
    response = await async_client.patch("/api/v3/rules/9999/reject")
    assert response.status_code == 404
