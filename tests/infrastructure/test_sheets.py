from __future__ import annotations

import ssl
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from finance_app.domain.portfolio.investment import Investment
from finance_app.domain.portfolio.snapshot import PerformanceSnapshot
from finance_app.domain.shared.errors import NotFoundError
from finance_app.domain.shared.money import Money
from finance_app.domain.shared.percentage import Rate
from finance_app.domain.simulation.value_objects import Frequency, WithdrawalPlan
from finance_app.infrastructure.config import load_settings
from finance_app.infrastructure.sheets.client import SheetsError, SheetsGateway
from finance_app.infrastructure.sheets.mappers import (
    investment_to_row,
    row_to_investment,
    row_to_snapshot,
    snapshot_to_row,
)
from finance_app.infrastructure.sheets.repository import GoogleSheetsInvestmentRepository
from finance_app.infrastructure.sheets.schema import (
    INVESTMENT_COLUMNS,
    INVESTMENTS_SHEET,
    SNAPSHOTS_SHEET,
    column_letter,
)
from tests.factories import make_params
from tests.infrastructure.fakes import FakeSheetsGateway


def make_investment() -> Investment:
    params = make_params(
        ter=Rate.from_percent(0.2),
        withdrawal=WithdrawalPlan(Money.of(300), Frequency.QUARTERLY, 60),
        apply_taxes=True,
    )
    inv = Investment.create("World ETF", date(2024, 1, 1), params, notes="core")
    inv.record_snapshot(PerformanceSnapshot(date(2024, 6, 1), Money.of(11_000), Money.of(1_200)))
    return inv


def test_column_letter() -> None:
    assert [column_letter(i) for i in (1, 20, 26, 27, 52)] == ["A", "T", "Z", "AA", "AZ"]


def test_mapper_roundtrip_with_sparse_and_string_values() -> None:
    inv = make_investment()
    row = investment_to_row(inv)
    assert len(row) == len(INVESTMENT_COLUMNS)
    as_text = [str(v) if not isinstance(v, bool) else ("TRUE" if v else "FALSE") for v in row]
    back = row_to_investment(as_text, inv.snapshots)
    assert back.parameters == inv.parameters
    assert back.name == inv.name and back.created_at == inv.created_at
    inv_id, snap = row_to_snapshot(snapshot_to_row(inv.id, inv.snapshots[0])[:3] + [11000])
    assert inv_id == inv.id and snap.contribution == Money.zero()


def test_repository_crud_against_fake_sheet() -> None:
    gateway = FakeSheetsGateway()
    repo = GoogleSheetsInvestmentRepository(gateway)
    assert repo.list() == []
    assert set(gateway.sheets) == {INVESTMENTS_SHEET, SNAPSHOTS_SHEET}
    assert gateway.sheets[INVESTMENTS_SHEET][0][0] == "id"

    first, second = make_investment(), make_investment()
    repo.save(first)
    repo.save(second)
    assert len(gateway.sheets[SNAPSHOTS_SHEET]) == 3

    loaded = repo.get(first.id)
    loaded.rename("Renamed")
    snap = loaded.snapshots[0]
    loaded.update_snapshot(snap.id, market_value=Money.of(12_000))
    loaded.record_snapshot(PerformanceSnapshot(date(2024, 12, 1), Money.of(13_000)))
    repo.save(loaded)

    fresh = GoogleSheetsInvestmentRepository(gateway)
    reloaded = fresh.get(first.id)
    assert reloaded.name == "Renamed"
    assert [s.market_value for s in reloaded.snapshots] == [Money.of(12_000), Money.of(13_000)]

    reloaded.remove_snapshot(snap.id)
    fresh.save(reloaded)
    assert len(fresh.get(first.id).snapshots) == 1

    fresh.delete(first.id)
    assert [i.id for i in fresh.list()] == [second.id]
    assert len(gateway.sheets[SNAPSHOTS_SHEET]) == 2  # header + second's snapshot
    with pytest.raises(NotFoundError):
        fresh.delete(first.id)


def test_repository_skips_corrupt_rows() -> None:
    gateway = FakeSheetsGateway()
    repo = GoogleSheetsInvestmentRepository(gateway)
    repo.save(make_investment())
    gateway.sheets[INVESTMENTS_SHEET].append(["bad-id", "x", "not-a-date"])
    repo.refresh()
    assert len(repo.list()) == 1


def _http_error(status: int) -> HttpError:
    resp = MagicMock(status=status, reason="err")
    return HttpError(resp, b"{}")


def test_gateway_retries_then_succeeds() -> None:
    request = MagicMock()
    request.execute.side_effect = [_http_error(429), _http_error(503), {"valueRanges": [{}]}]
    service = MagicMock()
    service.spreadsheets().values().batchGet.return_value = request
    sleeps: list[float] = []
    gateway = SheetsGateway(service, "sheet-id", sleep=sleeps.append)
    assert gateway.batch_get(["'A'!A1:B"]) == [[]]
    assert len(sleeps) == 2


def test_gateway_raises_on_permanent_error() -> None:
    request = MagicMock()
    request.execute.side_effect = _http_error(403)
    service = MagicMock()
    service.spreadsheets().get.return_value = request
    with pytest.raises(SheetsError):
        SheetsGateway(service, "id", sleep=lambda _: None).sheet_ids()


def test_gateway_retries_transport_errors() -> None:
    request = MagicMock()
    request.execute.side_effect = [ssl.SSLError("record layer failure"), {"sheets": []}]
    service = MagicMock()
    service.spreadsheets().get.return_value = request
    sleeps: list[float] = []
    gateway = SheetsGateway(service, "sheet-id", sleep=sleeps.append)
    assert gateway.sheet_ids() == {}
    assert len(sleeps) == 1


def test_gateway_gives_up_on_persistent_transport_error() -> None:
    request = MagicMock()
    request.execute.side_effect = ssl.SSLError("record layer failure")
    service = MagicMock()
    service.spreadsheets().get.return_value = request
    with pytest.raises(SheetsError):
        SheetsGateway(service, "id", max_retries=1, sleep=lambda _: None).sheet_ids()


def test_gateway_delete_rows_bottom_up() -> None:
    service = MagicMock()
    SheetsGateway(service, "id").delete_rows([(1, 3), (1, 7), (2, 4)])
    body: dict[str, Any] = service.spreadsheets().batchUpdate.call_args.kwargs["body"]
    starts = [r["deleteDimension"]["range"]["startIndex"] for r in body["requests"]]
    assert starts == [6, 2, 3]


def test_settings_from_file_and_env(tmp_path: Path) -> None:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[google_sheets]\nspreadsheet_id = "file-id"\ncredentials_path = "~/sa.json"\n'
        '[simulation]\nscenario_delta_pct = 3\n[ui]\nlanguage = "es"\n'
        "[[taxes.brackets]]\nupper = 1000\nrate_pct = 10\n[[taxes.brackets]]\nrate_pct = 20\n"
    )
    settings = load_settings(cfg, env={"FINANCE_SPREADSHEET_ID": "env-id"})
    assert settings.spreadsheet_id == "env-id"
    assert settings.credentials_path == Path("~/sa.json").expanduser()
    assert settings.scenario_delta_pct == 3
    assert settings.language == "es"
    assert [b.rate for b in settings.tax_brackets] == [0.1, 0.2]
    assert settings.sheets_enabled
    assert not load_settings(tmp_path / "missing.toml", env={}).sheets_enabled
