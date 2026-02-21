import pytest

from app.models import Policy, Rule


@pytest.mark.asyncio
async def test_list_rules_empty(async_client):
    response = await async_client.get("/api/v1/rules")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_approve_rule(async_client, db_session):
    policy = Policy(filename="test.pdf", markdown_text="Test", status="completed")
    db_session.add(policy)
    await db_session.flush()

    rule = Rule(
        policy_id=policy.id,
        title="Must be 18",
        source_quote="Employees must be 18.",
        compiled_sql="SELECT id FROM employees WHERE age < 18",
        status="pending_review",
    )
    db_session.add(rule)
    await db_session.commit()

    response = await async_client.patch(f"/api/v1/rules/{rule.id}/approve")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rule.id
    assert data["status"] == "approved"

    await db_session.refresh(rule)
    assert rule.status == "approved"
