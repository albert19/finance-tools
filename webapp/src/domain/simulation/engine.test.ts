import { describe, expect, it } from "vitest";
import { defaults, irr, simulate } from "./engine";
describe("browser projection", () => {
  it("compounds monthly and contributes at the end of a month", () => {
    const result = simulate({
      ...defaults,
      initial_capital: 1000,
      contribution: 100,
      horizon_months: 12,
      annual_rate: 0.12,
      inflation: 0,
      ter: 0,
      apply_taxes: false,
    });
    const monthly = 1 + 0.12 / 12 - 1;
    const expected =
      1000 * (1 + monthly) ** 12 + (100 * ((1 + monthly) ** 12 - 1)) / monthly;
    expect(result.summary.final_capital).toBeCloseTo(expected, 6);
    expect(result.yearly[0].contribution).toBe(1200);
    expect(result.summary.final_capital_net).toBe(result.summary.final_capital);
  });
  it("applies withdrawal tax to realised gains and estimates final capital gains", () => {
    const result = simulate({
      ...defaults,
      initial_capital: 10000,
      contribution: 0,
      horizon_months: 24,
      annual_rate: 0.12,
      withdrawal: { amount: 100, frequency: "monthly", start_month: 12 },
    });
    expect(result.summary.total_withdrawn).toBe(1200);
    expect(result.summary.total_taxes).toBeGreaterThan(0);
    expect(result.summary.final_capital_net).toBeLessThan(
      result.summary.final_capital,
    );
  });
  it("aggregates partial final years and prevents invalid inputs", () => {
    expect(simulate({ ...defaults, horizon_months: 13 }).yearly).toHaveLength(
      2,
    );
    expect(() => simulate({ ...defaults, horizon_months: 0 })).toThrow(
      RangeError,
    );
    expect(() => simulate({ ...defaults, initial_capital: NaN })).toThrow(
      RangeError,
    );
    expect(
      irr([
        [0, -100],
        [1, 110],
      ]),
    ).toBeCloseTo(0.1, 9);
  });
  it("compares scenario returns monotonically", () => {
    const low = simulate({ ...defaults, annual_rate: 0.04 }).summary
      .final_capital;
    const base = simulate(defaults).summary.final_capital;
    const high = simulate({ ...defaults, annual_rate: 0.08 }).summary
      .final_capital;
    expect(low).toBeLessThan(base);
    expect(base).toBeLessThan(high);
  });
});
