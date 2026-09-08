from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from pathlib import Path

from .base import Environment

logger = logging.getLogger(__name__)


class DockerEnvironment(Environment):
    """All agent + git workspace operations run inside a Docker container.

    The host directory is bind-mounted for persistence/debugging, but file I/O
    and commands go through `docker exec` so work happens in-container.
    """

    def __init__(
        self,
        workspace: Path,
        *,
        image: str = "issue-agent-sandbox:latest",
        workdir: str = "/workspace",
        network: str = "bridge",
        memory: str | None = "2g",
        cpus: str | None = "2",
        build_context: Path | None = None,
        auto_build: bool = True,
        execute_timeout: int = 120,
        github_token: str = "",
        skip_names: frozenset[str] | None = None,
    ):
        self.workspace = workspace.resolve()
        self.image = image
        self.workdir = workdir
        self.network = network
        self.memory = memory
        self.cpus = cpus
        self.build_context = build_context
        self.auto_build = auto_build
        self.execute_timeout = execute_timeout
        self.github_token = github_token
        self.skip_names = frozenset(skip_names or ())
        self.container_id: str | None = None
        self._name = f"issue-agent-{uuid.uuid4().hex[:10]}"

    def python_command(self) -> list[str]:
        return ["python"]

    def start(self) -> None:
        if shutil.which("docker") is None:
            raise RuntimeError(
                "Docker is not installed or not on PATH. "
                "Install Docker Desktop or set environment.type: local."
            )
        self.workspace.mkdir(parents=True, exist_ok=True)
        if self.auto_build:
            self._ensure_image()

        cmd = [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            self._name,
            "--network",
            self.network,
            "-v",
            f"{self.workspace}:{self.workdir}",
            "-w",
            self.workdir,
        ]
        if self.github_token:
            cmd.extend(["-e", f"GITHUB_TOKEN={self.github_token}"])
        if self.memory:
            cmd.extend(["--memory", self.memory])
        if self.cpus:
            cmd.extend(["--cpus", str(self.cpus)])
        cmd.extend([self.image, "sleep", "infinity"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start docker workspace:\n{result.stderr or result.stdout}"
            )
        self.container_id = result.stdout.strip()
        logger.info(
            "Started docker workspace %s (%s)",
            self._name,
            self.container_id[:12],
        )

    def cleanup(self) -> None:
        target = self.container_id or self._name
        subprocess.run(
            ["docker", "rm", "-f", target],
            capture_output=True,
            text=True,
            timeout=60,
        )
        logger.info("Stopped docker workspace %s", self._name)
        self.container_id = None

    def _safe_rel(self, path: str) -> str:
        text = (path or ".").strip() or "."
        candidate = Path(text)
        if candidate.is_absolute():
            raise ValueError(f"Absolute paths are not allowed: {path}")
        parts: list[str] = []
        for part in candidate.parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise ValueError(f"Path outside workspace: {path}")
            parts.append(part)
        return "/".join(parts) if parts else "."

    def resolve(self, path: str) -> Path:
        """Validate a workspace-relative path; return the host bind-mount path."""
        rel = self._safe_rel(path)
        target = (self.workspace / rel).resolve()
        if not target.is_relative_to(self.workspace):
            raise ValueError(f"Path outside workspace: {path}")
        return target

    def read_file(self, path: str) -> str:
        rel = self._safe_rel(path)
        code, out, err = self._exec_raw(["cat", "--", rel])
        if code != 0:
            raise FileNotFoundError(err or out or f"Cannot read {path}")
        return out

    def write_file(self, path: str, content: str) -> None:
        rel = self._safe_rel(path)
        parent = str(Path(rel).parent)
        if parent not in ("", "."):
            self.run(["mkdir", "-p", "--", parent])
        code, _, err = self._exec_raw(
            ["tee", "--", rel],
            input_text=content,
        )
        if code != 0:
            raise OSError(err or f"Cannot write {path}")

    def list_dir(self, path: str = ".") -> str:
        rel = self._safe_rel(path or ".")
        script = (
            "import os\n"
            f"path={rel!r}\n"
            f"skip={set(self.skip_names)!r}\n"
            "if not os.path.isdir(path):\n"
            "    raise SystemExit('not a directory')\n"
            "entries=[]\n"
            "for name in sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path,n)), n.lower())):\n"
            "    if name in skip: continue\n"
            "    entries.append(name + ('/' if os.path.isdir(os.path.join(path,name)) else ''))\n"
            "print('\\n'.join(entries) if entries else '(empty)')\n"
        )
        return self.run(["python", "-c", script]).rstrip("\n")

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
            timeout=timeout or self.execute_timeout,
        )
        if code != 0:
            detail = stderr or stdout
            if self.github_token:
                detail = detail.replace(self.github_token, "***")
            raise RuntimeError(
                f"Command failed ({code}): {' '.join(command)}\n{detail}"
            )
        return stdout

    def _exec_raw(
        self,
        command: list[str],
        *,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
        input_text: str | None = None,
    ) -> tuple[int, str, str]:
        if not self.container_id:
            return 1, "", "Error: docker workspace is not started"

        cmd = ["docker", "exec", "-i", "-w", self.workdir]
        if env:
            for key, value in env.items():
                cmd.extend(["-e", f"{key}={value}"])
        cmd.append(self.container_id)
        cmd.extend(command)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.execute_timeout,
                input=input_text,
            )
        except FileNotFoundError as exc:
            return 127, "", f"Command not found: docker\n{exc}"
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout or self.execute_timeout}s"
        return result.returncode, result.stdout, result.stderr

    def _ensure_image(self) -> None:
        inspect = subprocess.run(
            ["docker", "image", "inspect", self.image],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if inspect.returncode == 0:
            return
        if self.build_context is None or not self.build_context.exists():
            raise RuntimeError(
                f"Docker image {self.image!r} not found and no build_context "
                f"available at {self.build_context}"
            )
        logger.info("Building docker image %s from %s", self.image, self.build_context)
        build = subprocess.run(
            ["docker", "build", "-t", self.image, str(self.build_context)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if build.returncode != 0:
            raise RuntimeError(
                f"docker build failed for {self.image}:\n{build.stderr or build.stdout}"
            )
