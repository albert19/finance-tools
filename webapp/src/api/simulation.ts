import type { Parameters } from "../domain/simulation/engine";
import type { SimulationParameters } from "./types";

// The local legacy engine uses fractions; the API accepts percentage points.
export function toApiParameters(p: Parameters): SimulationParameters {
  return {
    initialCapital: p.initial_capital,
    contribution: p.contribution,
    annualRate: p.annual_rate * 100,
    horizonMonths: p.horizon_months,
    contributionFrequency: p.contribution_frequency,
    compoundingFrequency: p.compounding_frequency,
    contributionTiming: p.contribution_timing,
    inflation: p.inflation * 100,
    ter: p.ter * 100,
    contributionIncrease: p.contribution_increase * 100,
    applyTaxes: p.apply_taxes,
    withdrawalAmount: p.withdrawal?.amount ?? 0,
    withdrawalFrequency: p.withdrawal?.frequency ?? "monthly",
    withdrawalStartMonth: p.withdrawal?.start_month ?? 0,
  };
}
