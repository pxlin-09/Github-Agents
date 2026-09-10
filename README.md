# GitHub Issue Agent

Fetches a GitHub issue, clones the target repo into a sandboxed workspace (local or Docker), runs a coding agent to fix it, then opens a branch, commit, push, and pull request.

## Prerequisites

- Python 3.11+
- A GitHub personal access token with `repo` scope (clone, push, open PRs)
- An OpenAI API key with access to the model in `configs/models.yaml`
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (required when `environment.type` is `docker`, the default)

## Setup (step by step)

### 1. Clone this repository

```bash
git clone git@github.com:pxlin-09/Github-Agents.git
cd Github-Agents
```

If you use HTTPS:

```bash
git clone https://github.com/pxlin-09/Github-Agents.git
cd Github-Agents
```

### 2. Create and activate a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install the package

Editable install (recommended — registers the `issue-agent` CLI):

```bash
pip install -e ".[dev]"
```

Or with requirements only:

```bash
pip install -r requirements.txt
pip install -e .
```

### 4. Configure secrets

```bash
cp .env.example .env
```

Edit `.env` and set real values:

```bash
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
```

Do not commit `.env`.

### 5. (Optional) Review config

Defaults live in:

- `configs/default.yaml` — environment (`docker` / `local`), step limits, branch template, workspace skip lists
- `configs/models.yaml` — model ids (default: `gpt-5.6-luna`; tests use `gpt-5-nano`)

With Docker enabled, the first run builds `issue-agent-sandbox:latest` from `docker/sandbox/` if the image is missing. Ensure Docker is running.

## Run

From the repo root (with the venv active):

```bash
issue-agent --repo OWNER/REPO --issue ISSUE_NUMBER
```

Examples:

```bash
# owner/repo + issue number
issue-agent --repo pxlin-09/SimpleCalculator --issue 6

# full URLs also work
issue-agent --repo https://github.com/pxlin-09/SimpleCalculator --issue https://github.com/pxlin-09/SimpleCalculator/issues/6
```

Useful flags:

```bash
issue-agent --repo OWNER/REPO --issue 1 --environment local   # no Docker
issue-agent --repo OWNER/REPO --issue 1 --model gpt-5-nano    # cheapest override
issue-agent --repo OWNER/REPO --issue 1 --max-steps 20
issue-agent --repo OWNER/REPO --issue 1 --no-trajectory
```

### What one run does

1. Loads config and `.env`
2. Fetches the issue via the GitHub API
3. Starts the workspace environment (Docker container by default)
4. Clones / resets the target repo **inside** that environment
5. Creates a branch like `issue-agent/issue1-<slug>`
6. Runs the agent (list / read / write / search / pytest / git status+diff)
7. Commits, pushes, and opens a PR (body includes an AI-generated note)

Artifacts:

- Cloned workspaces under `workspace/`
- Step logs under `trajectories/` (unless `--no-trajectory`)

## Local smoke test (no clone / PR)

Against an existing checkout, without GitHub orchestration:

```bash
python scripts/smoke_query.py --environment local --workspace /path/to/repo
```

## Tests

```bash
pip install -e ".[dev]"
pytest tests/unit -q
pytest tests/integration -q   # needs OPENAI_API_KEY for live openai-marked tests
```

Live model smoke only:

```bash
pytest -m openai
```

- `tests/unit/` — config, parsing, PR draft helpers, path safety, tool registry
- `tests/integration/` — local environment, WorkspaceGit commit flow, factory/tools, agent loop (scripted + optional live nano)

## Layout

```text
Github-Agents/
├── configs/           # default.yaml, models.yaml
├── docker/sandbox/    # agent workspace image
├── scripts/           # smoke helpers
├── src/issue_agent/   # CLI, agent, tools, gitops, environments
├── tests/
├── trajectories/      # run logs (gitignored contents)
└── workspace/         # cloned target repos (gitignored)
```

## Configuration reference

| File | Purpose |
|------|---------|
| `configs/default.yaml` | `environment.type`, Docker settings, tools, limits, `github.branch_template` |
| `configs/models.yaml` | Model aliases / provider ids |
| `.env` | `OPENAI_API_KEY`, `GITHUB_TOKEN` |
