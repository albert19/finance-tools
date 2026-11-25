import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Sparkline } from "./ui";
import "../i18n";
describe("projection chart", () => {
  it("has a descriptive accessible name", () => {
    render(
      <Sparkline values={[100, 120, 160]} label="Projected balance by year" />,
    );
    expect(
      screen.getByRole("img", { name: "Projected balance by year" }),
    ).toBeTruthy();
  });
});
