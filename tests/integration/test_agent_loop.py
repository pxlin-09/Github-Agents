from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from openai import AuthenticationError, OpenAIError

from issue_agent.agent.agent import CodingAgent
from issue_agent.environment.local import LocalEnvironment
from issue_agent.models.openai_model import OpenAIModel
from issue_agent.tools.filesystem import ListDirTool, ReadFileTool, WriteFileTool
from issue_agent.tools.registry import ToolRegistry
from tests.helpers import TEST_MODEL


class _ScriptedModel:
    """Returns scripted Responses-API-shaped objects."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def generate(self, input_items, tools):
        self.calls += 1
        return self._responses.pop(0)


def _function_call(name: str, arguments: dict, call_id: str = "call_1"):
    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=json.dumps(arguments),
        call_id=call_id,
    )


def test_coding_agent_runs_tool_then_finishes(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "hello.txt").write_text("hi\n", encoding="utf-8")

    env = LocalEnvironment(workspace)
    tools = ToolRegistry()
    tools.register(ListDirTool(env))
    tools.register(ReadFileTool(env))
    tools.register(WriteFileTool(env))

    model = _ScriptedModel(
        [
            SimpleNamespace(
                output=[_function_call("read_file", {"path": "hello.txt"})],
                output_text="",
            ),
            SimpleNamespace(
                output=[],
                output_text=(
                    'Updated nothing.\n\n'
                    '{"commit_message":"noop","pr_title":"noop","pr_body":"Fixes #1"}'
                ),
            ),
        ]
    )

    agent = CodingAgent(
        model=model,
        tools=tools,
        max_steps=5,
        trajectory_dir=tmp_path / "traj",
        verbose=False,
    )
    answer = agent.run("Read hello.txt")
    assert "noop" in answer
    assert model.calls == 2
    saved = list((tmp_path / "traj").glob("*.json"))
    assert len(saved) == 1
    payload = json.loads(saved[0].read_text(encoding="utf-8"))
    assert payload["steps"][0]["tool"] == "read_file"
    assert "hi" in payload["steps"][0]["output"]


@pytest.mark.openai
def test_coding_agent_live_gpt5_nano(tmp_path: Path, openai_test_model: OpenAIModel):
    """Live smoke: real gpt-5-nano drives tools in a tiny workspace."""
    assert openai_test_model.model == TEST_MODEL

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "hello.txt").write_text("nano-ok\n", encoding="utf-8")

    env = LocalEnvironment(workspace)
    tools = ToolRegistry()
    tools.register(ListDirTool(env))
    tools.register(ReadFileTool(env))
    tools.register(WriteFileTool(env))

    agent = CodingAgent(
        model=openai_test_model,
        tools=tools,
        max_steps=8,
        trajectory_dir=tmp_path / "traj",
        verbose=False,
    )
    try:
        answer = agent.run(
            "Use read_file to read hello.txt. "
            "Then reply with a short summary and end with this JSON object:\n"
            '{"commit_message":"noop","pr_title":"noop","pr_body":"Fixes #1"}'
        )
    except AuthenticationError as exc:
        pytest.skip(f"OPENAI_API_KEY rejected by API: {exc}")
    except OpenAIError as exc:
        pytest.skip(f"OpenAI API error during live nano test: {exc}")

    assert answer
    assert "noop" in answer or "Fixes #1" in answer or "nano-ok" in answer.lower()
    saved = list((tmp_path / "traj").glob("*.json"))
    assert saved, "expected a trajectory file from the live run"
    payload = json.loads(saved[0].read_text(encoding="utf-8"))
    tools_used = {step["tool"] for step in payload["steps"]}
    assert "read_file" in tools_used or "list_dir" in tools_used


@pytest.mark.openai
def test_coding_agent_fixes_hello_world(tmp_path: Path, openai_test_model: OpenAIModel):
    """Live: agent edits a buggy hello program; assert runtime output."""
    assert openai_test_model.model == TEST_MODEL

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "hello.py").write_text('print("hello")\n', encoding="utf-8")

    env = LocalEnvironment(workspace)
    before = env.run([*env.python_command(), "hello.py"]).strip()
    assert before == "hello"

    tools = ToolRegistry()
    tools.register(ListDirTool(env))
    tools.register(ReadFileTool(env))
    tools.register(WriteFileTool(env))

    agent = CodingAgent(
        model=openai_test_model,
        tools=tools,
        max_steps=10,
        trajectory_dir=tmp_path / "traj",
        verbose=False,
    )
    try:
        answer = agent.run(
            "hello.py is supposed to print hello world, but it only prints hello. "
            "Fix hello.py so running it prints exactly: hello world\n"
            "Keep the change minimal. When done, end with this JSON object:\n"
            '{"commit_message":"Fix hello world","pr_title":"Fix hello world",'
            '"pr_body":"Fixes #1"}'
        )
    except AuthenticationError as exc:
        pytest.skip(f"OPENAI_API_KEY rejected by API: {exc}")
    except OpenAIError as exc:
        pytest.skip(f"OpenAI API error during live nano test: {exc}")

    assert answer
    after = env.run([*env.python_command(), "hello.py"]).strip()
    assert after == "hello world"

    saved = list((tmp_path / "traj").glob("*.json"))
    assert saved
    payload = json.loads(saved[0].read_text(encoding="utf-8"))
    tools_used = {step["tool"] for step in payload["steps"]}
    assert "write_file" in tools_used
