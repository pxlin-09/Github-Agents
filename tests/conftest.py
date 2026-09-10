from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from openai import AuthenticationError, OpenAIError

from issue_agent.config import project_root
from issue_agent.models.openai_model import OpenAIModel
from tests.helpers import TEST_MODEL


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "openai: live OpenAI API call (needs OPENAI_API_KEY; uses gpt-5-nano)",
    )


@pytest.fixture(scope="session", autouse=True)
def _load_env() -> None:
    load_dotenv(project_root() / ".env")
    load_dotenv()


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def openai_test_model() -> OpenAIModel:
    """Real Responses API client pointed at the cheapest test model."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key or key in {"sk-...", "ghp_..."} or key.endswith("..."):
        pytest.skip("OPENAI_API_KEY not set; skipping live model test")
    try:
        return OpenAIModel(TEST_MODEL)
    except (AuthenticationError, OpenAIError) as exc:
        pytest.skip(f"OpenAI client unavailable for live test: {exc}")
