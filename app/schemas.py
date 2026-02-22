from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# V1 schemas (existing — do not remove)
# ---------------------------------------------------------------------------


class CompiledRule(BaseModel):
    """Single atomic compliance rule compiled from policy text."""

    title: str = Field(description="Short title, e.g., 'Minimum Age Requirement'")
    source_quote: str = Field(description="Exact quote from PDF for audit trail")
    severity: str = Field(description="CRITICAL, HIGH, MEDIUM, or LOW")
    is_deterministic: bool = Field(
        description=(
            "True ONLY if the rule can be strictly evaluated via SQL. "
            "False for subjective rules like 'good moral character'."
        ),
    )
    compiled_sql: str | None = Field(
        default=None,
        description=(
            "PostgreSQL SELECT that RETURNS VIOLATING RECORDS. "
            "Example: SELECT id, age FROM employees WHERE age < 18. "
            "Must return 'id' (primary key of violating row) and evidence columns. "
            "None if is_deterministic is False."
        ),
    )


class PolicyUploadResponse(BaseModel):
    id: int
    filename: str
    status: str


class RuleResponse(BaseModel):
    id: int
    policy_id: int
    title: str
    source_quote: str
    severity: str
    compiled_sql: str | None
    is_deterministic: bool
    status: str

    model_config = {"from_attributes": True}


class RuleStatusUpdate(BaseModel):
    status: str = Field(description="New status: 'approved' or 'rejected'")


class ViolationResponse(BaseModel):
    id: int
    rule_id: int
    record_pk: str
    violating_data: dict
    ai_explanation: str | None
    status: str

    model_config = {"from_attributes": True}


class ScanResult(BaseModel):
    violations_found: int


# ---------------------------------------------------------------------------
# V3 schemas — Deontic AST for Neuro-Symbolic Compliance
# ---------------------------------------------------------------------------


class GlobalOntology(BaseModel):
    """Maps acronyms, roles, and domain terms from a policy PDF to their
    exact legal definitions. Injected into every extraction context so the
    LLM never invents meanings for abbreviations."""

    definitions: dict[str, str] = Field(
        default_factory=dict,
        description="Maps acronyms/roles/terms from the PDF to their exact legal definitions.",
    )


class Condition(BaseModel):
    """Leaf node of the deontic logic tree — a single testable predicate."""

    subject_column: str = Field(
        description="Exact DB column name matching the target table schema."
    )
    operator: Literal[
        "==",
        "=",
        ">",
        "<",
        ">=",
        "<=",
        "!=",
        "CONTAINS",
        "IS_NULL",
        "IS_NOT_NULL",
        "IS_VAGUE",
    ]
    value: Any | None = None
    semantic_rubric: str | None = Field(
        default=None,
        description=(
            "Required when operator is IS_VAGUE. Natural-language rubric for "
            "the AI Judge (e.g., 'Is this gift lavish relative to the recipient role?')."
        ),
    )


class LogicNode(BaseModel):
    """Interior node — combines children via AND / OR / UNLESS (defeasible)."""

    logic_type: Literal["AND", "OR", "UNLESS"]
    children: list[Union[LogicNode, Condition]]


# Pydantic V2 requires explicit rebuild for recursive models
LogicNode.model_rebuild()


class SymbolicRule(BaseModel):
    """Output of the extractor agent: one compliance rule mapped to a logic AST."""

    rule_id: str
    title: str = Field(description="Human-readable rule name")
    source_quote: str = Field(
        description="Exact quote from policy text for audit trail"
    )
    severity: str = Field(
        default="MEDIUM", description="CRITICAL, HIGH, MEDIUM, or LOW"
    )
    target_table: str = Field(description="DB table this rule scans against")
    logic_tree: LogicNode
    requires_semantic_scan: bool = Field(
        description="True if ANY condition in the tree uses IS_VAGUE operator"
    )
    compiled_sql: str | None = None


class SymbolicRuleDraft(BaseModel):
    """Extractor-friendly non-recursive shape.

    The Anthropic schema validator can reject recursive-only JSON schema fragments.
    This draft model keeps `logic_tree` as raw JSON and we validate it into a
    `LogicNode` server-side before persistence.
    """

    rule_id: str
    title: str = Field(description="Human-readable rule name")
    source_quote: str = Field(
        description="Exact quote from policy text for audit trail"
    )
    severity: str = Field(
        default="MEDIUM", description="CRITICAL, HIGH, MEDIUM, or LOW"
    )
    target_table: str = Field(description="DB table this rule scans against")
    logic_tree: dict[str, Any]
    requires_semantic_scan: bool = Field(
        description="True if ANY condition in the tree uses IS_VAGUE operator"
    )
    compiled_sql: str | None = None


# ---------------------------------------------------------------------------
# V3 response schemas
# ---------------------------------------------------------------------------


class V3RuleResponse(BaseModel):
    id: int
    policy_id: int
    rule_id: str
    title: str
    source_quote: str
    severity: str
    target_table: str
    logic_tree_json: dict | None
    requires_semantic_scan: bool
    compiled_sql: str | None
    status: str

    model_config = {"from_attributes": True}


class V3ViolationResponse(BaseModel):
    id: int
    v3_rule_id: int
    record_id: int
    violation_data: dict
    verdict_reasoning: str | None
    confidence_score: float | None
    status: str

    model_config = {"from_attributes": True}


class V3ScanResult(BaseModel):
    deterministic_violations: int
    semantic_violations: int
    total: int
