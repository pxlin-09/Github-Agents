"""Local smoke test without GitHub clone (uses an existing workspace)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from issue_agent.config import load_config, project_root
from issue_agent.runtime.runner import build_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)

_DEFAULT_WORKSPACE = Path(__file__).resolve().parents[2] / "calculator"
_DEFAULT_QUERY = (
    "The calculator project has a bug: dividing by zero crashes. "
    "Inspect the code, fix div.py so divide-by-zero returns None, "
    "and run pytest until the tests pass. Keep the change minimal."
)


def main() -> int:
    load_dotenv(project_root() / ".env")
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run the agent against a local workspace (no clone).",
    )
    parser.add_argument("query", nargs="?", default=_DEFAULT_QUERY)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=_DEFAULT_WORKSPACE,
        help="Existing workspace path (default: ../calculator)",
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--trajectory-dir", type=Path, default=None)
    parser.add_argument("--no-trajectory", action="store_true")
    parser.add_argument(
        "--environment",
        choices=["local", "docker"],
        default="local",
        help="Workspace backend (default: local for smoke tests)",
    )
    args = parser.parse_args()

    config = load_config(
        config_path=args.config,
        model_override=args.model,
        max_steps_override=args.max_steps,
        trajectory_dir_override=args.trajectory_dir,
        no_trajectory=args.no_trajectory,
        environment_override=args.environment,
    )
    agent, environment = build_agent(
        workspace=args.workspace.resolve(),
        config=config,
    )
    environment.start()
    try:
        print(agent.run(args.query))
    finally:
        environment.cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
