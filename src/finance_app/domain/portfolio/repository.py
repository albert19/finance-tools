from __future__ import annotations

from abc import ABC, abstractmethod

from finance_app.domain.portfolio.investment import Investment


class InvestmentRepository(ABC):
    """Persistence port for the Investment aggregate (snapshots included)."""

    @abstractmethod
    def list(self) -> list[Investment]: ...

    @abstractmethod
    def get(self, investment_id: str) -> Investment:
        """Return the investment or raise ``NotFoundError``."""

    @abstractmethod
    def save(self, investment: Investment) -> None:
        """Insert or update the aggregate, including its snapshots."""

    @abstractmethod
    def delete(self, investment_id: str) -> None:
        """Delete the aggregate or raise ``NotFoundError``."""
