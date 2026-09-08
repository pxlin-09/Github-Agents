"""Read-only git tools available to the agent.

Clone, branch, commit, push, and PR creation are handled by the program
(see issue_agent.github.gitops), not by agent tools.
"""

from .base import Tool


class GitStatusTool(Tool):
    name = "git_status"
    description = (
        "Show git status for the workspace repository. "
        "Read-only; cannot modify git state."
    )

    def __init__(self, environment):
        self.environment = environment

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self) -> str:
        return self.environment.execute(["git", "status", "--short"])


class GitDiffTool(Tool):
    name = "git_diff"
    description = (
        "Show the git diff for the workspace (read-only). "
        "Pass an empty path for the full diff, or a relative file path."
    )

    def __init__(self, environment):
        self.environment = environment

    def schema(self):
        return {
            "type": "function",
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Optional workspace-relative path to diff. "
                            "Use an empty string for the full workspace diff."
                        ),
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, path: str = "") -> str:
        command = ["git", "diff"]
        if path:
            try:
                self.environment.resolve(path)
            except ValueError as exc:
                return f"Error: {exc}"
            command.extend(["--", path])
        return self.environment.execute(command)
