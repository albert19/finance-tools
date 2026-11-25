import { describe, expect, it } from "vitest";
import { defaults } from "../domain/simulation/engine";
import { toApiParameters } from "./simulation";

describe("simulation API parameters", () => {
  it("converts fractions into percentage points and uses camelCase", () => {
    const result = toApiParameters({
      ...defaults,
      annual_rate: 0.0625,
      inflation: 0.02,
      ter: 0.003,
      contribution_increase: 0.05,
      horizon_months: 48,
    });
    expect(result).toMatchObject({
      annualRate: 6.25,
      inflation: 2,
      ter: 0.3,
      contributionIncrease: 5,
      horizonMonths: 48,
    });
    expect(result).not.toHaveProperty("annual_rate");
    expect(result).toMatchObject({
      withdrawalAmount: 0,
      withdrawalFrequency: "monthly",
      withdrawalStartMonth: 0,
    });
    expect(
      toApiParameters({
        ...defaults,
        withdrawal: { amount: 750, frequency: "quarterly", start_month: 18 },
      }),
    ).toMatchObject({
      withdrawalAmount: 750,
      withdrawalFrequency: "quarterly",
      withdrawalStartMonth: 18,
    });
  });
});
