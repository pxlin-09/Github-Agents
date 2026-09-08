from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .base import Environment


class LocalEnvironment(Environment):
    def __init__(
        self,
        workspace: Path,
        *,
        skip_names: frozenset[str] | None = None,
    ):
        self.workspace = workspace.resolve()
        self.skip_names = frozenset(skip_names or ())

    def resolve(self, path: str) -> Path:
        target = (self.workspace / path).resolve()
        if not target.is_relative_to(self.workspace):
            raise ValueError(f"Path outside workspace: {path}")
        return target

    def read_file(self, path: str) -> str:
        return self.resolve(path).read_text(errors="replace")

    def write_file(self, path: str, content: str) -> None:
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def list_dir(self, path: str = ".") -> str:
        target = self.resolve(path or ".")
        if not target.exists():
            raise FileNotFoundError(f"No such directory: {path}")
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        entries: list[str] = []
        for child in sorted(
            target.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        ):
            if child.name in self.skip_names:
                continue
            entries.append(f"{child.name}/" if child.is_dir() else child.name)
        return "\n".join(entries) if entries else "(empty)"

    def python_command(self) -> list[str]:
        return [sys.executable]

    def _exec_raw(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int | None = 60,
        input_text: str | None = None,
    ) -> tuple[int, str, str]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        try:
            result = subprocess.run(
                command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=merged,
                input=input_text,
            )
        except FileNotFoundError as exc:
            return 127, "", f"Command not found: {command[0]}\n{exc}"
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout}s"
        return result.returncode, result.stdout, result.stderr

    def execute(self, command: list[str]) -> str:
        code, stdout, stderr = self._exec_raw(command)
        return f"exit_code={code}\nstdout:\n{stdout}\nstderr:\n{stderr}"

    def run(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> str:
        code, stdout, stderr = self._exec_raw(
            command,
            env=env,
            timeout=timeout or 120,
        )
        if code != 0:
            raise RuntimeError(
                f"Command failed ({code}): {' '.join(command)}\n{stderr or stdout}"
            )
        return stdout
