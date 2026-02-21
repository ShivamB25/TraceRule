from functools import lru_cache

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel, AnthropicModelSettings
from pydantic_ai.providers.anthropic import AnthropicProvider

from app.config import settings


@lru_cache(maxsize=1)
def get_explainer_agent() -> Agent[None, str]:
    model = AnthropicModel(
        "claude-sonnet-4-6",
        provider=AnthropicProvider(api_key=settings.anthropic_api_key),
    )
    return Agent(
        model,
        output_type=str,
        model_settings=AnthropicModelSettings(
            anthropic_thinking={"type": "adaptive"},
            anthropic_effort="medium",
        ),
        instructions=(
            "You explain compliance violations to non-technical compliance officers. "
            "Given a rule title, the SQL that caught the violation, and the violating data, "
            "write exactly 2 sentences: what the violation is, and what action should be taken. "
            "Be specific. Reference the actual data values."
        ),
    )
