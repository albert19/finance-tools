# Finance manager

PySide6 personal finance desktop app with four tabs:

- **Simulator**: a compound-interest calculator that updates in real time. Inputs: initial capital, periodic contributions and their frequency, return, horizon, compounding, contribution timing, inflation, TER fees, Spanish savings tax, yearly contribution increase and withdrawals. Outputs: KPIs (final capital, contributed, interest, real value, total return, IRR), a growth chart, a yearly/monthly breakdown and a pessimistic/baseline/optimistic scenario comparison.
- **Portfolio**: save a simulation as an investment, record real performance snapshots over time, and compare them with the original projection (chart, deviation, actual XIRR vs expected rate).
- **Budget**: monthly budgets with planned income/expense lines per category (multiple lines per category allowed), a copy-from-another-month helper, an annual read-only roll-up of all months, and a category manager (rename, archive, delete-if-unused, defaults). Variance tables and charts compare planned vs actual with Favorable / On budget / Unfavorable statuses.
- **Transactions**: manual income and expense entries per month, with a kind filter and monthly totals.

Data is stored in Google Sheets through `google-api-python-client`. Without configuration the app runs in offline (in-memory) mode.

> This is a simulation only. Past performance does not guarantee future results.

## Run

```bash
uv sync
uv run finance-app
```

## Language

The UI is available in **English** and **Spanish**. Switch it from the **Language / Idioma** menu. The window is rebuilt immediately and keeps your current inputs, tab and selected investment. The choice is saved with `QSettings` (on Linux: `~/.config/finance-app/finance-app.conf`) and applied on the next start.

If no choice has been saved, the default comes from `[ui] language` in the config file or from `FINANCE_APP_LANGUAGE` (`en` / `es`). Numbers and money always use the euro format (`1.234,56 €`).

## Google Sheets setup (service account)

1. In Google Cloud Console, create a project, enable the **Google Sheets API**, and create a **service account**. Download its JSON key.
2. Create an empty Google Sheet and **share it** (Editor) with the service account email (`...@...iam.gserviceaccount.com`).
3. Copy `config.example.toml` to `~/.config/finance-app/config.toml` and set `spreadsheet_id` (from the sheet URL) and `credentials_path`. You can also export `FINANCE_SPREADSHEET_ID` and `GOOGLE_APPLICATION_CREDENTIALS`.
4. Start the app. The `Investments`, `Snapshots`, `Categories`, `Budgets`, `Budget lines` and `Transactions` tabs and their headers are created automatically.

Never commit the JSON key. `.gitignore` excludes `config.toml` and common key file names.

## Architecture (DDD)

```
src/finance_app/
  domain/          pure model: Money/Rate, SimulationParameters, CompoundInterestSimulator,
                   tax policies, IRR/XIRR, scenarios, Investment aggregate, comparison,
                   InvestmentRepository port; budget context: YearMonth, Category,
                   MonthlyBudget/BudgetLine, Transaction, variance roll-ups and repository ports
  application/     DTOs, assemblers and use cases (RunSimulation, CompareScenarios,
                   CreateInvestmentFromSimulation, RecordSnapshot, CreateMonthlyBudget,
                   RecordTransaction, GetMonthlyReport/GetAnnualReport, ...)
  infrastructure/  settings, Google Sheets gateway/schema/mappers/repositories, in-memory repos
  presentation/    PySide6 views, view models, Qt Charts, background task runner
  bootstrap.py     composition root (dependency injection)
```

The engine steps month by month. Any compounding frequency is converted to its exact equivalent monthly rate. Tests check it against `A = P(1+r/n)^(nt) + PMT·[((1+r/n)^(nt) − 1)/(r/n)]`.

## Development

```bash
uv run pytest                 # all tests (Qt tests run offscreen)
uv run ruff check . && uv run ruff format --check .
uv run mypy src
```
