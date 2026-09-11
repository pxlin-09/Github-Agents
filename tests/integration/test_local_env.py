from __future__ import annotations

from pathlib import Path

import pytest

from issue_agent.environment.local import LocalEnvironment


def test_local_environment_read_write_list(tmp_workspace: Path):
    env = LocalEnvironment(
        tmp_workspace,
        skip_names=frozenset({".git", "__pycache__"}),
    )
    env.write_file("src/hello.py", "print('hi')\n")
    assert env.read_file("src/hello.py") == "print('hi')\n"

    (tmp_workspace / "__pycache__").mkdir()
    (tmp_workspace / "__pycache__" / "x.pyc").write_text("x")
    listing = env.list_dir(".")
    assert "src/" in listing
    assert "__pycache__" not in listing


def test_local_environment_execute_and_run(tmp_workspace: Path):
    env = LocalEnvironment(tmp_workspace)
    env.write_file("note.txt", "hello")
    formatted = env.execute(["cat", "note.txt"])
    assert "exit_code=0" in formatted
    assert "hello" in formatted

    assert env.run(["cat", "note.txt"]).strip() == "hello"
    with pytest.raises(RuntimeError, match="Command failed"):
        env.run(["false"])


def test_local_list_dir_missing(tmp_workspace: Path):
    env = LocalEnvironment(tmp_workspace)
    with pytest.raises(FileNotFoundError):
        env.list_dir("missing")


def test_list_dir_missing_returns_tool_error(tmp_workspace: Path):
    from issue_agent.tools.filesystem import ListDirTool
    from issue_agent.tools.registry import ToolRegistry

    env = LocalEnvironment(tmp_workspace)
    registry = ToolRegistry()
    registry.register(ListDirTool(env))
    result = registry.execute("list_dir", {"path": ".github"})
    assert result.startswith("Error:")
    assert ".github" in result
