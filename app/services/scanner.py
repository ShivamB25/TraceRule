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
            logger.exception("SQL execution failed for rule %d: %s", rule["id"], e)

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
            logger.exception("Explanation failed for violation %d: %s", row["id"], e)
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
# V3 scanner — SQL Pre-Filtering + Multi-Agent Semantic Evaluation
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


async def _find_bm25_candidates(
    db: AsyncSession,
    target_table: str,
    rubric_text: str,
    limit: int = 20,
) -> list[dict]:
    """BM25 full-text search on company_records for pure-vague rules.

    Uses Postgres-native ts_rank + websearch_to_tsquery — no embeddings,
    no pgvector, no external API calls.
    """
    bm25_query = text("""
        SELECT id, data_payload,
               ts_rank(ts_vector, websearch_to_tsquery('english', :query_text)) as rank_score
        FROM company_records
        WHERE table_name = :target_table
          AND ts_vector @@ websearch_to_tsquery('english', :query_text)
        ORDER BY rank_score DESC
        LIMIT :result_limit;
    """)
    result = await db.execute(
        bm25_query,
        {
            "query_text": rubric_text,
            "target_table": target_table,
            "result_limit": limit,
        },
    )
    return [dict(row) for row in result.mappings().all()]


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
            # Pure deterministic — run SQL, save with confidence=1.0
            deterministic_count += await _scan_deterministic_v3(
                db, rule_id_pk, rule_row
            )
        else:
            # Mixed or pure-vague — SQL pre-filter + courtroom evaluation
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
        logger.exception("V3 deterministic scan failed for rule %d: %s", rule_pk, e)

    return count


async def _scan_semantic_v3(
    db: AsyncSession,
    session_factory: async_sessionmaker,
    rule_pk: int,
    rule_row: Mapping,
) -> int:
    """Semantic scan: SQL pre-filter → courtroom evaluation.

    Mixed rules (deterministic + vague conditions):
      Compiled SQL has IS_VAGUE → 1=1, producing a superset of candidates.
      Each candidate is evaluated by the adversarial courtroom.

    Pure-vague rules (no deterministic SQL):
      BM25 text search on company_records finds candidates.
      Each candidate is evaluated by the adversarial courtroom.
    """
    logic_tree = LogicNode.model_validate(rule_row["logic_tree_json"])
    rubrics = _collect_semantic_rubrics(logic_tree)
    if not rubrics:
        return 0

    combined_rubric = " | ".join(rubrics)
    compiled_sql = rule_row["compiled_sql"]

    # Phase 1: Get candidate rows
    if compiled_sql:
        # Mixed rule — SQL pre-filter (IS_VAGUE compiled to 1=1 → superset)
        try:
            candidate_result = await db.execute(text(compiled_sql))
            candidate_rows = [
                {"id": r.get("id"), "data_payload": _make_json_safe(dict(r))}
                for r in candidate_result.mappings().all()
            ]
        except Exception as e:
            logger.exception(
                "SQL pre-filter failed for rule %d: %s — falling back to BM25",
                rule_pk,
                e,
            )
            candidate_rows = await _find_bm25_candidates(
                db, rule_row["target_table"], combined_rubric
            )
    else:
        # Pure-vague rule — BM25 text search on company_records
        candidate_rows = await _find_bm25_candidates(
            db, rule_row["target_table"], combined_rubric
        )

    if not candidate_rows:
        return 0

    # Phase 2: Dedup against existing violations
    existing = await db.execute(
        text("SELECT record_id FROM v3_violations WHERE v3_rule_id = :rule_id"),
        {"rule_id": rule_pk},
    )
    known_ids: set[int] = {row[0] for row in existing}

    # Phase 3: Courtroom evaluation for each candidate
    count = 0
    for row in candidate_rows:
        record_id = row.get("id")
        if record_id is None or record_id in known_ids:
            continue

        record_data = row.get("data_payload", row)

        try:
            verdict = await run_semantic_debate(
                record_data=record_data,
                rule_rubric=combined_rubric,
            )
            if verdict.is_violation:
                v3_violation = V3Violation(
                    v3_rule_id=rule_pk,
                    record_id=record_id,
                    violation_data=_make_json_safe(
                        record_data if isinstance(record_data, dict) else dict(row)
                    ),
                    confidence_score=verdict.confidence_score,
                    verdict_reasoning=verdict.chief_justice_reasoning,
                )
                db.add(v3_violation)
                known_ids.add(record_id)
                count += 1
        except Exception as e:
            logger.exception(
                "Courtroom debate failed for record %s on rule %d: %s",
                record_id,
                rule_pk,
                e,
            )

    return count
