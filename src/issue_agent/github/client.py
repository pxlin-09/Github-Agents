from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from .models import GitHubIssue

_REPO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#\s]+)",
)
_OWNER_REPO_RE = re.compile(r"^(?P<owner>[^/]+)/(?P<repo>[^/#\s]+)$")
_ISSUE_NUMBER_RE = re.compile(r"(?:/issues/|#)?(?P<number>\d+)\s*$")


def parse_repo(repo: str) -> tuple[str, str]:
    """Parse a repo URL or 'owner/repo' into (owner, repo)."""
    text = repo.strip().rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    match = _REPO_RE.search(text) or _OWNER_REPO_RE.match(text)
    if match is None:
        raise ValueError(
            "Invalid repo. Use https://github.com/owner/repo or owner/repo."
        )
    return match.group("owner"), match.group("repo")


def parse_issue_number(issue: str | int) -> int:
    """Parse an issue number or issue URL into an int."""
    if isinstance(issue, int):
        return issue
    text = issue.strip()
    if text.isdigit():
        return int(text)
    match = _ISSUE_NUMBER_RE.search(text)
    if match is None:
        raise ValueError("Invalid issue. Use a number or an issue URL.")
    return int(match.group("number"))


class GitHubClient:
    """GitHub REST API client (issue metadata + helpers).

    Clone/commit/push/PR git work runs via WorkspaceGit inside the Environment.
    """

    def __init__(self, token: str | None = None, api_base: str = "https://api.github.com"):
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
        self.api_base = api_base.rstrip("/")

    def get_issue(
        self,
        repo: str,
        issue: str | int,
    ) -> GitHubIssue:
        owner, name = parse_repo(repo)
        number = parse_issue_number(issue)
        data = self._request("GET", f"/repos/{owner}/{name}/issues/{number}")
        return GitHubIssue(
            owner=owner,
            repo=name,
            number=number,
            title=data.get("title") or "",
            body=data.get("body") or "",
        )

    def get_default_branch(self, owner: str, repo: str) -> str:
        data = self._request("GET", f"/repos/{owner}/{repo}")
        return data.get("default_branch") or "main"

    def clone_url(self, owner: str, name: str) -> str:
        if self.token:
            return (
                f"https://x-access-token:{self.token}"
                f"@github.com/{owner}/{name}.git"
            )
        return f"https://github.com/{owner}/{name}.git"

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        *,
        title: str,
        body: str,
        head: str,
        base: str,
    ) -> str:
        """Host-side PR create (used when not going through WorkspaceGit)."""
        try:
            data = self._request(
                "POST",
                f"/repos/{owner}/{repo}/pulls",
                payload={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                },
            )
            return data.get("html_url") or ""
        except RuntimeError as exc:
            if "already exists" not in str(exc).lower():
                raise
            pulls = self._request(
                "GET",
                f"/repos/{owner}/{repo}/pulls?state=open&head={owner}:{head}",
            )
            if isinstance(pulls, list) and pulls:
                return pulls[0].get("html_url") or ""
            raise

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        url = f"{self.api_base}{path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "issue-agent-for-github",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} failed: {exc.code} {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"GitHub API request failed: {exc}") from exc
