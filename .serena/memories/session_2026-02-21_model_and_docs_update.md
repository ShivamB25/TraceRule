Session summary (2026-02-21):
- Updated Anthropic model usage in agents to Claude Sonnet 4.6.
- Compiler agent now uses `anthropic:claude-sonnet-4-6` with `AnthropicModelSettings(anthropic_thinking={"type":"adaptive"}, anthropic_effort="high")`.
- Explainer agent now uses `anthropic:claude-sonnet-4-6` with adaptive thinking and `anthropic_effort="medium"`.
- Updated docs to match model switch:
  - AGENTS.md model section and thinking convention
  - README.md stack line
  - docs/ARCHITECTURE_RESEARCH.md philosophy section
- Verification after updates: `uv run pytest -q` passed (2 passed).
- Note: project runtime DB remains PostgreSQL; tests use in-memory SQLite only.