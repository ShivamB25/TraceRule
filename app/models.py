from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class JSONVariant(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Base(AsyncAttrs, DeclarativeBase):
    pass


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
