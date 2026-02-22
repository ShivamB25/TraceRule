import asyncio
import logging
from functools import lru_cache
from time import perf_counter

from pydantic import BaseModel, Field

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.config import settings

logger = logging.getLogger(__name__)


class LegalArgument(BaseModel):
    points: list[str]
    evidence_citations: list[str]


class Verdict(BaseModel):
    is_violation: bool
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Mathematical certainty of verdict"
    )
    prosecutor_summary: str
    defender_summary: str
    chief_justice_reasoning: str


def _build_model() -> AnthropicModel:
    return AnthropicModel(
        "claude-sonnet-4-6",
        provider=AnthropicProvider(api_key=settings.anthropic_api_key),
    )


_THINKING_SETTINGS = AnthropicModelSettings(
    anthropic_thinking={"type": "enabled", "budget_tokens": 8000},
    max_tokens=16000,
)


@lru_cache(maxsize=1)
def _get_prosecutor() -> Agent[None, LegalArgument]:
    return Agent(
        _build_model(),
        output_type=LegalArgument,
        model_settings=_THINKING_SETTINGS,
        instructions=(
            "You are the Prosecutor in a compliance courtroom. "
            "Argue forcefully why the evidence shows a VIOLATION of the rule. "
            "Cite specific data fields as evidence."
        ),
    )


@lru_cache(maxsize=1)
def _get_defender() -> Agent[None, LegalArgument]:
    return Agent(
        _build_model(),
        output_type=LegalArgument,
        model_settings=_THINKING_SETTINGS,
        instructions=(
            "You are the Defense Attorney in a compliance courtroom. "
            "Argue why the record COMPLIES with the rule. "
            "Find loopholes, exceptions, and mitigating context in the data."
        ),
    )


@lru_cache(maxsize=1)
def _get_chief_justice() -> Agent[None, Verdict]:
    return Agent(
        _build_model(),
        output_type=Verdict,
        model_settings=AnthropicModelSettings(
            anthropic_thinking={"type": "enabled", "budget_tokens": 16000},
            max_tokens=32000,
        ),
        instructions=(
            "You are the Chief Justice presiding over a compliance case. "
            "You have heard arguments from both the Prosecution and Defense. "
            "Issue a final verdict with a mathematical confidence_score (0.0–1.0). "
            "Be impartial. Weigh evidence quality, not argument quantity."
        ),
    )


async def run_semantic_debate(record_data: dict, rule_rubric: str) -> Verdict:
    context = f"RULE RUBRIC: {rule_rubric}\nRECORD EVIDENCE: {record_data}"
    started = perf_counter()

    pros_task = _run_legal_argument_stream(
        _get_prosecutor(),
        f"Argue why this record VIOLATES the rule.\n{context}",
    )
    def_task = _run_legal_argument_stream(
        _get_defender(),
        f"Argue why this record COMPLIES with the rule (find loopholes).\n{context}",
    )
    pros_res, def_res = await asyncio.gather(pros_task, def_task)

    async with _get_chief_justice().run_stream(
        f"Prosecution Argument: {pros_res.model_dump_json()}\n"
        f"Defense Argument: {def_res.model_dump_json()}\n"
        f"Original context: {context}\n"
        f"Issue your final verdict."
    ) as response:
        verdict = await response.get_output()

    logger.info(
        "Courtroom semantic debate completed in %.2fs", perf_counter() - started
    )
    return verdict


async def _run_legal_argument_stream(
    agent: Agent[None, LegalArgument],
    prompt: str,
) -> LegalArgument:
    async with agent.run_stream(prompt) as response:
        return await response.get_output()
