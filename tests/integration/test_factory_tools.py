from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from issue_agent.environment.docker import DockerEnvironment
from issue_agent.environment.factory import create_environment
from issue_agent.environment.local import LocalEnvironment
from issue_agent.runtime.runner import build_agent
from issue_agent.tools.filesystem import ListDirTool, ReadFileTool, WriteFileTool
from tests.helpers import TEST_MODEL, make_config


def test_create_environment_local(tmp_path: Path):
    config = make_config(tmp_path, environment_type="local")
    env = create_environment(tmp_path / "ws", config)
    assert isinstance(env, LocalEnvironment)
    assert ".git" in env.skip_names


def test_create_environment_docker(tmp_path: Path):
    config = make_config(tmp_path, environment_type="docker")
    env = create_environment(tmp_path / "ws", config, github_token="tok")
    assert isinstance(env, DockerEnvironment)
    assert env.github_token == "tok"
    assert env.auto_build is False


def test_build_agent_uses_test_model_and_registers_tools(tmp_path: Path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "app.py").write_text("x = 1\n", encoding="utf-8")

    config = make_config(tmp_path, environment_type="local")
    assert config.model_name == TEST_MODEL
    env = LocalEnvironment(workspace, skip_names=config.skip_names)
    with patch(
        "issue_agent.runtime.runner.OpenAIModel",
        return_value=MagicMock(),
    ) as mock_model:
        agent, used_env = build_agent(workspace, config, environment=env)

    mock_model.assert_called_once_with(TEST_MODEL)
    assert used_env is env
    names = {tool["name"] for tool in agent.tools.schemas()}
    assert {
        "list_dir",
        "read_file",
        "write_file",
        "search_code",
        "run_tests",
        "git_status",
        "git_diff",
    } <= names

    assert ListDirTool(env).execute(".") == "app.py"
    assert "x = 1" in ReadFileTool(env).execute("app.py")
    WriteFileTool(env).execute("app.py", "x = 2\n")
    assert env.read_file("app.py") == "x = 2\n"
