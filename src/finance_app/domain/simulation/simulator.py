from __future__ import annotations

from finance_app.domain.simulation.result import (
    PeriodRow,
    SimulationResult,
    Summary,
    aggregate_years,
)
from finance_app.domain.simulation.returns import CashFlow, irr
from finance_app.domain.simulation.tax_policy import NoTaxPolicy, TaxPolicy
from finance_app.domain.simulation.value_objects import ContributionTiming, SimulationParameters

_DEPLETED = 0.005


class CompoundInterestSimulator:
    """Domain service that projects an investment month by month.

    Monthly stepping (instead of the closed formula) lets us combine
    contribution timing, growing contributions, fees, withdrawals and taxes.
    Any compounding frequency is converted to its exact equivalent monthly rate.
    """

    def __init__(self, tax_policy: TaxPolicy | None = None) -> None:
        self._tax_policy: TaxPolicy = tax_policy or NoTaxPolicy()

    @property
    def tax_policy(self) -> TaxPolicy:
        return self._tax_policy

    @staticmethod
    def monthly_growth_rate(params: SimulationParameters) -> float:
        n = params.compounding_frequency.periods_per_year
        return float((1 + params.annual_rate.fraction / n) ** (n / 12) - 1)

    def run(self, params: SimulationParameters) -> SimulationResult:
        tax: TaxPolicy = self._tax_policy if params.apply_taxes else NoTaxPolicy()
        growth = self.monthly_growth_rate(params)
        fee_rate = 1 - (1 + params.ter.fraction) ** (-1 / 12)
        inflation = params.inflation.fraction
        contribution_step = params.contribution_frequency.months_per_period
        beginning = params.contribution_timing is ContributionTiming.BEGINNING
        plan = params.withdrawal
        total_months = params.horizon.months

        balance = basis = params.initial_capital.to_float()
        contributed, withdrawn, fees_total, taxes_total = balance, 0.0, 0.0, 0.0
        year_gain = 0.0
        depletion_month: int | None = None
        gross_flows: list[CashFlow] = [(0.0, -balance)]
        net_flows: list[CashFlow] = [(0.0, -balance)]
        rows: list[PeriodRow] = []

        for month in range(1, total_months + 1):
            index = month - 1
            opening = balance
            in_withdrawal = plan is not None and month > plan.start_month
            due = index % contribution_step == (0 if beginning else contribution_step - 1)
            amount = 0.0
            if due and not in_withdrawal and depletion_month is None:
                increase = (1 + params.contribution_increase.fraction) ** (index // 12)
                amount = params.contribution.to_float() * increase

            if beginning and amount:
                balance += amount
                basis += amount
                gross_flows.append((index / 12, -amount))
                net_flows.append((index / 12, -amount))

            interest = balance * growth
            fees = (balance + interest) * fee_rate
            balance += interest - fees

            if not beginning and amount:
                balance += amount
                basis += amount
                gross_flows.append((month / 12, -amount))
                net_flows.append((month / 12, -amount))

            withdrawal = 0.0
            if (
                plan is not None
                and in_withdrawal
                and depletion_month is None
                and (month - plan.start_month) % plan.frequency.months_per_period == 0
            ):
                withdrawal = min(plan.amount.to_float(), max(balance, 0.0))
                if balance > 0:
                    basis_share = basis * withdrawal / balance
                    year_gain += withdrawal - basis_share
                    basis -= basis_share
                balance -= withdrawal
                withdrawn += withdrawal
                gross_flows.append((month / 12, withdrawal))
                net_flows.append((month / 12, withdrawal))
                if balance < _DEPLETED:
                    balance, basis, depletion_month = 0.0, 0.0, month

            taxes = 0.0
            if month % 12 == 0 or month == total_months:
                taxes = tax.tax_for(year_gain)
                if taxes:
                    net_flows.append((month / 12, -taxes))
                taxes_total += taxes
                if month != total_months:
                    year_gain = 0.0

            contributed += amount
            fees_total += fees
            rows.append(
                PeriodRow(
                    index=month,
                    opening=opening,
                    contribution=amount,
                    interest=interest,
                    fees=fees,
                    withdrawal=withdrawal,
                    taxes=taxes,
                    closing=balance,
                    cost_basis=basis,
                    real_closing=balance / (1 + inflation) ** (month / 12),
                )
            )

        unrealized = balance - basis
        final_tax = tax.tax_for(year_gain + unrealized) - tax.tax_for(year_gain)
        final_net = balance - final_tax
        horizon_years = total_months / 12
        deflator = (1 + inflation) ** horizon_years
        gross_flows.append((horizon_years, balance))
        net_flows.append((horizon_years, final_net))
        interest_earned = balance + withdrawn - contributed

        summary = Summary(
            final_capital=balance,
            final_capital_net=final_net,
            total_contributed=contributed,
            total_withdrawn=withdrawn,
            interest_earned=interest_earned,
            total_fees=fees_total,
            total_taxes=taxes_total + final_tax,
            final_tax=final_tax,
            real_final_capital=balance / deflator,
            real_final_capital_net=final_net / deflator,
            total_return=interest_earned / contributed if contributed else 0.0,
            irr=irr(gross_flows),
            irr_net=irr(net_flows),
            depletion_month=depletion_month,
        )
        monthly = tuple(rows)
        return SimulationResult(params, monthly, aggregate_years(monthly), summary)
