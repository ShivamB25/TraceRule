import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@patch("app.routes.policies.ingest_policy", new_callable=AsyncMock, return_value=1)
async def test_upload_creates_policy_record(mock_ingest, async_client, db_session):
    response = await async_client.post(
        "/api/v1/policies/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 fake content", "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert data["status"] == "processing"
    assert "id" in data


@pytest.mark.asyncio
@patch("app.routes.policies.ingest_policy", new_callable=AsyncMock, return_value=1)
async def test_upload_markdown_creates_policy_record(
    mock_ingest, async_client, db_session
):
    response = await async_client.post(
        "/api/v1/policies/upload",
        files={"file": ("policy.md", b"# Policy\n\nRule text", "text/markdown")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "policy.md"
    assert data["status"] == "processing"
    assert "id" in data


@pytest.mark.asyncio
async def test_upload_without_file_returns_422(async_client):
    response = await async_client.post("/api/v1/policies/upload")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_unsupported_extension_returns_400(async_client):
    response = await async_client.post(
        "/api/v1/policies/upload",
        files={"file": ("policy.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
