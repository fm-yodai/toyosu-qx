Before requesting review, ensure you:
- Run `uv run ruff format`, `uv run ruff check`, `uv run mypy --strict`, and `uv run pytest -q --cov=sim --maxfail=1` to keep style, typing, and coverage consistent (call out any intentional gaps in the PR description).
- Execute `uv run python quick_check.py` or the canonical `uv run python run.py ... --seed <int>` when planner/KPI behavior changes, capturing the resulting run_id + config hash from data/runs/<id>/meta.jsonl in the PR notes if results matter.
- Avoid committing files under data/runs/; note any large assets reviewers must regenerate.