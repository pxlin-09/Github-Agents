from __future__ import annotations

import pytest

from issue_agent.github.client import GitHubClient, parse_issue_number, parse_repo
from issue_agent.github.models import GitHubIssue


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("acme/demo", ("acme", "demo")),
        ("https://github.com/acme/demo", ("acme", "demo")),
        ("https://github.com/acme/demo.git", ("acme", "demo")),
        ("https://www.github.com/acme/demo/", ("acme", "demo")),
    ],
)
def test_parse_repo_valid(raw: str, expected: tuple[str, str]):
    assert parse_repo(raw) == expected


def test_parse_repo_invalid():
    with pytest.raises(ValueError, match="Invalid repo"):
        parse_repo("not-a-repo")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (7, 7),
        ("7", 7),
        ("#7", 7),
        ("https://github.com/acme/demo/issues/12", 12),
    ],
)
def test_parse_issue_number_valid(raw, expected: int):
    assert parse_issue_number(raw) == expected


def test_parse_issue_number_invalid():
    with pytest.raises(ValueError, match="Invalid issue"):
        parse_issue_number("no-number-here")


def test_github_issue_as_task_with_body():
    issue = GitHubIssue(
        owner="acme",
        repo="demo",
        number=1,
        title="Add power",
        body="Please add x**n",
    )
    task = issue.as_task()
    assert "acme/demo#1" in task
    assert "Add power" in task
    assert "Please add x**n" in task


def test_github_issue_as_task_empty_body():
    issue = GitHubIssue("acme", "demo", 2, "Title", "")
    assert "(no description)" in issue.as_task()


def test_clone_url_with_and_without_token():
    assert GitHubClient(token="").clone_url("acme", "demo") == (
        "https://github.com/acme/demo.git"
    )
    assert GitHubClient(token="secret").clone_url("acme", "demo") == (
        "https://x-access-token:secret@github.com/acme/demo.git"
    )
