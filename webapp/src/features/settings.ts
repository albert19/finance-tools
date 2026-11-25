import { defaults, type Parameters } from "../domain/simulation/engine";

const key = (userId: string) => `finance-simulation-defaults:${userId}`;
export function loadSimulationDefaults(userId: string): Parameters {
  try {
    const saved = window.localStorage?.getItem(key(userId));
    return saved
      ? { ...defaults, ...(JSON.parse(saved) as Partial<Parameters>) }
      : defaults;
  } catch {
    return defaults;
  }
}
export function saveSimulationDefaults(userId: string, value: Parameters) {
  window.localStorage?.setItem(key(userId), JSON.stringify(value));
}
