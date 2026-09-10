from __future__ import annotations

from pathlib import Path

import pytest

from issue_agent.environment.docker import DockerEnvironment
from issue_agent.environment.local import LocalEnvironment


def test_local_resolve_rejects_escape(tmp_path: Path):
    env = LocalEnvironment(tmp_path)
    with pytest.raises(ValueError, match="outside workspace"):
        env.resolve("../secret")


def test_local_resolve_accepts_nested(tmp_path: Path):
    env = LocalEnvironment(tmp_path)
    assert env.resolve("a/b.txt") == (tmp_path / "a" / "b.txt").resolve()


def test_docker_safe_rel_rejects_absolute_and_parent(tmp_path: Path):
    env = DockerEnvironment(tmp_path, auto_build=False)
    with pytest.raises(ValueError, match="Absolute"):
        env._safe_rel("/etc/passwd")
    with pytest.raises(ValueError, match="outside workspace"):
        env._safe_rel("../secret")
    assert env._safe_rel("src/main.py") == "src/main.py"
    assert env._safe_rel(".") == "."


def test_docker_resolve_stays_in_workspace(tmp_path: Path):
    env = DockerEnvironment(tmp_path, auto_build=False)
    assert env.resolve("ok.txt") == (tmp_path / "ok.txt").resolve()
