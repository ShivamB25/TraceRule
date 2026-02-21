from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModelSettings

from app.schemas import CompiledRule


@dataclass
class CompilerDeps:
    db_schema_context: str


_INSTRUCTIONS = (
    "You are TraceRule, an enterprise compliance compiler. "
    "Convert legal/policy text into deterministic PostgreSQL queries.\n\n"
    "RULES:\n"
    "1. Apply MECE decomposition (Mutually Exclusive, Collectively Exhaustive).\n"
    "2. Write queries that RETURN VIOLATIONS. If policy says 'must be >= 18', write WHERE age < 18.\n"
    "3. Use EXACT column names from the provided database schema.\n"
    "4. If a rule is purely subjective ('good moral character'), set is_deterministic=False, compiled_sql=None.\n"
    "5. Each rule must be independently testable — one SQL query per rule."
)


@lru_cache(maxsize=1)
def get_compiler_agent() -> Agent[CompilerDeps, list[CompiledRule]]:
    agent: Agent[CompilerDeps, list[CompiledRule]] = Agent(
        "anthropic:claude-sonnet-4-5",
        deps_type=CompilerDeps,
        output_type=list[CompiledRule],
        retries=3,
        model_settings=AnthropicModelSettings(
            anthropic_thinking={"type": "enabled", "budget_tokens": 4000},
        ),
        instructions=_INSTRUCTIONS,
    )

    @agent.system_prompt
    def inject_db_schema(ctx: RunContext[CompilerDeps]) -> str:
        return f"Database schema to query against:\n{ctx.deps.db_schema_context}"

    return agent
