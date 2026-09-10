from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelPricing:
    """USD per 1M tokens."""

    input_per_mtok: float
    output_per_mtok: float
    cached_input_per_mtok: float | None = None


# Standard short-context list prices (USD / 1M tokens).
MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-5-nano": ModelPricing(0.05, 0.40, 0.005),
    "gpt-5.6-luna": ModelPricing(0.20, 1.20, 0.02),
    "gpt-5.6-terra": ModelPricing(2.00, 12.00, 0.20),
    "gpt-5.6": ModelPricing(4.00, 20.00, 0.40),
    "gpt-5.6-sol": ModelPricing(4.00, 20.00, 0.40),
}

# Unknown models: assume Sol rates so the budget errs on the side of stopping early.
_DEFAULT_PRICING = ModelPricing(4.00, 20.00, 0.40)


class CostLimitExceeded(RuntimeError):
    def __init__(self, spent_usd: float, max_cost_usd: float, model: str):
        self.spent_usd = spent_usd
        self.max_cost_usd = max_cost_usd
        self.model = model
        super().__init__(
            f"Cost limit exceeded for {model}: "
            f"spent ${spent_usd:.4f} >= max ${max_cost_usd:.4f}"
        )


def pricing_for_model(model: str) -> ModelPricing:
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]
    for key, pricing in MODEL_PRICING.items():
        if model.startswith(key):
            return pricing
    logger.warning(
        "No pricing entry for model %r; using conservative default rates",
        model,
    )
    return _DEFAULT_PRICING


def cost_usd_from_usage(model: str, usage: Any) -> float:
    """Compute USD cost from a Responses API usage object."""
    if usage is None:
        return 0.0
    pricing = pricing_for_model(model)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    cached = 0
    details = getattr(usage, "input_tokens_details", None)
    if details is not None:
        cached = int(getattr(details, "cached_tokens", 0) or 0)
    cached = min(cached, input_tokens)
    billable_input = input_tokens - cached
    cached_rate = (
        pricing.cached_input_per_mtok
        if pricing.cached_input_per_mtok is not None
        else pricing.input_per_mtok
    )
    return (
        billable_input / 1_000_000 * pricing.input_per_mtok
        + cached / 1_000_000 * cached_rate
        + output_tokens / 1_000_000 * pricing.output_per_mtok
    )


class CostTracker:
    """Tracks spend and blocks further model calls past max_cost_usd."""

    def __init__(self, model: str, max_cost_usd: float):
        if max_cost_usd < 0:
            raise ValueError("max_cost_usd must be >= 0")
        self.model = model
        self.max_cost_usd = float(max_cost_usd)
        self.pricing = pricing_for_model(model)
        self.spent_usd = 0.0
        self.calls = 0

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_cost_usd - self.spent_usd)

    def ensure_can_call(self) -> None:
        if self.spent_usd >= self.max_cost_usd:
            raise CostLimitExceeded(self.spent_usd, self.max_cost_usd, self.model)

    def record_usage(self, usage: Any) -> float:
        cost = cost_usd_from_usage(self.model, usage)
        self.spent_usd += cost
        self.calls += 1
        logger.info(
            "Model usage cost=$%.6f spent=$%.4f/$%.4f remaining=$%.4f (call #%d)",
            cost,
            self.spent_usd,
            self.max_cost_usd,
            self.remaining_usd,
            self.calls,
        )
        return cost
