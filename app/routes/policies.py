from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import PolicyUploadResponse
from app.services.ingestion import ingest_policy

router = APIRouter(tags=["policies"])


async def _background_ingest(file_bytes: bytes, filename: str, policy_id: int) -> None:
    from app.database import async_session_factory

    async with async_session_factory() as db:
        await ingest_policy(db, file_bytes, filename, policy_id=policy_id)


@router.post("/policies/upload", response_model=PolicyUploadResponse)
async def upload_policy(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> PolicyUploadResponse:
    file_bytes = await file.read()
    filename = file.filename or "unknown.pdf"

    from app.models import Policy

    policy = Policy(filename=filename, markdown_text="", status="processing")
    db.add(policy)
    await db.commit()
    await db.refresh(policy)

    background_tasks.add_task(_background_ingest, file_bytes, filename, policy.id)

    return PolicyUploadResponse(id=policy.id, filename=filename, status="processing")
