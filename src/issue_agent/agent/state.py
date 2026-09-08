from dataclasses import dataclass, field


@dataclass
class AgentState:
    step: int = 0

    tool_calls: list = field(default_factory=list)