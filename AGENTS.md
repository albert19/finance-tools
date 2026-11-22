# AGENTS.md

- Python package in `src/finance_app` (PySide6 + Google Sheets), managed with **uv**. Spec lives in `requirements.txt` (it is NOT a pip requirements file; deps are in `pyproject.toml`).
- Setup: `uv sync`. Run: `uv run finance-app`.
- Verify after changes:
  - `uv run pytest` (Qt tests use `QT_QPA_PLATFORM=offscreen`, set in `tests/conftest.py`)
  - `uv run ruff check . && uv run ruff format --check .`
  - `uv run mypy src`
- Layering: `domain` must not import Qt/Google/application; `application` depends only on `domain`; `presentation` talks to use cases/DTOs; wiring happens in `bootstrap.py`.
- Bounded contexts in `domain/`: `simulation`, `portfolio`, `budget` (categories, monthly budgets, transactions, variance roll-ups), `shared` (Money, errors). Google Sheets tabs: `Investments`, `Snapshots`, `Categories`, `Budgets`, `Budget lines`, `Transactions`.
- UI tests must not trigger modal dialogs (patch `QMessageBox` as in `tests/presentation/test_ui.py`).
- Use `presentation.widgets.named()` instead of `objectName=` kwargs (PySide stubs reject them under mypy).
- i18n: wrap every user-facing string in `tr("English text", **placeholders)` from `presentation/i18n.py` at widget-build time; use `N_("...")` for module-level constants and call `tr()` when displaying them. Add the Spanish text to `presentation/translations/es.py`. `tests/presentation/test_i18n.py` fails on missing keys (including domain validation messages, which are translated in the UI) or mismatched placeholders.
- Pin new dependencies to versions published at least 7 days ago.
