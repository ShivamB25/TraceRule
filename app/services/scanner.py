import logging
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.courtroom import run_semantic_debate
from app.agents.explainer import get_explainer_agent
from app.config import settings
from app.models import V3Violation, Violation
from app.schemas import Condition, LogicNode

logger = logging.getLogger(__name__)


def _make_json_safe(row: dict) -> dict:
    out: dict = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, timedelta):
            out[k] = str(v)
        elif isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, (bytes, memoryview)):
            out[k] = v.hex() if isinstance(v, bytes) else bytes(v).hex()
        elif isinstance(v, (IPv4Address, IPv6Address)):
            out[k] = str(v)
        elif isinstance(v, (str, int, float, bool, list, dict, type(None))):
            out[k] = v
        else:
            out[k] = str(v)
    return out


# ---------------------------------------------------------------------------
# V1 scanner (existing — unchanged)
# ---------------------------------------------------------------------------


async def run_deterministic_scan(db: AsyncSession) -> int:
    result = await db.execute(
        text(
            "SELECT id, title, compiled_sql FROM rules "
            "WHERE status = 'approved' AND is_deterministic = true"
        )
    )
    violation_count = 0

    for rule in result.mappings():
        try:
            existing = await db.execute(
                text(
                    "SELECT record_pk FROM violations "
                    "WHERE rule_id = :rule_id AND status = 'open'"
                ),
                {"rule_id": rule["id"]},
            )
            known_pks: set[str] = {row[0] for row in existing}

            violators = await db.execute(text(rule["compiled_sql"]))
            for record in violators.mappings().all():
                pk = str(record.get("id", "unknown"))
                if pk in known_pks:
                    continue
                violation = Violation(
                    rule_id=rule["id"],
                    record_pk=pk,
                    violating_data=_make_json_safe(dict(record)),
                )
                db.add(violation)
                known_pks.add(pk)
                violation_count += 1
        except Exception as e:
            logger.error("SQL execution failed for rule %d: %s", rule["id"], e)

    await db.commit()

    if violation_count:
        await _explain_new_violations(db)

    return violation_count


def _build_fallback_explanation(row: dict) -> str:
    return (
        f"Matched approved deterministic rule '{row['title']}' for violation #{row['id']}. "
        "Review violating_data and the compiled SQL result in the dashboard for details."
    )


async def _explain_new_violations(
    db: AsyncSession, max_model_calls: int | None = None
) -> None:
    limit = (
        settings.explanation_model_limit_per_scan
        if max_model_calls is None
        else max_model_calls
    )
    limit = max(limit, 0)

    result = await db.execute(
        text(
            "SELECT v.id, v.violating_data, r.title, r.compiled_sql "
            "FROM violations v "
            "JOIN rules r ON v.rule_id = r.id "
            "WHERE v.ai_explanation IS NULL "
            "ORDER BY v.id ASC"
        )
    )

    pending_rows = list(result.mappings())
    model_rows = pending_rows[:limit]
    fallback_rows = pending_rows[limit:]

    if fallback_rows:
        logger.info(
            "Capping model explanations at %d for this scan; using fallback text for %d violations",
            limit,
            len(fallback_rows),
        )

    for row in model_rows:
        try:
            prompt = (
                f"Rule: {row['title']}\n"
                f"SQL: {row['compiled_sql']}\n"
                f"Violating data: {row['violating_data']}"
            )
            explanation_result = await get_explainer_agent().run(prompt)
            await db.execute(
                text(
                    "UPDATE violations SET ai_explanation = :explanation WHERE id = :id"
                ),
                {"explanation": explanation_result.output, "id": row["id"]},
            )
        except Exception as e:
            logger.error("Explanation failed for violation %d: %s", row["id"], e)
            await db.execute(
                text(
                    "UPDATE violations SET ai_explanation = :explanation WHERE id = :id"
                ),
                {
                    "explanation": _build_fallback_explanation(dict(row)),
                    "id": row["id"],
                },
            )

    for row in fallback_rows:
        await db.execute(
            text("UPDATE violations SET ai_explanation = :explanation WHERE id = :id"),
            {"explanation": _build_fallback_explanation(dict(row)), "id": row["id"]},
        )

    await db.commit()


# ---------------------------------------------------------------------------
# V3 scanner — Hybrid deterministic + RRF semantic + courtroom
# ---------------------------------------------------------------------------


def _collect_semantic_rubrics(node: LogicNode | Condition) -> list[str]:
    """Walk the AST and collect all IS_VAGUE semantic rubrics."""
    if isinstance(node, Condition):
        if node.operator == "IS_VAGUE" and node.semantic_rubric:
            return [node.semantic_rubric]
        return []
    rubrics: list[str] = []
    for child in node.children:
        rubrics.extend(_collect_semantic_rubrics(child))
    return rubrics


async def find_suspicious_rows(
    db: AsyncSession,
    target_table: str,
    query_text: str,
    query_embedding: list[float],
) -> list[dict]:
    """Reciprocal Rank Fusion: fuses pgvector cosine distance with Postgres BM25."""
    rrf_query = text("""
        WITH semantic_search AS (
            SELECT id, data_payload,
                   RANK() OVER (ORDER BY embedding <=> :query_embedding::vector) as vector_rank
            FROM company_records
            WHERE table_name = :target_table
        ),
        keyword_search AS (
            SELECT id,
                   RANK() OVER (
                       ORDER BY ts_rank(ts_vector, websearch_to_tsquery('english', :query_text))
                   ) as text_rank
            FROM company_records
            WHERE table_name = :target_table
              AND ts_vector @@ websearch_to_tsquery('english', :query_text)
        )
        SELECT s.id, s.data_payload,
               (COALESCE(1.0 / (60 + s.vector_rank), 0.0) +
                COALESCE(1.0 / (60 + k.text_rank), 0.0)) as rrf_score
        FROM semantic_search s
        LEFT JOIN keyword_search k ON s.id = k.id
        ORDER BY rrf_score DESC
        LIMIT 10;
    """)
    result = await db.execute(
        rrf_query,
        {
            "query_embedding": query_embedding,
            "query_text": query_text,
            "target_table": target_table,
        },
    )
    return [dict(row) for row in result.mappings().all()]


async def _generate_query_embedding(text_input: str) -> list[float]:
    """Placeholder for embedding generation.

    In production, call an embedding API (OpenAI, Voyage, Cohere).
    Returns a zero vector for now — replace with real embeddings.
    """
    return [0.0] * 1536


async def run_v3_scan(
    db: AsyncSession,
    session_factory: async_sessionmaker,
) -> dict[str, int]:
    result = await db.execute(
        text(
            "SELECT id, rule_id, title, target_table, logic_tree_json, "
            "requires_semantic_scan, compiled_sql "
            "FROM v3_rules "
            "WHERE status = 'approved'"
        )
    )

    deterministic_count = 0
    semantic_count = 0

    for rule_row in result.mappings():
        rule_id_pk = rule_row["id"]

        if not rule_row["requires_semantic_scan"]:
            deterministic_count += await _scan_deterministic_v3(
                db, rule_id_pk, rule_row
            )
        else:
            semantic_count += await _scan_semantic_v3(
                db, session_factory, rule_id_pk, rule_row
            )

    await db.commit()
    return {
        "deterministic_violations": deterministic_count,
        "semantic_violations": semantic_count,
        "total": deterministic_count + semantic_count,
    }


async def _scan_deterministic_v3(
    db: AsyncSession, rule_pk: int, rule_row: Mapping
) -> int:
    compiled_sql = rule_row["compiled_sql"]
    if not compiled_sql:
        return 0

    count = 0
    try:
        existing = await db.execute(
            text("SELECT record_id FROM v3_violations WHERE v3_rule_id = :rule_id"),
            {"rule_id": rule_pk},
        )
        known_ids: set[int] = {row[0] for row in existing}

        violators = await db.execute(text(compiled_sql))
        for record in violators.mappings().all():
            record_id = record.get("id")
            if record_id is None or record_id in known_ids:
                continue
            v3_violation = V3Violation(
                v3_rule_id=rule_pk,
                record_id=record_id,
                violation_data=_make_json_safe(dict(record)),
                confidence_score=1.0,
                verdict_reasoning="Deterministic SQL match",
            )
            db.add(v3_violation)
            known_ids.add(record_id)
            count += 1
    except Exception as e:
        logger.error("V3 deterministic scan failed for rule %d: %s", rule_pk, e)

    return count


async def _scan_semantic_v3(
    db: AsyncSession,
    session_factory: async_sessionmaker,
    rule_pk: int,
    rule_row: Mapping,
) -> int:
    logic_tree = LogicNode.model_validate(rule_row["logic_tree_json"])
    rubrics = _collect_semantic_rubrics(logic_tree)
    if not rubrics:
        return 0

    combined_rubric = " | ".join(rubrics)
    query_embedding = await _generate_query_embedding(combined_rubric)

    suspicious_rows = await find_suspicious_rows(
        db,
        target_table=rule_row["target_table"],
        query_text=combined_rubric,
        query_embedding=query_embedding,
    )

    existing = await db.execute(
        text("SELECT record_id FROM v3_violations WHERE v3_rule_id = :rule_id"),
        {"rule_id": rule_pk},
    )
    known_ids: set[int] = {row[0] for row in existing}

    count = 0
    for row in suspicious_rows:
        record_id = row.get("id")
        if record_id is None or record_id in known_ids:
            continue

        try:
            verdict = await run_semantic_debate(
                record_data=row.get("data_payload", {}),
                rule_rubric=combined_rubric,
            )
            if verdict.is_violation:
                v3_violation = V3Violation(
                    v3_rule_id=rule_pk,
                    record_id=record_id,
                    violation_data=_make_json_safe(row.get("data_payload", {})),
                    confidence_score=verdict.confidence_score,
                    verdict_reasoning=verdict.chief_justice_reasoning,
                )
                db.add(v3_violation)
                known_ids.add(record_id)
                count += 1
        except Exception as e:
            logger.error(
                "Courtroom debate failed for record %s on rule %d: %s",
                record_id,
                rule_pk,
                e,
            )

    return count
