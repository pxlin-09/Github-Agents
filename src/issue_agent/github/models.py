from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GitHubIssue:
    owner: str
    repo: str
    number: int
    title: str
    body: str

    def as_task(self) -> str:
        body = self.body.strip() if self.body else "(no description)"
        return (
            f"GitHub issue {self.owner}/{self.repo}#{self.number}\n"
            f"Title: {self.title}\n\n"
            f"{body}"
        )


@dataclass
class PullRequestDraft:
    commit_message: str
    title: str
    body: str
