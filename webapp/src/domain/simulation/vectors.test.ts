import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { simulate, type Parameters } from "./engine";
const path = resolve(
  process.cwd(),
  "../contracts/simulation-vectors/legacy-python.json",
);
type Vector = {
  name: string;
  input: Record<string, number | string | boolean>;
  expected: {
    summary: Record<string, number | null>;
    monthly: Record<string, number>[];
    yearly: Record<string, number>[];
  };
};
describe("shared Python golden vectors", () => {
  const vectors = JSON.parse(readFileSync(path, "utf8")) as Vector[];
  it("includes all five shared cases", () => expect(vectors).toHaveLength(5));
  for (const vector of vectors)
    it(vector.name, () => {
      const v = vector.input;
      const input: Parameters = {
        initial_capital: Number(v.initial_capital),
        contribution: Number(v.contribution),
        contribution_frequency:
          v.contribution_frequency as Parameters["contribution_frequency"],
        annual_rate: Number(v.annual_rate_pct) / 100,
        compounding_frequency:
          v.compounding_frequency as Parameters["compounding_frequency"],
        horizon_months: Number(v.horizon_months),
        contribution_timing:
          v.contribution_timing as Parameters["contribution_timing"],
        inflation: Number(v.inflation_pct) / 100,
        ter: Number(v.ter_pct) / 100,
        contribution_increase: Number(v.contribution_increase_pct) / 100,
        apply_taxes: Boolean(v.apply_taxes),
        withdrawal:
          Number(v.withdrawal_amount) > 0
            ? {
                amount: Number(v.withdrawal_amount),
                frequency: v.withdrawal_frequency as "monthly",
                start_month: Number(v.withdrawal_start_month),
              }
            : null,
      };
      const actual = simulate(input);
      for (const [key, expected] of Object.entries(vector.expected.summary)) {
        const value = key.endsWith("_pct")
          ? (actual.summary[
              key.slice(0, -4) as keyof typeof actual.summary
            ] as number) * 100
          : actual.summary[key as keyof typeof actual.summary];
        if (expected === null) expect(value, key).toBeNull();
        else
          expect(Math.abs((value as number) - expected), key).toBeLessThan(
            key.includes("irr") || key.includes("return") ? 1e-7 : 1e-6,
          );
      }
      for (const kind of ["monthly", "yearly"] as const) {
        expect(actual[kind]).toHaveLength(vector.expected[kind].length);
        for (const [index, row] of vector.expected[kind].entries()) {
          for (const [key, expected] of Object.entries(row)) {
            if (key === "gains") continue;
            expect(
              Math.abs(
                actual[kind][index][
                  key as keyof (typeof actual.monthly)[number]
                ] - expected,
              ),
              `${kind} ${index} ${key}`,
            ).toBeLessThan(1e-6);
          }
        }
      }
    });
});
