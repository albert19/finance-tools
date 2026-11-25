import { afterEach, describe, expect, it } from "vitest";
import { defaults } from "../domain/simulation/engine";
import { loadSimulationDefaults, saveSimulationDefaults } from "./settings";

afterEach(() => window.localStorage.clear());

describe("simulation defaults", () => {
  it("keeps one account's financial inputs out of another account's projections", () => {
    saveSimulationDefaults("alice", { ...defaults, initial_capital: 67890 });
    expect(loadSimulationDefaults("alice").initial_capital).toBe(67890);
    expect(loadSimulationDefaults("bob").initial_capital).toBe(
      defaults.initial_capital,
    );
  });
});
