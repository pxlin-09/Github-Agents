from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class Environment(ABC):
    """Workspace the agent can inspect and mutate."""

    workspace: Path
    skip_names: frozenset[str] = frozenset()

    @abstractmethod
    def read_file(self, path: str) -> str:
        pass

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        pass

    @abstractmethod
    def list_dir(self, path: str = ".") -> str:
        pass

    @abstractmethod
    def execute(self, command: list[str]) -> str:
        """Run a command for the agent; always returns a formatted string."""

    @abstractmethod
    def run(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> str:
        """Run a command for orchestration; raises on non-zero exit."""

    def python_command(self) -> list[str]:
        import sys

        return [sys.executable]

    def start(self) -> None:
        """Optional setup (e.g. start a container)."""

    def cleanup(self) -> None:
        """Optional teardown."""
