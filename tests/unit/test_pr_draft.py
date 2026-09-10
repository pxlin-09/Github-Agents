from __future__ import annotations

from issue_agent.github.models import GitHubIssue
from issue_agent.runtime.runner import AgentRunner, _PR_AI_NOTE


def _issue() -> GitHubIssue:
    return GitHubIssue("acme", "demo", 9, "Add feature", "details")


def test_parse_pr_draft_from_json():
    text = """
Done.

{
  "commit_message": "Add feature",
  "pr_title": "Add feature",
  "pr_body": "Implements the feature.\\n\\nFixes #9"
}
"""
    draft = AgentRunner._parse_pr_draft(text, _issue())
    assert draft.commit_message == "Add feature"
    assert draft.title == "Add feature"
    assert "Fixes #9" in draft.body


def test_parse_pr_draft_appends_fixes_when_missing():
    text = """
{
  "commit_message": "Add feature",
  "pr_title": "Add feature",
  "pr_body": "Implements the feature."
}
"""
    draft = AgentRunner._parse_pr_draft(text, _issue())
    assert draft.body.endswith("Fixes #9")


def test_parse_pr_draft_fallback_when_json_missing():
    draft = AgentRunner._parse_pr_draft("no json here", _issue())
    assert "Fix issue #9" in draft.commit_message
    assert "Fixes #9" in draft.body


def test_with_ai_note_appends_once():
    body = AgentRunner._with_ai_note("Implements the feature.")
    assert body.strip().endswith(_PR_AI_NOTE)
    again = AgentRunner._with_ai_note(body)
    assert again.count(_PR_AI_NOTE) == 1
