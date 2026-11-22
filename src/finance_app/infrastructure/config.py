"""Application settings loaded from a TOML file and environment variables.

Lookup order (later wins): defaults -> config file -> environment variables.
Config file: ``$FINANCE_APP_CONFIG`` or ``$XDG_CONFIG_HOME/finance-app/config.toml``
(defaults to ``~/.config/finance-app/config.toml``).
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finance_app.domain.simulation.tax_policy import SPANISH_SAVINGS_BRACKETS, TaxBracket


@dataclass(frozen=True, slots=True)
class Settings:
    spreadsheet_id: str | None = None
    credentials_path: Path | None = None
    tax_brackets: tuple[TaxBracket, ...] = SPANISH_SAVINGS_BRACKETS
    scenario_delta_pct: float = 2.0
    deviation_tolerance_pct: float = 2.0
    budget_tolerance_pct: float = 2.0
    language: str = "en"
    config_path: Path | None = None

    @property
    def sheets_enabled(self) -> bool:
        return bool(self.spreadsheet_id and self.credentials_path)


def default_config_path(env: Mapping[str, str] = os.environ) -> Path:
    if env.get("FINANCE_APP_CONFIG"):
        return Path(env["FINANCE_APP_CONFIG"]).expanduser()
    base = Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "finance-app" / "config.toml"


def _brackets(raw: Any) -> tuple[TaxBracket, ...]:
    if not raw:
        return SPANISH_SAVINGS_BRACKETS
    return tuple(
        TaxBracket(
            upper=float(b["upper"]) if b.get("upper") is not None else None,
            rate=float(b["rate_pct"]) / 100,
        )
        for b in raw
    )


def load_settings(path: Path | None = None, env: Mapping[str, str] = os.environ) -> Settings:
    path = path or default_config_path(env)
    data: dict[str, Any] = {}
    if path.is_file():
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    sheets = data.get("google_sheets", {})
    spreadsheet_id = env.get("FINANCE_SPREADSHEET_ID") or sheets.get("spreadsheet_id")
    credentials = env.get("GOOGLE_APPLICATION_CREDENTIALS") or sheets.get("credentials_path")
    return Settings(
        spreadsheet_id=spreadsheet_id or None,
        credentials_path=Path(credentials).expanduser() if credentials else None,
        tax_brackets=_brackets(data.get("taxes", {}).get("brackets")),
        scenario_delta_pct=float(data.get("simulation", {}).get("scenario_delta_pct", 2.0)),
        deviation_tolerance_pct=float(
            data.get("portfolio", {}).get("deviation_tolerance_pct", 2.0)
        ),
        budget_tolerance_pct=float(data.get("budget", {}).get("tolerance_pct", 2.0)),
        language=env.get("FINANCE_APP_LANGUAGE") or str(data.get("ui", {}).get("language", "en")),
        config_path=path,
    )
