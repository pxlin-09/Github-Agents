from dataclasses import dataclass


@dataclass
class RunLimits:
    max_steps: int = 40
    max_cost_usd: float = 2.0
    max_runtime_seconds: int = 900
    max_test_runs: int = 10