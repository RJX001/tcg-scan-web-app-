from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class BudgetGuard:
    max_input_tokens: int = 8_000
    max_output_tokens: int = 2_000
    max_cost_usd: float = 0.05
    input_tokens: int = field(default=0, init=False)
    output_tokens: int = field(default=0, init=False)
    cost_usd: float = field(default=0.0, init=False)

    def record(
        self, *, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0
    ) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost_usd += cost_usd
        if self.input_tokens > self.max_input_tokens:
            raise BudgetExceededError("input token budget exceeded")
        if self.output_tokens > self.max_output_tokens:
            raise BudgetExceededError("output token budget exceeded")
        if self.cost_usd > self.max_cost_usd:
            raise BudgetExceededError("cost budget exceeded")
