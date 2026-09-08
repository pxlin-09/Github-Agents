from __future__ import annotations

import json
import re
import textwrap

from issue_agent.environment.base import Environment
from issue_agent.github.client import GitHubClient, parse_repo


class WorkspaceGit:
    """Git + PR operations executed through the active Environment.

    In docker mode every command runs inside the container via `docker exec`.
    """

    def __init__(
        self,
        environment: Environment,
        github: GitHubClient,
        *,
        gitignore_entries: tuple[str, ...] = (),
    ):
        self.env = environment
        self.github = github
        self.gitignore_entries = gitignore_entries

    def ensure_repo(self, repo: str) -> None:
        owner, name = parse_repo(repo)
        if self._has_git_dir():
            self._ensure_remote_auth(owner, name)
            return

        self._clear_workdir()
        url = self.github.clone_url(owner, name)
        self._git("clone", "--", url, ".", timeout=300)

    def prepare_workspace(self, owner: str, repo: str) -> str:
        self._ensure_remote_auth(owner, repo)
        default = self.github.get_default_branch(owner, repo)
        self._git("fetch", "origin", timeout=180)
        self._git("checkout", default)
        self._git("reset", "--hard", f"origin/{default}")
        self._git("clean", "-fd")
        return default

    def create_branch(self, branch: str) -> None:
        self._git("checkout", "-B", branch)

    def has_changes(self) -> bool:
        self._ensure_ignore_rules()
        return bool(self._git("status", "--porcelain").strip())

    def commit(
        self,
        message: str,
        *,
        author_name: str,
        author_email: str | None = None,
    ) -> None:
        self._stage_changes()
        if not self._git("diff", "--cached").strip():
            raise RuntimeError("Nothing to commit")

        email = author_email or f"{author_name}@users.noreply.github.com"
        env = {
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": email,
        }
        self._git("commit", "-m", message, env=env)

    def push(self, owner: str, repo: str, branch: str) -> None:
        url = self.github.clone_url(owner, repo)
        self._git(
            "push",
            "--force-with-lease",
            "-u",
            url,
            f"HEAD:{branch}",
            timeout=180,
        )

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
        """Create (or reuse) a PR using Python inside the environment."""
        request_path = ".issue-agent-pr-request.json"
        self.env.write_file(
            request_path,
            json.dumps(
                {
                    "api_base": self.github.api_base,
                    "owner": owner,
                    "repo": repo,
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base,
                }
            ),
        )
        script = textwrap.dedent(
            f"""\
            import json, os, urllib.error, urllib.request

            with open({request_path!r}, encoding="utf-8") as fh:
                cfg = json.load(fh)

            token = os.environ.get("GITHUB_TOKEN", "")
            api_base = cfg["api_base"]
            owner = cfg["owner"]
            repo = cfg["repo"]
            payload = {{
                "title": cfg["title"],
                "body": cfg["body"],
                "head": cfg["head"],
                "base": cfg["base"],
            }}

            def request(method, path, body=None):
                url = api_base + path
                headers = {{
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "issue-agent-for-github",
                }}
                if token:
                    headers["Authorization"] = f"Bearer {{token}}"
                data = None
                if body is not None:
                    data = json.dumps(body).encode("utf-8")
                    headers["Content-Type"] = "application/json"
                req = urllib.request.Request(url, data=data, method=method, headers=headers)
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        raw = resp.read().decode("utf-8")
                        return json.loads(raw) if raw else {{}}
                except urllib.error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"HTTP {{exc.code}} {{detail}}") from exc

            try:
                data = request("POST", f"/repos/{{owner}}/{{repo}}/pulls", payload)
                print(data.get("html_url") or "")
            except RuntimeError as exc:
                text = str(exc)
                if "already exists" not in text.lower():
                    raise
                head = payload["head"]
                pulls = request(
                    "GET",
                    f"/repos/{{owner}}/{{repo}}/pulls?state=open&head={{owner}}:{{head}}",
                )
                if isinstance(pulls, list) and pulls:
                    print(pulls[0].get("html_url") or "")
                else:
                    raise
            """
        )
        env = {"GITHUB_TOKEN": self.github.token} if self.github.token else None
        try:
            return self.env.run(["python", "-c", script], env=env, timeout=60).strip()
        finally:
            self.env.execute(["rm", "-f", "--", request_path])

    def _has_git_dir(self) -> bool:
        result = self.env.execute(["test", "-d", ".git"])
        first = result.split("\n", 1)[0]
        return first.strip() == "exit_code=0"

    def _clear_workdir(self) -> None:
        script = textwrap.dedent(
            """\
            import pathlib, shutil
            root = pathlib.Path(".")
            for path in list(root.iterdir()):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            """
        )
        self.env.run(["python", "-c", script], timeout=60)

    def _ensure_ignore_rules(self) -> None:
        if not self.gitignore_entries:
            return
        try:
            existing = self.env.read_file(".gitignore")
        except FileNotFoundError:
            existing = ""
        missing = [line for line in self.gitignore_entries if line not in existing]
        if not missing:
            return
        addition = ("\n" if existing and not existing.endswith("\n") else "")
        addition += "\n".join(missing) + "\n"
        self.env.write_file(".gitignore", existing + addition)

    def _stage_changes(self) -> None:
        self._ensure_ignore_rules()
        # Ignore failure if __pycache__ was never tracked.
        staged = self.env.execute(
            ["git", "rm", "-r", "--cached", "--ignore-unmatch", "__pycache__"]
        )
        if "exit_code=0" not in staged.split("\n", 1)[0]:
            pass
        self._git("add", "-A")

    def _ensure_remote_auth(self, owner: str, repo: str) -> None:
        if not self.github.token:
            return
        self._git(
            "remote",
            "set-url",
            "origin",
            self.github.clone_url(owner, repo),
        )

    def _git(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        timeout: int | None = 120,
    ) -> str:
        try:
            return self.env.run(["git", *args], env=env, timeout=timeout)
        except RuntimeError as exc:
            raise RuntimeError(self._redact(str(exc))) from None

    def _redact(self, text: str) -> str:
        if self.github.token:
            text = text.replace(self.github.token, "***")
        return re.sub(
            r"https://x-access-token:[^@\s]+@",
            "https://x-access-token:***@",
            text,
        )
