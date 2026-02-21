from functools import lru_cache

from pydantic_ai import Agent


@lru_cache(maxsize=1)
def get_explainer_agent() -> Agent[None, str]:
    return Agent(
        "anthropic:claude-sonnet-4-5",
        output_type=str,
        instructions=(
            "You explain compliance violations to non-technical compliance officers. "
            "Given a rule title, the SQL that caught the violation, and the violating data, "
            "write exactly 2 sentences: what the violation is, and what action should be taken. "
            "Be specific. Reference the actual data values."
        ),
    )
