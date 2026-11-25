import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Portfolio } from "./Portfolio";
import i18n from "../i18n";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return { ...original, request };
});
const investments = ["first", "second"].map((id) => ({
  id,
  name: id,
  status: "active",
  notes: "",
}));
const projection = {
  parameters: { initialCapital: 100, horizonMonths: 12 },
  summary: { finalCapital: 130 },
  monthly: [
    { month: 6, closing: 110 },
    { month: 12, closing: 130 },
  ],
  yearly: [{ year: 1, month: 12, closing: 130 }],
};
const point = {
  date: "2025-07-01",
  monthsElapsed: 6,
  projected: 110,
  actual: 120,
  contributedActual: 100,
  deviation: 10,
  deviationPct: 10 / 110,
};
const earlier = {
  ...point,
  date: "2025-04-01",
  monthsElapsed: 3,
  projected: 105,
  actual: 107,
  deviation: 2,
  deviationPct: 2 / 105,
};
function mount() {
  return render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false } },
          })
        }
      >
        <Portfolio />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
afterEach(async () => {
  cleanup();
  request.mockReset();
  vi.unstubAllGlobals();
  await i18n.changeLanguage("en");
});

describe("portfolio comparison", () => {
  it("shows server comparison points, latest metrics, XIRR and localized status; refetches after a snapshot and on selection change", async () => {
    let snapshots = 0;
    request.mockImplementation(async (path: string, init?: RequestInit) => {
      if (init) {
        snapshots++;
        return null;
      }
      if (path === "/investments") return investments;
      if (path.endsWith("/comparison"))
        return path.includes("second")
          ? {
              projection,
              points: [],
              expectedRate: 0.04,
              actualXirr: null,
              status: "No data yet",
            }
          : {
              projection,
              points: [
                earlier,
                snapshots
                  ? {
                      ...point,
                      actual: 125,
                      deviation: 15,
                      deviationPct: 15 / 110,
                    }
                  : point,
              ],
              expectedRate: 0.04,
              actualXirr: 0.075,
              status: "Ahead of plan",
            };
      if (path.startsWith("/investments/"))
        return { ...investments[0], projection, snapshots: [] };
      return null;
    });
    mount();
    const section = await screen.findByRole("region", {
      name: "Performance against plan",
    });
    expect(within(section).getAllByText("€120.00")).toHaveLength(2);
    expect(within(section).getAllByText("€110.00")).toHaveLength(2);
    expect(within(section).getAllByText("+9.09%")).toHaveLength(2);
    expect(within(section).getByText("+7.5%")).toBeTruthy();
    expect(within(section).getByText("+4%")).toBeTruthy();
    expect(within(section).getByText("Ahead of plan")).toBeTruthy();
    const chart = within(section).getByRole("img", {
      name: "Projected balance and actual recorded balances over time",
    });
    expect(chart.querySelectorAll("polyline")).toHaveLength(2);
    fireEvent.change(screen.getByRole("spinbutton", { name: "Value" }), {
      target: { value: "125" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record a balance" }));
    await waitFor(() =>
      expect(within(section).getAllByText("€125.00")).toHaveLength(2),
    );
    expect(
      request.mock.calls.filter(
        ([path]) => path === "/investments/first/comparison",
      ),
    ).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: /second/ }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith("/investments/second/comparison"),
    );
    expect(
      await screen.findByText(
        "Record a balance to compare your progress with the plan.",
      ),
    ).toBeTruthy();
    expect(screen.getByText("No data yet")).toBeTruthy();
    expect(
      within(
        screen.getByRole("region", { name: "Performance against plan" }),
      ).getByText("Not available yet"),
    ).toBeTruthy();
  });

  it("offers retry when comparison request fails and translates results to Spanish", async () => {
    await i18n.changeLanguage("es");
    let attempts = 0;
    request.mockImplementation(async (path: string) => {
      if (path === "/investments") return [investments[0]];
      if (path.endsWith("/comparison")) {
        if (++attempts === 1) throw new Error("network");
        return {
          projection,
          points: [point],
          expectedRate: 0.04,
          actualXirr: null,
          status: "Behind plan",
        };
      }
      return { ...investments[0], projection, snapshots: [] };
    });
    mount();
    expect((await screen.findByRole("alert")).textContent).toContain(
      "No se pudo cargar la comparación de resultados.",
    );
    fireEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Por debajo del plan")).toBeTruthy();
    expect(
      screen.getByRole("img", {
        name: "Saldo previsto y saldos reales registrados a lo largo del tiempo",
      }),
    ).toBeTruthy();
    expect(
      screen.getByText("Rentabilidad anualizada real (TIR):"),
    ).toBeTruthy();
  });
});
