# GitHub Issue Agent

Agent that takes a GitHub issue, explores a local workspace, applies minimal fixes, and records trajectories.

## Layout

```text
github-issue-agent/
├── configs/
├── src/issue_agent/
├── tests/
├── evals/
└── trajectories/
```

## Setup

```bash
cd github-issue-agent
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
issue-agent "Fix the failing unit test in foo.py"
```

## Configuration

- `configs/default.yaml` — workspace path, step limits, timeouts
- `configs/models.yaml` — model provider settings
