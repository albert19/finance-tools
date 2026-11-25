export type Frequency =
  | "daily"
  | "monthly"
  | "quarterly"
  | "semiannual"
  | "annual";
export type Parameters = {
  initial_capital: number;
  contribution: number;
  contribution_frequency: Exclude<Frequency, "daily">;
  annual_rate: number;
  compounding_frequency: Frequency;
  horizon_months: number;
  contribution_timing: "beginning" | "end";
  inflation: number;
  ter: number;
  contribution_increase: number;
  apply_taxes: boolean;
  withdrawal?: {
    amount: number;
    frequency: Exclude<Frequency, "daily">;
    start_month: number;
  } | null;
};
export type Row = {
  index: number;
  opening: number;
  contribution: number;
  interest: number;
  fees: number;
  withdrawal: number;
  taxes: number;
  closing: number;
  cost_basis: number;
  real_closing: number;
};
export type Summary = {
  final_capital: number;
  final_capital_net: number;
  total_contributed: number;
  total_withdrawn: number;
  interest_earned: number;
  total_fees: number;
  total_taxes: number;
  final_tax: number;
  real_final_capital: number;
  real_final_capital_net: number;
  total_return: number;
  irr: number | null;
  irr_net: number | null;
  depletion_month: number | null;
};
export type Result = {
  parameters: Parameters;
  monthly: Row[];
  yearly: Row[];
  summary: Summary;
};
const periods: Record<Frequency, number> = {
  daily: 365,
  monthly: 12,
  quarterly: 4,
  semiannual: 2,
  annual: 1,
};
const tax = (gain: number) => {
  if (gain <= 0) return 0;
  let result = 0;
  let lower = 0;
  for (const [upper, rate] of [
    [6000, 0.19],
    [50000, 0.21],
    [200000, 0.23],
    [300000, 0.27],
    [Infinity, 0.3],
  ]) {
    result += Math.max(0, Math.min(gain, upper) - lower) * rate;
    lower = upper;
  }
  return result;
};
export function irr(flows: [number, number][]): number | null {
  const entries = flows.filter(([, amount]) => amount !== 0);
  if (!entries.some(([, a]) => a < 0) || !entries.some(([, a]) => a > 0))
    return null;
  const npv = (rate: number) =>
    entries.reduce((v, [t, a]) => v + a / (1 + rate) ** t, 0);
  const slope = (rate: number) =>
    entries.reduce((v, [t, a]) => v - (t * a) / (1 + rate) ** (t + 1), 0);
  let rate = 0.05;
  for (let i = 0; i < 50; i++) {
    const value = npv(rate);
    const derivative = slope(rate);
    if (
      !Number.isFinite(value) ||
      !Number.isFinite(derivative) ||
      derivative === 0
    )
      break;
    const next = rate - value / derivative;
    if (next <= -0.99) break;
    if (Math.abs(next - rate) < 1e-10) return next;
    rate = next;
  }
  const grid = [-0.99, -0.5, -0.2, 0, 0.1, 0.3, 1, 5, 100];
  for (let i = 1; i < grid.length; i++) {
    let lo = grid[i - 1],
      hi = grid[i],
      flo = npv(lo);
    const fhi = npv(hi);
    if (flo === 0) return lo;
    if (flo > 0 === fhi > 0) continue;
    for (let j = 0; j < 200; j++) {
      const mid = (lo + hi) / 2,
        value = npv(mid);
      if (Math.abs(value) < 1e-9 || hi - lo < 1e-12) return mid;
      if (value > 0 === flo > 0) {
        lo = mid;
        flo = value;
      } else hi = mid;
    }
    return (lo + hi) / 2;
  }
  return null;
}
export function simulate(p: Parameters): Result {
  if (
    ![
      p.initial_capital,
      p.contribution,
      p.annual_rate,
      p.inflation,
      p.ter,
      p.contribution_increase,
      p.withdrawal?.amount ?? 0,
      p.withdrawal?.start_month ?? 0,
    ].every(Number.isFinite) ||
    !Number.isInteger(p.horizon_months) ||
    p.horizon_months < 1 ||
    p.horizon_months > 1200 ||
    p.initial_capital < 0 ||
    p.contribution < 0 ||
    p.initial_capital + p.contribution === 0 ||
    p.annual_rate < -0.5 ||
    p.annual_rate > 1 ||
    p.inflation < 0 ||
    p.inflation > 0.5 ||
    p.ter < 0 ||
    p.ter > 0.1 ||
    p.contribution_increase < 0 ||
    p.contribution_increase > 0.5 ||
    (p.withdrawal &&
      (p.withdrawal.amount <= 0 ||
        p.withdrawal.start_month < 0 ||
        p.withdrawal.start_month >= p.horizon_months))
  )
    throw new RangeError("Invalid simulation parameters");
  const growth =
    (1 + p.annual_rate / periods[p.compounding_frequency]) **
      (periods[p.compounding_frequency] / 12) -
    1;
  const feeRate = 1 - (1 + p.ter) ** (-1 / 12);
  const step = 12 / periods[p.contribution_frequency];
  const beginning = p.contribution_timing === "beginning";
  let balance = p.initial_capital,
    basis = balance,
    contributed = balance,
    withdrawn = 0,
    feesTotal = 0,
    taxesTotal = 0,
    yearGain = 0;
  let depletionMonth: number | null = null;
  const gross: [number, number][] = [[0, -balance]],
    net: [number, number][] = [[0, -balance]];
  const monthly: Row[] = [];
  for (let month = 1; month <= p.horizon_months; month++) {
    const index = month - 1,
      opening = balance;
    const inWithdrawal = !!p.withdrawal && month > p.withdrawal.start_month;
    const due = index % step === (beginning ? 0 : step - 1);
    const amount =
      due && !inWithdrawal && depletionMonth === null
        ? p.contribution *
          (1 + p.contribution_increase) ** Math.floor(index / 12)
        : 0;
    if (beginning && amount) {
      balance += amount;
      basis += amount;
      gross.push([index / 12, -amount]);
      net.push([index / 12, -amount]);
    }
    const interest = balance * growth;
    const fees = (balance + interest) * feeRate;
    balance += interest - fees;
    if (!beginning && amount) {
      balance += amount;
      basis += amount;
      gross.push([month / 12, -amount]);
      net.push([month / 12, -amount]);
    }
    let withdrawal = 0;
    if (
      p.withdrawal &&
      inWithdrawal &&
      depletionMonth === null &&
      (month - p.withdrawal.start_month) %
        (12 / periods[p.withdrawal.frequency]) ===
        0
    ) {
      withdrawal = Math.min(p.withdrawal.amount, Math.max(balance, 0));
      if (balance > 0) {
        const share = (basis * withdrawal) / balance;
        yearGain += withdrawal - share;
        basis -= share;
      }
      balance -= withdrawal;
      withdrawn += withdrawal;
      gross.push([month / 12, withdrawal]);
      net.push([month / 12, withdrawal]);
      if (balance < 0.005) {
        balance = 0;
        basis = 0;
        depletionMonth = month;
      }
    }
    let taxes = 0;
    if (month % 12 === 0 || month === p.horizon_months) {
      taxes = p.apply_taxes ? tax(yearGain) : 0;
      if (taxes) net.push([month / 12, -taxes]);
      taxesTotal += taxes;
      if (month !== p.horizon_months) yearGain = 0;
    }
    contributed += amount;
    feesTotal += fees;
    monthly.push({
      index: month,
      opening,
      contribution: amount,
      interest,
      fees,
      withdrawal,
      taxes,
      closing: balance,
      cost_basis: basis,
      real_closing: balance / (1 + p.inflation) ** (month / 12),
    });
  }
  const finalTax = p.apply_taxes
    ? tax(yearGain + balance - basis) - tax(yearGain)
    : 0;
  const finalNet = balance - finalTax,
    years = p.horizon_months / 12,
    deflator = (1 + p.inflation) ** years;
  gross.push([years, balance]);
  net.push([years, finalNet]);
  const interestEarned = balance + withdrawn - contributed;
  const yearly: Row[] = [];
  for (let start = 0; start < monthly.length; start += 12) {
    const chunk = monthly.slice(start, start + 12),
      last = chunk[chunk.length - 1];
    yearly.push({
      ...last,
      index: start / 12 + 1,
      opening: chunk[0].opening,
      contribution: chunk.reduce((v, r) => v + r.contribution, 0),
      interest: chunk.reduce((v, r) => v + r.interest, 0),
      fees: chunk.reduce((v, r) => v + r.fees, 0),
      withdrawal: chunk.reduce((v, r) => v + r.withdrawal, 0),
      taxes: chunk.reduce((v, r) => v + r.taxes, 0),
    });
  }
  return {
    parameters: p,
    monthly,
    yearly,
    summary: {
      final_capital: balance,
      final_capital_net: finalNet,
      total_contributed: contributed,
      total_withdrawn: withdrawn,
      interest_earned: interestEarned,
      total_fees: feesTotal,
      total_taxes: taxesTotal + finalTax,
      final_tax: finalTax,
      real_final_capital: balance / deflator,
      real_final_capital_net: finalNet / deflator,
      total_return: contributed ? interestEarned / contributed : 0,
      irr: irr(gross),
      irr_net: irr(net),
      depletion_month: depletionMonth,
    },
  };
}
export const defaults: Parameters = {
  initial_capital: 10000,
  contribution: 250,
  contribution_frequency: "monthly",
  annual_rate: 0.06,
  compounding_frequency: "monthly",
  horizon_months: 240,
  contribution_timing: "end",
  inflation: 0.02,
  ter: 0.002,
  contribution_increase: 0,
  apply_taxes: true,
};
