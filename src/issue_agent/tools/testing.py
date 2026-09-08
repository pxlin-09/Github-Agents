import sys

from .base import Tool


class RunTestsTool(Tool):
    name = "run_tests"
    description = "Run pytest in the workspace and return the output."

    def __init__(self, environment, max_test_runs: int = 10):
        self.environment = environment
        self.max_test_runs = max_test_runs
        self._runs = 0

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": (
                            "Test path or node id. Use '.' for the whole suite."
                        ),
                    },
                },
                "required": ["target"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, target: str) -> str:
        if self._runs >= self.max_test_runs:
            return (
                f"Error: max_test_runs ({self.max_test_runs}) reached; "
                "cannot run more tests this session."
            )
        self._runs += 1
        python = self.environment.python_command()
        return self.environment.execute(
            [*python, "-m", "pytest", target, "-q", "--tb=short"]
        )
