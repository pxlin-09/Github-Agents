from __future__ import annotations

from types import SimpleNamespace

import pytest

from issue_agent.agent.agent import CodingAgent
from issue_agent.runtime.cost import (
    CostLimitExceeded,
    CostTracker,
    cost_usd_from_usage,
    pricing_for_model,
)
from issue_agent.tools.base import Tool
from issue_agent.tools.registry import ToolRegistry


def test_pricing_known_models():
    nano = pricing_for_model("gpt-5-nano")
    assert nano.input_per_mtok == 0.05
    assert nano.output_per_mtok == 0.40
    luna = pricing_for_model("gpt-5.6-luna")
    assert luna.input_per_mtok == 0.20


def test_cost_from_usage_with_cache():
    usage = SimpleNamespace(
        input_tokens=1_000_000,
        output_tokens=500_000,
        input_tokens_details=SimpleNamespace(cached_tokens=200_000),
    )
    # nano: 800k * 0.05/1M + 200k * 0.005/1M + 500k * 0.40/1M
    cost = cost_usd_from_usage("gpt-5-nano", usage)
    assert cost == pytest.approx(0.04 + 0.001 + 0.20)


def test_cost_tracker_blocks_after_budget():
    tracker = CostTracker("gpt-5-nano", max_cost_usd=0.01)
    usage = SimpleNamespace(
        input_tokens=100_000,
        output_tokens=10_000,
        input_tokens_details=SimpleNamespace(cached_tokens=0),
    )
    # 100k*0.05/1M + 10k*0.40/1M = 0.005 + 0.004 = 0.009
    tracker.record_usage(usage)
    assert tracker.spent_usd == pytest.approx(0.009)
    tracker.ensure_can_call()

    tracker.record_usage(usage)  # +0.009 → 0.018 > 0.01
    with pytest.raises(CostLimitExceeded):
        tracker.ensure_can_call()


class _NoopTool(Tool):
    name = "noop"
    description = "noop"

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self) -> str:
        return "ok"


class _BudgetModel:
    def __init__(self):
        self.calls = 0

    def generate(self, input_items, tools):
        self.calls += 1
        # First call spends past $0.01 on nano.
        usage = SimpleNamespace(
            input_tokens=100_000,
            output_tokens=20_000,
            input_tokens_details=SimpleNamespace(cached_tokens=0),
        )
        if self.calls == 1:
            return SimpleNamespace(
                usage=usage,
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="noop",
                        arguments="{}",
                        call_id="c1",
                    )
                ],
                output_text="",
            )
        return SimpleNamespace(
            usage=usage,
            output=[],
            output_text="done",
        )


def test_agent_stops_when_cost_limit_exceeded():
    tools = ToolRegistry()
    tools.register(_NoopTool())
    model = _BudgetModel()
    tracker = CostTracker("gpt-5-nano", max_cost_usd=0.01)
    agent = CodingAgent(
        model=model,
        tools=tools,
        max_steps=10,
        verbose=False,
        cost_tracker=tracker,
    )
    # After first call (~$0.013), the next loop's ensure_can_call raises.
    with pytest.raises(CostLimitExceeded):
        agent.run("do something")
    assert model.calls == 1
    assert tracker.spent_usd >= 0.01
