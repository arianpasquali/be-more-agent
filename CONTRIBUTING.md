# Contributing to bmo-orq

## Dev setup

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone git@github.com:arianpasquali/be-more-agent.git
cd be-more-agent
uv sync --extra dev
uv run pre-commit install
cp .env.example .env
# fill in ORQ_API_KEY
```

## Running

```bash
uv run bmo                   # run the agent (entry point)
uv run python -m bmo.main    # equivalent
```

## Tests

```bash
uv run pytest                # default: skips live tests
uv run pytest -m live        # only live tests (needs ORQ_API_KEY)
uv run pytest -v --cov       # with coverage
```

## Lint + format + types

```bash
uv run ruff format src tests scripts
uv run ruff check src tests scripts
uv run pyright
```

Pre-commit runs ruff automatically on staged files.

## Branch / PR convention

- Branch: `arianpasquali/<short-name>` (matches the `arianpasquali` prefix used throughout the repo).
- Conventional Commits in subject lines (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`, `style:`).
- Keep PRs focused on one concern.

## Releases

1. Update `CHANGELOG.md` (move `## Unreleased` content under a new `## vX.Y.Z` heading with a date).
2. Bump `version` in `pyproject.toml`.
3. Tag: `git tag -a vX.Y.Z -m "vX.Y.Z: <one-line summary>"`.
4. Push: `git push --follow-tags`.

## Adding a new orq agent / dataset / evaluator

Source-of-truth lives under `orq/`. Edit the JSON / Markdown there, then run the matching script in `scripts/`:

```bash
uv run python scripts/bootstrap_agent.py
uv run python scripts/bootstrap_dataset.py
uv run python scripts/bootstrap_evaluators.py
```

All three scripts are idempotent.
