from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from issue_agent.config import load_config, project_root
from issue_agent.runtime.runner import AgentRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(message)s",
)


def main(argv: list[str] | None = None) -> int:
    load_dotenv(project_root() / ".env")
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Fetch a GitHub issue, clone the repo, run the coding agent, "
            "then branch/commit/push and open a PR."
        ),
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repo URL or owner/repo",
    )
    parser.add_argument(
        "--issue",
        required=True,
        help="Issue number or issue URL",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to default.yaml (default: <project>/configs/default.yaml)",
    )
    parser.add_argument(
        "--models-config",
        type=Path,
        default=None,
        help="Path to models.yaml (default: <project>/configs/models.yaml)",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=None,
        help="Override environment.workspace_root from config",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override model.name from config / models.yaml key",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Override agent.max_steps from config",
    )
    parser.add_argument(
        "--trajectory-dir",
        type=Path,
        default=None,
        help="Override trajectory.dir from config",
    )
    parser.add_argument(
        "--no-trajectory",
        action="store_true",
        help="Disable writing trajectory logs",
    )
    parser.add_argument(
        "--environment",
        choices=["local", "docker"],
        default=None,
        help="Override environment.type from config",
    )
    args = parser.parse_args(argv)

    config = load_config(
        config_path=args.config,
        models_path=args.models_config,
        model_override=args.model,
        max_steps_override=args.max_steps,
        workspace_root_override=args.workspace_root,
        trajectory_dir_override=args.trajectory_dir,
        no_trajectory=args.no_trajectory,
        environment_override=args.environment,
    )
    logging.info(
        "Loaded config %s (model=%s max_steps=%s env=%s)",
        config.config_path,
        config.model_name,
        config.max_steps,
        config.environment_type,
    )

    runner = AgentRunner(config=config)
    print(runner.run(args.repo, args.issue))
    return 0


if __name__ == "__main__":
    sys.exit(main())
