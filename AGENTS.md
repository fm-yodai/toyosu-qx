# Repository Guidelines

## Project Structure & Module Organization
`main.py` offers a minimal DES harness while `run.py` is the full CLI that loads YAML scenarios and orchestrates report generation; prefer developing new flows inside `sim/` (engine, demand, planner, KPI, viz modules) so both entry points may reuse them. Scenario and global parameters live in `config/` (`config.yaml` for core knobs, `config/scenario/*.yaml` per demand profile). Simulation outputs and artifacts are stored under `data/runs/{run_id}/`, so avoid committing that tree. Documentation that explains architecture, visualization, and glossary details sits in `docs/`, and exploratory workflows belong to `notebooks/`. Keep lightweight utilities such as `generate_report.py` and `quick_check.py` in the repo root for easy invocation.

## Build, Test, and Development Commands
- `uv sync` — install and lock all runtime + dev dependencies declared in `pyproject.toml`.
- `uv run python run.py --scenario config/scenario/default.yaml --config config/config.yaml --seed 42` — execute the canonical simulation pipeline and emit dashboards into `data/runs/`.
- `uv run python generate_report.py <run_id> --scenario …` — rebuild dashboards from an existing run.
- `uv run pytest -q` — run the test suite; add `--cov=sim --maxfail=1` before opening a PR.
- `uv run python quick_check.py` — fast deterministic smoke test that exercises the planner without producing reports.

## Coding Style & Naming Conventions
Target Python 3.12+ and keep files type-hinted end-to-end; run `uv run mypy --strict` before committing. Adopt Ruff’s defaults (`uv run ruff format && uv run ruff check`) for formatting and linting, and prefer 4-space indents with snake_case symbols (`TareEvent`-style dataclasses may use PascalCase). Align module names with their responsibility (`sim/engine.py`, `sim/planner_rule.py`, etc.) and place scenario fixtures under `config/scenario/` with kebab-case filenames.

## Testing Guidelines
Pytest is the reference harness; create mirrors of the runtime modules under `tests/` using `test_<module>.py` naming and descriptive test function names such as `test_dispatch_queue_handles_idle_gap`. When contributing new KPIs or planner logic, provide property-style tests plus a targeted integration run via `quick_check.py`. Shoot for ≥85% coverage on the touched package as enforced by `pytest-cov`; if coverage temporarily dips, explain the trade-off in the PR and add TODO links to follow-up issues.

## Commit & Pull Request Guidelines
The current history uses concise sentence-case summaries (e.g., `Initial commit`); continue using short imperative statements under ~70 characters, optionally prefixed with a conventional type (`feat`, `fix`, `chore`). Each PR should include: a one-paragraph rationale, bullet-pointed changes, reproduction steps (`uv run …` commands), linked issues, and screenshots/GIFs for visualization updates. Always mention whether you ran `mypy`, `ruff`, and `pytest`, and call out any data files that reviewers must regenerate.

## Security & Configuration Tips
Never commit secrets in YAML configs; instead, add overrides via environment variables or ignored files. Deterministic experiments require fixed seeds (`--seed <int>`) plus tracking of the scenario hash that `run.py` logs into `data/runs/<id>/meta.jsonl`, so capture that metadata in PR descriptions when results matter. Clean up large Parquet outputs before pushing to keep the repository lean.
