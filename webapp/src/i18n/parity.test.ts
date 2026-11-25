import { describe, expect, it } from "vitest";
import en from "./en.json";
import es from "./es.json";
describe("translations", () => {
  it("has matching keys and placeholders", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(es).sort());
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      const placeholders = (value: string) =>
        [...value.matchAll(/\{\{\s*(\w+)\s*\}\}/g)]
          .map((match) => match[1])
          .sort();
      expect(placeholders(en[key]), key).toEqual(placeholders(es[key]));
    }
  });
});
