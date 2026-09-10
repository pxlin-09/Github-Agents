from __future__ import annotations

import subprocess
from pathlib import Path

from issue_agent.environment.local import LocalEnvironment
from issue_agent.github.client import GitHubClient
from issue_agent.github.gitops import WorkspaceGit


def _git_init_with_commit(repo: Path) -> None:
    result = subprocess.run(
        ["git", "init"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git init failed: {result.stderr or result.stdout}")
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # Avoid depending on the default branch name across git versions.
    subprocess.run(
        ["git", "checkout", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_workspace_git_branch_commit_and_gitignore(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_init_with_commit(repo)

    env = LocalEnvironment(repo)
    git = WorkspaceGit(
        env,
        GitHubClient(token=""),
        gitignore_entries=(
            "__pycache__/",
            "*.py[cod]",
            ".pytest_cache/",
            ".issue-agent-pr-request.json",
        ),
    )

    assert git._has_git_dir()
    git.create_branch("issue-agent/issue1-test")

    env.write_file("feature.py", "def f():\n    return 1\n")
    (repo / "__pycache__").mkdir()
    (repo / "__pycache__" / "feature.cpython-312.pyc").write_bytes(b"abc")

    assert git.has_changes()
    git.commit("Add feature", author_name="issue-agent-for-demo")

    status = env.execute(["git", "status", "--porcelain"])
    assert "feature.py" not in status
    assert "__pycache__" not in status.split("??", 1)[-1] or "feature.py" not in status

    ignore = env.read_file(".gitignore")
    assert "__pycache__/" in ignore
    assert ".issue-agent-pr-request.json" in ignore

    log = env.run(["git", "log", "-1", "--pretty=%s"]).strip()
    assert log == "Add feature"

    author = env.run(["git", "log", "-1", "--pretty=%an"]).strip()
    assert author == "issue-agent-for-demo"


def test_workspace_git_redact_hides_token(tmp_path: Path):
    env = LocalEnvironment(tmp_path)
    git = WorkspaceGit(env, GitHubClient(token="super-secret-token"))
    text = git._redact(
        "fatal: https://x-access-token:super-secret-token@github.com/acme/demo.git"
    )
    assert "super-secret-token" not in text
    assert "x-access-token:***@" in text
