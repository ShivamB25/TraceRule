import logging
import tempfile
from pathlib import Path

import pymupdf4llm
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.compiler import CompilerDeps, get_compiler_agent
from app.agents.extractor import ExtractorDeps, get_extractor_agent
from app.models import Policy, Rule, V3Rule
from app.config import settings
from app.schemas import GlobalOntology

logger = logging.getLogger(__name__)

_INTERNAL_TABLES = frozenset(
    {
        "policies",
        "rules",
        "violations",
        "company_records",
        "v3_rules",
        "v3_violations",
    }
)


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


# ---------------------------------------------------------------------------
# V1 ingestion (existing — unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# V3 ingestion — Global Lexicon + AST extraction
# ---------------------------------------------------------------------------


_LEXICON_INSTRUCTIONS = (
    "You are a legal terminology analyst. "
    "Extract a glossary of ALL acronyms, role names, legal terms, and domain jargon "
    "from the following policy document. "
    "Return a JSON object where keys are the term/acronym and values are their "
    "plain-English definitions as used in this specific policy."
)


def _chunk_policy_text(
    full_text: str, chunk_size: int = 4000, overlap: int = 500
) -> list[str]:
    if len(full_text) <= chunk_size:
        return [full_text]

    chunks: list[str] = []
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunk = full_text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


async def _extract_global_ontology(full_text: str) -> GlobalOntology:
    from pydantic_ai import Agent
    from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
    from pydantic_ai.providers.anthropic import AnthropicProvider

    model = AnthropicModel(
        "claude-sonnet-4-6",
        provider=AnthropicProvider(api_key=settings.anthropic_api_key),
    )
    lexicon_agent: Agent[None, GlobalOntology] = Agent(
        model,
        output_type=GlobalOntology,
        model_settings=AnthropicModelSettings(
            anthropic_thinking={"type": "enabled", "budget_tokens": 4000},
        ),
        instructions=_LEXICON_INSTRUCTIONS,
    )
    result = await lexicon_agent.run(full_text[:12000])
    return result.output


async def ingest_policy_v3(
    db: AsyncSession,
    file_bytes: bytes,
    filename: str,
    policy_id: int,
) -> int:
    result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = result.scalar_one_or_none()
    if policy is None:
        logger.error("Policy %d not found for V3 ingestion", policy_id)
        return policy_id

    policy.status = "processing"

    try:
        markdown_text = _extract_policy_text(file_bytes, filename)
    except Exception as e:
        logger.error("V3 text extraction failed for policy %d: %s", policy_id, e)
        policy.status = "failed"
        await db.commit()
        return policy_id

    policy.markdown_text = markdown_text

    try:
        global_ontology = await _extract_global_ontology(markdown_text)
        schema_context = await _introspect_db_schema(db)

        deps = ExtractorDeps(
            db=db,
            db_schema_context=schema_context,
            global_ontology=global_ontology,
        )

        chunks = _chunk_policy_text(markdown_text)
        all_rules: list[V3Rule] = []

        for i, chunk in enumerate(chunks):
            prompt = f"[Chunk {i + 1}/{len(chunks)}]\n\n{chunk}"
            try:
                extraction = await get_extractor_agent().run(prompt, deps=deps)
                for symbolic_rule in extraction.output:
                    v3_rule = V3Rule(
                        policy_id=policy_id,
                        rule_id=symbolic_rule.rule_id,
                        title=symbolic_rule.title,
                        source_quote=symbolic_rule.source_quote,
                        severity=symbolic_rule.severity,
                        target_table=symbolic_rule.target_table,
                        logic_tree_json=symbolic_rule.logic_tree.model_dump(),
                        requires_semantic_scan=symbolic_rule.requires_semantic_scan,
                        compiled_sql=symbolic_rule.compiled_sql,
                        status="pending_review",
                    )
                    db.add(v3_rule)
                    all_rules.append(v3_rule)
            except Exception as e:
                logger.error(
                    "V3 extraction failed for policy %d chunk %d: %s",
                    policy_id,
                    i,
                    e,
                )

        policy.status = "completed" if all_rules else "failed"
    except Exception as e:
        logger.error("V3 ingestion failed for policy %d: %s", policy_id, e)
        policy.status = "failed"

    await db.commit()
    return policy_id
