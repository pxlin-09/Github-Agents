from __future__ import annotations

from pathlib import Path

from issue_agent.config import AppConfig
from issue_agent.environment.base import Environment
from issue_agent.environment.docker import DockerEnvironment
from issue_agent.environment.local import LocalEnvironment


def create_environment(
    workspace: Path,
    config: AppConfig,
    *,
    github_token: str = "",
) -> Environment:
    env_type = config.environment_type
    if env_type == "local":
        return LocalEnvironment(workspace, skip_names=config.skip_names)
    if env_type == "docker":
        return DockerEnvironment(
            workspace,
            image=config.docker_image,
            workdir=config.docker_workdir,
            network=config.docker_network,
            memory=config.docker_memory,
            cpus=config.docker_cpus,
            build_context=config.docker_build_context,
            auto_build=config.docker_auto_build,
            github_token=github_token,
            skip_names=config.skip_names,
        )
    raise ValueError(f"Unsupported environment type: {env_type}")
