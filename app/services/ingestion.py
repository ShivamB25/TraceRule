import logging
import tempfile
from pathlib import Path

import pymupdf4llm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.compiler import CompilerDeps, get_compiler_agent
from app.models import Policy, Rule

logger = logging.getLogger(__name__)

_INTERNAL_TABLES = frozenset({"policies", "rules", "violations"})


def _extract_pdf_text(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        raw = pymupdf4llm.to_markdown(str(tmp_path))
        return (
            raw
            if isinstance(raw, str)
            else "\n".join(chunk["text"] for chunk in raw if "text" in chunk)
        )
    finally:
        tmp_path.unlink(missing_ok=True)


def _extract_markdown_text(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("utf-8-sig")


def _extract_policy_text(file_bytes: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_text(file_bytes)
    if suffix in {".md", ".markdown"}:
        return _extract_markdown_text(file_bytes)
    raise ValueError("Unsupported file type. Upload a .pdf or .md file.")


async def _introspect_db_schema(db: AsyncSession) -> str:
    rows = await db.execute(
        text(
            "SELECT table_name, column_name, data_type, "
            "is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "ORDER BY table_name, ordinal_position"
        )
    )

    tables: dict[str, list[str]] = {}
    for row in rows.mappings():
        table = row["table_name"]
        if table in _INTERNAL_TABLES:
            continue
        col = f"  - {row['column_name']} ({row['data_type']}"
        if row["is_nullable"] == "NO":
            col += ", NOT NULL"
        col += ")"
        tables.setdefault(table, []).append(col)

    if not tables:
        logger.warning("No user tables found — compiler will have no schema context")
        return "No tables found in the database."

    parts: list[str] = []
    for table_name, columns in tables.items():
        parts.append(f"Table: {table_name}")
        parts.append("Columns:")
        parts.extend(columns)
        parts.append("")

    return "\n".join(parts)


async def ingest_policy(
    db: AsyncSession,
    file_bytes: bytes,
    filename: str,
    policy_id: int | None = None,
) -> int:
    policy: Policy
    if policy_id is not None:
        result = await db.execute(select(Policy).where(Policy.id == policy_id))
        existing = result.scalar_one_or_none()
        if existing is None:
            logger.warning(
                "Policy %d not found during background ingestion, creating a new policy",
                policy_id,
            )
            policy = Policy(filename=filename, markdown_text="", status="processing")
            db.add(policy)
            await db.flush()
            policy_id = policy.id
        else:
            policy = existing
            policy.filename = filename
    else:
        policy = Policy(filename=filename, markdown_text="", status="processing")
        db.add(policy)
        await db.flush()
        policy_id = policy.id

    policy.status = "processing"

    try:
        markdown_text = _extract_policy_text(file_bytes, filename)
    except Exception as e:
        logger.error("Text extraction failed for policy %d: %s", policy_id, e)
        policy.status = "failed"
        await db.commit()
        return policy_id

    policy.markdown_text = markdown_text
    policy.status = "processing"

    try:
        schema_context = await _introspect_db_schema(db)
        deps = CompilerDeps(db_schema_context=schema_context)
        result = await get_compiler_agent().run(markdown_text, deps=deps)

        for compiled_rule in result.output:
            rule = Rule(
                policy_id=policy_id,
                title=compiled_rule.title,
                source_quote=compiled_rule.source_quote,
                severity=compiled_rule.severity,
                compiled_sql=compiled_rule.compiled_sql,
                is_deterministic=compiled_rule.is_deterministic,
                status="pending_review",
            )
            db.add(rule)

        policy.status = "completed"
    except Exception as e:
        logger.error("Compilation failed for policy %d: %s", policy_id, e)
        policy.status = "failed"

    await db.commit()
    return policy_id
