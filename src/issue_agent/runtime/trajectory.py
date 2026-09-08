from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class StepRecord:
    step: int
    tool: str
    arguments: dict[str, Any]
    output: str


@dataclass
class Trajectory:
    task: str
    steps: list[StepRecord] = field(default_factory=list)
    _trajectory_id: str = field(default_factory=lambda: uuid4().hex[:12], repr=False)
    _started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        repr=False,
    )

    def add_step(
        self,
        tool: str,
        arguments: dict[str, Any],
        output: str,
    ) -> None:
        self.steps.append(
            StepRecord(
                step=len(self.steps) + 1,
                tool=tool,
                arguments=arguments,
                output=output,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "steps": [
                {
                    "step": step.step,
                    "tool": step.tool,
                    "arguments": step.arguments,
                    "output": step.output,
                }
                for step in self.steps
            ],
        }

    def save(self, directory: str | Path) -> Path:
        out_dir = Path(directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = self._started_at.replace(":", "")
        path = out_dir / f"{stamp}_{self._trajectory_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path
