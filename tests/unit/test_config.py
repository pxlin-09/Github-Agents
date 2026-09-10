from __future__ import annotations

from pathlib import Path

from issue_agent.config import (
    DEFAULT_BRANCH_TEMPLATE,
    load_config,
    slugify,
)
from tests.helpers import make_config


def test_slugify_basic():
    assert slugify("Add power function") == "add-power-function"


def test_slugify_strips_punctuation_and_collapses_hyphens():
    assert slugify("  Fix: divide-by-zero!!!  ") == "fix-divide-by-zero"


def test_slugify_empty_falls_back():
    assert slugify("") == "issue"
    assert slugify("@@@") == "issue"


def test_slugify_truncates():
    long_title = "a" * 80
    assert len(slugify(long_title, max_length=20)) == 20


def test_branch_name_uses_issue_and_slug(tmp_path: Path):
    config = make_config(tmp_path, branch_template=DEFAULT_BRANCH_TEMPLATE)
    assert (
        config.branch_name(1, "Add power function")
        == "issue-agent/issue1-add-power-function"
    )


def test_agent_name_formats_repo(tmp_path: Path):
    config = make_config(tmp_path)
    assert config.agent_name(owner="acme", repo="demo", issue=3) == (
        "issue-agent-for-demo"
    )


def test_load_config_reads_workspace_skip(tmp_path: Path):
    default = tmp_path / "default.yaml"
    models = tmp_path / "models.yaml"
    default.write_text(
        """
model:
  name: gpt-5-nano
environment:
  type: local
  workspace_root: ws
workspace:
  skip:
    - .git
    - custom_skip
  gitignore:
    - custom_ignore/
tools:
  - filesystem
limits:
  max_steps: 7
""",
        encoding="utf-8",
    )
    models.write_text(
        """
default: gpt-5-nano
models:
  gpt-5-nano:
    model: gpt-5-nano
""",
        encoding="utf-8",
    )

    config = load_config(
        config_path=default,
        models_path=models,
        no_trajectory=True,
    )
    assert config.environment_type == "local"
    assert config.max_steps == 7
    assert "custom_skip" in config.skip_names
    assert config.gitignore_entries == ("custom_ignore/",)
