from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON, TypeDecorator


# ---------------------------------------------------------------------------
# Type helpers
# ---------------------------------------------------------------------------


class JSONVariant(TypeDecorator):
    """JSONB on Postgres, plain JSON elsewhere (SQLite tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class TSVectorVariant(TypeDecorator):
    """TSVECTOR on Postgres, plain Text elsewhere (SQLite tests)."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(Text())


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class Base(AsyncAttrs, DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# V1 models (existing — do not remove)
# ---------------------------------------------------------------------------


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str]
    markdown_text: Mapped[str]
    status: Mapped[str] = mapped_column(default="processing")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"))
    title: Mapped[str]
    source_quote: Mapped[str]
    severity: Mapped[str] = mapped_column(default="MEDIUM")
    compiled_sql: Mapped[str | None]
    is_deterministic: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(default="pending_review")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Violation(Base):
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id"))
    record_pk: Mapped[str]
    violating_data: Mapped[dict] = mapped_column(JSONVariant)
    ai_explanation: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="open")
    detected_at: Mapped[datetime] = mapped_column(server_default=func.now())


# ---------------------------------------------------------------------------
# V3 models — Neuro-Symbolic Compliance Engine
# ---------------------------------------------------------------------------


class CompanyRecord(Base):
    """Universal record store for BM25 full-text search.

    Business table rows are flattened here so the scanner can run
    Postgres-native ts_rank BM25 ranking for pure-vague policy clauses.
    Deterministic and mixed rules query target tables directly via SQL.
    """

    __tablename__ = "company_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(
        index=True, comment="Logical source table (e.g. 'expenses', 'employees')"
    )
    data_payload: Mapped[dict] = mapped_column(JSONVariant)
    search_text: Mapped[str] = mapped_column(
        Text, comment="Concatenated text for BM25 full-text search"
    )
    ts_vector: Mapped[str] = mapped_column(
        TSVectorVariant(), nullable=True, comment="Postgres tsvector for ts_rank"
    )

    __table_args__ = (
        Index("ix_records_search_vector", "ts_vector", postgresql_using="gin"),
        Index("ix_records_table_name", "table_name"),
    )


class V3Rule(Base):
    """A single compliance rule expressed as a deontic logic AST."""

    __tablename__ = "v3_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"))
    rule_id: Mapped[str] = mapped_column(
        unique=True, comment="Stable identifier from extractor (e.g. 'AML-3.2')"
    )
    title: Mapped[str]
    source_quote: Mapped[str]
    severity: Mapped[str] = mapped_column(default="MEDIUM")
    target_table: Mapped[str]
    logic_tree_json: Mapped[dict] = mapped_column(
        JSONVariant, comment="Serialised LogicNode"
    )
    requires_semantic_scan: Mapped[bool] = mapped_column(default=False)
    compiled_sql: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="pending_review")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class V3Violation(Base):
    """Violation detected by V3 scanner (deterministic or semantic)."""

    __tablename__ = "v3_violations"

    id: Mapped[int] = mapped_column(primary_key=True)
    v3_rule_id: Mapped[int] = mapped_column(ForeignKey("v3_rules.id"))
    record_id: Mapped[int]
    violation_data: Mapped[dict] = mapped_column(JSONVariant)
    verdict_reasoning: Mapped[str | None] = mapped_column(
        comment="Chief Justice reasoning for semantic violations"
    )
    confidence_score: Mapped[float | None] = mapped_column(
        comment="0.0-1.0 confidence from courtroom verdict"
    )
    status: Mapped[str] = mapped_column(default="open")
    detected_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index("ix_v3_violations_dedup", "v3_rule_id", "record_id", unique=True),
    )
