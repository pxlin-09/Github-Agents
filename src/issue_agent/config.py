from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from issue_agent.runtime.limits import RunLimits

DEFAULT_SKIP_NAMES: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
)

DEFAULT_GITIGNORE_ENTRIES: tuple[str, ...] = (
    "__pycache__/",
    "*.py[cod]",
    ".pytest_cache/",
    ".issue-agent-pr-request.json",
)

DEFAULT_BRANCH_TEMPLATE = "issue-agent/issue{issue}-{slug}"


def project_root() -> Path:
    """github-issue-agent/ (repo root containing configs/)."""
    return Path(__file__).resolve().parents[2]


def slugify(text: str, *, max_length: int = 50) -> str:
    """Turn an issue title into a git-safe branch slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if max_length and len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "issue"


@dataclass(frozen=True)
class AppConfig:
    model_name: str
    max_steps: int
    workspace_root: Path
    trajectory_dir: Path | None
    limits: RunLimits
    agent_name_template: str
    branch_template: str
    environment_type: str
    tools: tuple[str, ...]
    skip_names: frozenset[str]
    gitignore_entries: tuple[str, ...]
    config_path: Path
    models_path: Path
    docker_image: str
    docker_workdir: str
    docker_network: str
    docker_memory: str | None
    docker_cpus: str | None
    docker_build_context: Path | None
    docker_auto_build: bool

    def agent_name(self, *, owner: str, repo: str, issue: int | None = None) -> str:
        return self.agent_name_template.format(
            owner=owner,
            repo=repo,
            issue=issue if issue is not None else "",
        )

    def branch_name(self, issue_number: int, issue_title: str) -> str:
        slug = slugify(issue_title)
        return self.branch_template.format(
            issue=issue_number,
            slug=slug,
        )


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def _resolve_model_name(models_cfg: dict[str, Any], requested: str | None) -> str:
    models = models_cfg.get("models") or {}
    default_key = models_cfg.get("default")
    key = requested or default_key
    if key is None:
        raise ValueError("No model specified and models.yaml has no default")

    entry = models.get(key)
    if isinstance(entry, dict) and entry.get("model"):
        return str(entry["model"])
    return str(key)


def load_config(
    config_path: Path | None = None,
    models_path: Path | None = None,
    *,
    model_override: str | None = None,
    max_steps_override: int | None = None,
    workspace_root_override: Path | None = None,
    trajectory_dir_override: Path | None = None,
    no_trajectory: bool = False,
    environment_override: str | None = None,
) -> AppConfig:
    root = project_root()
    config_file = (config_path or root / "configs" / "default.yaml").resolve()
    models_file = (models_path or root / "configs" / "models.yaml").resolve()

    raw = _read_yaml(config_file)
    models_cfg = _read_yaml(models_file)

    agent = raw.get("agent") or {}
    model = raw.get("model") or {}
    environment = raw.get("environment") or {}
    trajectory = raw.get("trajectory") or {}
    github = raw.get("github") or {}
    limits_raw = raw.get("limits") or {}
    docker = environment.get("docker") or {}
    workspace_cfg = raw.get("workspace") or {}
    tools = tuple(raw.get("tools") or ())

    skip_raw = workspace_cfg.get("skip")
    skip_names = frozenset(
        str(item) for item in (skip_raw if skip_raw is not None else DEFAULT_SKIP_NAMES)
    )
    gitignore_raw = workspace_cfg.get("gitignore")
    gitignore_entries = tuple(
        str(item)
        for item in (
            gitignore_raw
            if gitignore_raw is not None
            else DEFAULT_GITIGNORE_ENTRIES
        )
    )

    model_name = _resolve_model_name(
        models_cfg,
        model_override or model.get("name"),
    )
    max_steps = (
        max_steps_override
        if max_steps_override is not None
        else int(
            limits_raw.get(
                "max_steps",
                agent.get("max_steps", 40),
            )
        )
    )

    workspace_root = workspace_root_override or Path(
        environment.get("workspace_root", "workspace")
    )
    if not workspace_root.is_absolute():
        workspace_root = (Path.cwd() / workspace_root).resolve()

    traj_enabled = bool(trajectory.get("enabled", True)) and not no_trajectory
    if trajectory_dir_override is not None:
        trajectory_dir = trajectory_dir_override
    elif traj_enabled:
        trajectory_dir = Path(trajectory.get("dir", "trajectories"))
    else:
        trajectory_dir = None
    if trajectory_dir is not None and not trajectory_dir.is_absolute():
        trajectory_dir = (Path.cwd() / trajectory_dir).resolve()

    limits = RunLimits(
        max_steps=max_steps,
        max_cost_usd=float(limits_raw.get("max_cost_usd", 2.0)),
        max_runtime_seconds=int(limits_raw.get("max_runtime_seconds", 900)),
        max_test_runs=int(limits_raw.get("max_test_runs", 10)),
    )

    build_context_raw = docker.get("build_context", "docker/sandbox")
    build_context: Path | None
    if build_context_raw:
        build_context = Path(build_context_raw)
        if not build_context.is_absolute():
            build_context = (root / build_context).resolve()
    else:
        build_context = None

    return AppConfig(
        model_name=model_name,
        max_steps=max_steps,
        workspace_root=workspace_root,
        trajectory_dir=trajectory_dir,
        limits=limits,
        agent_name_template=str(
            agent.get("name_template", "issue-agent-for-{repo}")
        ),
        branch_template=str(
            github.get("branch_template", DEFAULT_BRANCH_TEMPLATE)
        ),
        environment_type=str(
            environment_override or environment.get("type", "local")
        ),
        tools=tools,
        skip_names=skip_names,
        gitignore_entries=gitignore_entries,
        config_path=config_file,
        models_path=models_file,
        docker_image=str(docker.get("image", "issue-agent-sandbox:latest")),
        docker_workdir=str(docker.get("workdir", "/workspace")),
        docker_network=str(docker.get("network", "bridge")),
        docker_memory=(
            None if docker.get("memory") in (None, "", False) else str(docker.get("memory"))
        ),
        docker_cpus=(
            None if docker.get("cpus") in (None, "", False) else str(docker.get("cpus"))
        ),
        docker_build_context=build_context,
        docker_auto_build=bool(docker.get("auto_build", True)),
    )
