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
import { BudgetPage } from "./Budget";
import i18n from "../i18n";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return { ...original, request };
});
const totals = (n: number) => ({
  plannedIncome: n * 100,
  actualIncome: n * 110,
  plannedExpense: n * 40,
  actualExpense: n * 50,
  plannedNet: n * 60,
  actualNet: n * 60,
});
const now = new Date(),
  year = now.getFullYear(),
  month = now.getMonth() + 1;
function mount() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <BudgetPage />
    </QueryClientProvider>,
  );
}
afterEach(async () => {
  cleanup();
  request.mockReset();
  await i18n.changeLanguage("en");
});

describe("budget parity", () => {
  it("renders monthly and annual comparison charts, twelve months and annual API category roll-up", async () => {
    request.mockImplementation(async (path: string) => {
      if (path === "/categories") return [];
      if (path === `/budgets/${year}/${month}`)
        return { id: "current", version: 1, lines: [], notes: "" };
      if (path.startsWith("/reports/monthly/"))
        return { totals: totals(1), rows: [] };
      if (path.startsWith("/reports/annual/"))
        return {
          totals: totals(78),
          months: Array.from({ length: 12 }, (_, i) => ({
            month: i + 1,
            totals: totals(i + 1),
          })),
          rows: [
            {
              categoryId: "food",
              name: "Food",
              kind: "expense",
              planned: 480,
              actual: 600,
              variance: 120,
              status: "unfavourable",
            },
          ],
        };
      return [];
    });
    mount();
    expect(
      await screen.findByRole("img", { name: "Monthly planned vs actual" }),
    ).toBeTruthy();
    fireEvent.click(screen.getByText(`Annual overview — ${year}`));
    expect(
      await screen.findByRole("img", {
        name: "Annual planned vs actual by month",
      }),
    ).toBeTruthy();
    const table = screen.getByRole("table", {
      name: "12-month income, expenses and balance",
    });
    expect(within(table).getAllByRole("row")).toHaveLength(14); // header + 12 months + total
    expect(within(table).getByText("€7,800.00")).toBeTruthy();
    expect(
      within(
        screen.getByRole("table", { name: "Annual category variance" }),
      ).getByText("Food"),
    ).toBeTruthy();
  });

  it("copies a chosen period across years and archives or restores a category", async () => {
    request.mockImplementation(async (path: string, init?: RequestInit) => {
      if (init) return null;
      if (path === "/categories")
        return [{ id: "food", name: "Food", kind: "expense", archived: 0 }];
      if (path === `/budgets/${year}/${month}`) return null;
      if (path === "/budgets")
        return [{ id: "old", year: year - 2, month: 6, lines: [] }];
      if (path.startsWith("/reports/"))
        return { totals: totals(0), rows: [], months: [] };
      return [];
    });
    mount();
    const source = await screen.findByRole("combobox", {
      name: "Copy from plan",
    });
    await screen.findByRole("option", { name: new RegExp(String(year - 2)) });
    fireEvent.change(source, { target: { value: `${year - 2}-6` } });
    fireEvent.click(screen.getByRole("button", { name: "Copy selected plan" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/budgets",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            year,
            month,
            copyFrom: { year: year - 2, month: 6 },
          }),
        }),
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "Archive Food" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/categories/food",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ archived: true }),
        }),
      ),
    );
    request.mockImplementation(async (path: string, init?: RequestInit) => {
      if (init) return null;
      if (path === "/categories")
        return [{ id: "food", name: "Food", kind: "expense", archived: 1 }];
      if (path === `/budgets/${year}/${month}`) return null;
      if (path === "/budgets") return [];
      if (path.startsWith("/reports/"))
        return { totals: totals(0), rows: [], months: [] };
    });
    // The query was invalidated by the archive action; explicitly refetch with a fresh mount.
    cleanup();
    mount();
    fireEvent.click(
      await screen.findByRole("button", { name: "Unarchive Food" }),
    );
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/categories/food",
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ archived: false }),
        }),
      ),
    );
  });

  it("localizes the new controls in Spanish", async () => {
    await i18n.changeLanguage("es");
    request.mockImplementation(async (path: string) => {
      if (path === "/categories")
        return [{ id: "food", name: "Comida", kind: "expense", archived: 1 }];
      if (path === `/budgets/${year}/${month}`) return null;
      if (path === "/budgets") return [];
      if (path.startsWith("/reports/"))
        return { totals: totals(0), rows: [], months: [] };
    });
    mount();
    expect(
      await screen.findByRole("combobox", { name: "Copiar del plan" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Desarchivar Comida" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("img", { name: "Previsto y real del mes" }),
    ).toBeTruthy();
  });
});
