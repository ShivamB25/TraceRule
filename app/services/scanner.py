import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.explainer import get_explainer_agent
from app.config import settings
from app.models import Violation

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
