from __future__ import annotations

import copy

from finance_app.domain.portfolio.investment import Investment
from finance_app.domain.portfolio.repository import InvestmentRepository
from finance_app.domain.shared.errors import NotFoundError


class InMemoryInvestmentRepository(InvestmentRepository):
    """Non-persistent repository used for tests and offline mode."""

    def __init__(self) -> None:
        self._items: dict[str, Investment] = {}

    def list(self) -> list[Investment]:
        return [copy.deepcopy(i) for i in self._items.values()]

    def get(self, investment_id: str) -> Investment:
        try:
            return copy.deepcopy(self._items[investment_id])
        except KeyError:
            raise NotFoundError(f"Investment {investment_id} not found") from None

    def save(self, investment: Investment) -> None:
        self._items[investment.id] = copy.deepcopy(investment)

    def delete(self, investment_id: str) -> None:
        if self._items.pop(investment_id, None) is None:
            raise NotFoundError(f"Investment {investment_id} not found")
