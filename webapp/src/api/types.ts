// Symfony controller responses; DBAL decimal columns may arrive as strings.
export type Money = number | string;
export type User = { id: string; email: string; locale: string };
export type SimulationParameters = {
  initialCapital: number;
  contribution: number;
  annualRate: number;
  horizonMonths: number;
  contributionFrequency: "monthly" | "quarterly" | "semiannual" | "annual";
  compoundingFrequency:
    | "daily"
    | "monthly"
    | "quarterly"
    | "semiannual"
    | "annual";
  contributionTiming: "beginning" | "end";
  inflation: number;
  ter: number;
  contributionIncrease: number;
  applyTaxes: boolean;
  withdrawalAmount: number;
  withdrawalFrequency: "monthly" | "quarterly" | "semiannual" | "annual";
  withdrawalStartMonth: number;
};
export type Projection = {
  parameters: SimulationParameters;
  summary: {
    finalCapital: number;
    finalCapitalNet: number;
    totalContributed: number;
  };
  yearly: { year: number; month: number; closing: number }[];
};
export type PerformanceComparison = {
  projection: Projection & { monthly?: { month: number; closing: number }[] };
  points: {
    date: string;
    monthsElapsed: number;
    projected: number;
    actual: number;
    contributedActual: number;
    deviation: number;
    deviationPct: number | null;
  }[];
  expectedRate: number;
  actualXirr: number | null;
  status: "No data yet" | "Ahead of plan" | "On track" | "Behind plan";
};
export type Investment = {
  // Collection aliases startDate, detail currently returns the raw start_date column.
  id: string;
  name: string;
  startDate?: string;
  start_date?: string;
  status: "active" | "closed";
  notes: string;
  parameters?: SimulationParameters;
  projection?: Projection;
  snapshots?: Snapshot[];
};
export type Snapshot = {
  id: string;
  date: string;
  marketValue: Money;
  contribution: Money;
  withdrawal: Money;
  note: string;
};
export type Category = {
  id: string;
  name: string;
  kind: "income" | "expense";
  archived: boolean | number;
};
export type BudgetLine = {
  id: string;
  categoryId: string;
  categoryName: string;
  kind: Category["kind"];
  amount: Money;
  notes: string;
};
export type Budget = {
  id: string;
  year: number;
  month: number;
  notes: string;
  version: number;
  lines: BudgetLine[];
};
export type Transaction = {
  id: string;
  date: string;
  kind: Category["kind"];
  categoryId: string;
  categoryName: string;
  amount: Money;
  description: string;
};
export type ReportTotals = {
  plannedIncome: number;
  actualIncome: number;
  plannedExpense: number;
  actualExpense: number;
  plannedNet: number;
  actualNet: number;
};
export type MonthlyReport = {
  year: number;
  month: number;
  budget: Budget | null;
  rows: {
    categoryId: string;
    name: string;
    kind: Category["kind"];
    planned: number;
    actual: number;
    variance: number;
    status: "on_budget" | "favourable" | "unfavourable";
  }[];
  totals: ReportTotals;
};
// Annual controller returns a category variance roll-up, twelve monthly reports and totals.
export type AnnualReport = {
  year: number;
  rows: MonthlyReport["rows"];
  months: MonthlyReport[];
  totals: ReportTotals;
};
