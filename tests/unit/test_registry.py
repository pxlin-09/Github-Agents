from __future__ import annotations

from issue_agent.tools.base import Tool
from issue_agent.tools.registry import ToolRegistry
from issue_agent.tools.testing import RunTestsTool


class _EchoTool(Tool):
    name = "echo"
    description = "Echo arguments"

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, text: str) -> str:
        return text


class _BoomTool(Tool):
    name = "boom"
    description = "Raise ValueError"

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
        raise ValueError("bad path")


def test_registry_execute_unknown_tool():
    registry = ToolRegistry()
    assert registry.execute("missing", {}) == "Error: Unknown tool: missing"


def test_registry_execute_success_and_schemas():
    registry = ToolRegistry()
    registry.register(_EchoTool())
    assert registry.execute("echo", {"text": "hi"}) == "hi"
    schemas = registry.schemas()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "echo"


def test_registry_catches_value_error():
    registry = ToolRegistry()
    registry.register(_BoomTool())
    assert registry.execute("boom", {}).startswith("Error: bad path")


class _FakeEnv:
    def python_command(self):
        return ["python"]

    def execute(self, command):
        raise AssertionError(f"should not run: {command}")


def test_run_tests_respects_max_runs():
    tool = RunTestsTool(_FakeEnv(), max_test_runs=1)
    # First call would hit env; stub execute via monkeypatch-like override
    tool.environment.execute = lambda command: "ok"  # type: ignore[method-assign]
    assert tool.execute(".") == "ok"
    blocked = tool.execute(".")
    assert "max_test_runs" in blocked
