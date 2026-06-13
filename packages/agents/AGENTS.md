# packages/agents — AGENTS.md

Every agent = `graph.py` + `prompts.py` + `models.py`. LLM calls only here.

Default model: `claude-haiku-4-5-20251001`. Sonnet 4.6 only for synthesis nodes per root AGENTS.md.

Wrap nodes with `@traced` and `BudgetGuard`.
