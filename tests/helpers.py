from __future__ import annotations

from pathlib import Path

from issue_agent.config import AppConfig, DEFAULT_BRANCH_TEMPLATE
from issue_agent.runtime.limits import RunLimits

# Cheapest OpenAI model — used whenever tests construct a real/config model.
TEST_MODEL = "gpt-5-nano"


def make_config(
    tmp_path: Path,
    *,
    environment_type: str = "local",
    tools: tuple[str, ...] = ("filesystem", "search", "testing", "git"),
    skip_names: frozenset[str] | None = None,
    gitignore_entries: tuple[str, ...] = (
        "__pycache__/",
        "*.py[cod]",
        ".pytest_cache/",
    ),
    branch_template: str = DEFAULT_BRANCH_TEMPLATE,
    agent_name_template: str = "issue-agent-for-{repo}",
    max_steps: int = 10,
    max_test_runs: int = 3,
    model_name: str = TEST_MODEL,
) -> AppConfig:
    return AppConfig(
        model_name=model_name,
        max_steps=max_steps,
        workspace_root=tmp_path / "workspaces",
        trajectory_dir=None,
        limits=RunLimits(
            max_steps=max_steps,
            max_cost_usd=1.0,
            max_runtime_seconds=60,
            max_test_runs=max_test_runs,
        ),
        agent_name_template=agent_name_template,
        branch_template=branch_template,
        environment_type=environment_type,
        tools=tools,
        skip_names=skip_names
        if skip_names is not None
        else frozenset({".git", "__pycache__", "node_modules"}),
        gitignore_entries=gitignore_entries,
        config_path=tmp_path / "default.yaml",
        models_path=tmp_path / "models.yaml",
        docker_image="issue-agent-sandbox:latest",
        docker_workdir="/workspace",
        docker_network="bridge",
        docker_memory="1g",
        docker_cpus="1",
        docker_build_context=None,
        docker_auto_build=False,
    )
