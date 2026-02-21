from pydantic import BaseModel, Field


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
