from __future__ import annotations

import textwrap

from .base import Tool


class SearchTool(Tool):
    name = "search_code"
    description = "Search source code in the repository."

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
                    "query": {
                        "type": "string",
                    }
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "strict": True,
        }

    def execute(self, query: str) -> str:
        command = ["rg", "-n", "--hidden"]
        for name in sorted(self.environment.skip_names):
            command.extend(["--glob", f"!{name}", "--glob", f"!**/{name}/**"])
        command.extend([query, "."])
        result = self.environment.execute(command)
        if (
            result.startswith("exit_code=127")
            or "Command not found: rg" in result
        ):
            return self._python_search(query)
        return result

    def _python_search(self, query: str) -> str:
        script = textwrap.dedent(
            f"""\
            from pathlib import Path
            skip = {sorted(self.environment.skip_names)!r}
            query = {query!r}
            matches = []
            root = Path(".")
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if any(part in skip for part in path.parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for line_no, line in enumerate(text.splitlines(), start=1):
                    if query in line:
                        matches.append(f"{{path}}:{{line_no}}:{{line}}")
                        if len(matches) >= 200:
                            print("\\n".join(matches))
                            raise SystemExit(0)
            print("\\n".join(matches) if matches else f"No matches for {{query!r}}")
            """
        )
        return self.environment.execute(["python", "-c", script])
