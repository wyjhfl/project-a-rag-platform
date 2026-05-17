import math
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TokenUsage:
    request_id: str
    module: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float


class TokenCostEstimator:
    """Local token/cost estimator so v0.5 can track cost without an external LLM API."""

    def __init__(self, price_per_1k_tokens: float = 0.0) -> None:
        self.price_per_1k_tokens = price_per_1k_tokens

    def estimate(self, module: str, prompt: str, completion: str) -> TokenUsage:
        prompt_tokens = self._estimate_tokens(prompt)
        completion_tokens = self._estimate_tokens(completion)
        total_tokens = prompt_tokens + completion_tokens
        return TokenUsage(
            request_id=str(uuid4()),
            module=module,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=round(total_tokens / 1000 * self.price_per_1k_tokens, 6),
        )

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        ascii_chars = sum(1 for char in text if ord(char) < 128 and not char.isspace())
        non_ascii_chars = sum(1 for char in text if ord(char) >= 128 and not char.isspace())
        return max(1, math.ceil(ascii_chars / 4) + math.ceil(non_ascii_chars / 1.8))
