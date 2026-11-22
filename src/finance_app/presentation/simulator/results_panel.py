from __future__ import annotations

from PySide6.QtWidgets import QWidget

from finance_app.application.dto import SummaryDTO
from finance_app.presentation import theme
from finance_app.presentation.formatting import duration, money, percent
from finance_app.presentation.i18n import tr
from finance_app.presentation.widgets.kpi import KpiGrid

_CARDS = [
    ("final_capital", "Final capital", "Total accumulated at the end of the horizon (before tax)."),
    ("total_contributed", "Total contributed", "Money invested from your own pocket."),
    (
        "interest_earned",
        "Interest earned",
        "Final capital + withdrawals − contributions (net of fees): the compounding effect.",
    ),
    ("real_value", "Inflation-adjusted value", "Final capital in today's money."),
    ("net_capital", "Final capital after tax", "If fully liquidated at the end."),
    ("total_return", "Total return", "Interest earned / total contributed."),
    (
        "irr",
        "Equivalent annual rate (IRR)",
        "Money-weighted annual return of all cash flows (before / after tax).",
    ),
    ("costs", "Fees & taxes", "Total fees (TER) and taxes paid or due."),
]


class ResultsPanel(KpiGrid):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(_CARDS, columns=4, parent=parent)

    def show_summary(self, s: SummaryDTO) -> None:
        c = self.cards
        c["final_capital"].set_value(
            money(s.final_capital),
            tr("Withdrawn: {value}", value=money(s.total_withdrawn)) if s.total_withdrawn else "",
        )
        c["total_contributed"].set_value(money(s.total_contributed))
        c["interest_earned"].set_value(
            money(s.interest_earned),
            color=theme.POSITIVE if s.interest_earned >= 0 else theme.NEGATIVE,
        )
        c["real_value"].set_value(
            money(s.real_final_capital),
            tr("After tax: {value}", value=money(s.real_final_capital_net)),
        )
        hint = (
            tr("Depleted after {duration}", duration=duration(s.depletion_month))
            if s.depletion_month
            else ""
        )
        c["net_capital"].set_value(
            money(s.final_capital_net), hint, color=theme.NEGATIVE if s.depletion_month else None
        )
        c["total_return"].set_value(percent(s.total_return_pct, signed=True))
        c["irr"].set_value(
            percent(s.irr_pct), tr("After tax: {value}", value=percent(s.irr_net_pct))
        )
        c["costs"].set_value(
            money(s.total_fees + s.total_taxes),
            tr("Fees {fees} · Taxes {taxes}", fees=money(s.total_fees), taxes=money(s.total_taxes)),
        )
