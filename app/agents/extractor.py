import logging
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ast_compiler import compile_ast_to_sql
from app.config import settings
from app.schemas import GlobalOntology, SymbolicRule

logger = logging.getLogger(__name__)


@dataclass
class ExtractorDeps:
    db: AsyncSession
    db_schema_context: str
    global_ontology: GlobalOntology


_INSTRUCTIONS = (
    "You are TraceRule V3, a neuro-symbolic compliance compiler.\n\n"
    "Convert policy text into a SymbolicRule with a deontic logic AST.\n\n"
    "RULES:\n"
    "1. Map each enforceable clause to a LogicNode tree of Conditions.\n"
    "2. Use EXACT column names from the database schema provided.\n"
    "3. If a clause is subjective (e.g., 'lavish gifts', 'reasonable effort'), "
    "use operator='IS_VAGUE' with a semantic_rubric describing what to evaluate.\n"
    "4. Set requires_semantic_scan=True if ANY Condition uses IS_VAGUE.\n"
    "5. Use UNLESS for legal exceptions (defeasible reasoning).\n"
    "6. The compiled_sql field will be auto-generated — leave it as None.\n"
    "7. Consult the Global Ontology for acronym/term definitions."
)


@lru_cache(maxsize=1)
def get_extractor_agent() -> Agent[ExtractorDeps, list[SymbolicRule]]:
    model = AnthropicModel(
        "claude-sonnet-4-6",
        provider=AnthropicProvider(api_key=settings.anthropic_api_key),
    )
    agent: Agent[ExtractorDeps, list[SymbolicRule]] = Agent(
        model,
        deps_type=ExtractorDeps,
        output_type=list[SymbolicRule],
        retries=4,
        model_settings=AnthropicModelSettings(
            anthropic_thinking={"type": "enabled", "budget_tokens": 16000},
        ),
        instructions=_INSTRUCTIONS,
    )

    @agent.system_prompt
    def inject_schema(ctx: RunContext[ExtractorDeps]) -> str:
        ontology_block = ""
        if ctx.deps.global_ontology.definitions:
            defs = "\n".join(
                f"  {k}: {v}" for k, v in ctx.deps.global_ontology.definitions.items()
            )
            ontology_block = (
                f"\n\nGlobal Ontology (term definitions from policy):\n{defs}"
            )

        return (
            f"Database schema to compile rules against:\n"
            f"{ctx.deps.db_schema_context}"
            f"{ontology_block}"
        )

    @agent.output_validator
    async def validate_sql_sandbox(
        ctx: RunContext[ExtractorDeps], result: list[SymbolicRule]
    ) -> list[SymbolicRule]:
        for rule in result:
            sql_where = compile_ast_to_sql(rule.logic_tree)
            test_sql = f"SELECT id FROM {rule.target_table} WHERE {sql_where} LIMIT 1"

            try:
                async with ctx.deps.db.begin_nested():
                    await ctx.deps.db.execute(text(f"EXPLAIN {test_sql}"))
                rule.compiled_sql = (
                    f"SELECT id, data_payload FROM {rule.target_table} "
                    f"WHERE {sql_where}"
                )
            except DBAPIError as e:
                raise ModelRetry(
                    f"SQL validation failed for rule '{rule.rule_id}'. "
                    f"Postgres error: {e.orig}. "
                    f"Fix the subject_column values in the AST to match "
                    f"the actual DB schema columns."
                )

        return result

    return agent
