import { afterEach, describe, expect, it, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { Transactions } from "./Transactions";
import { BudgetPage } from "./Budget";
import { Portfolio } from "./Portfolio";
import "../i18n";

const { request } = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return { ...original, request };
});
const category = { id: "food", name: "Food", kind: "expense", archived: false };
const total = {
  plannedIncome: 0,
  actualIncome: 0,
  plannedExpense: 20,
  actualExpense: 12,
  plannedNet: -20,
  actualNet: -12,
};
function mount(element: React.ReactNode) {
  return render(
    <MemoryRouter>
      <QueryClientProvider
        client={
          new QueryClient({
            defaultOptions: { queries: { retry: false } },
          })
        }
      >
        {element}
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
afterEach(() => {
  cleanup();
  request.mockReset();
  vi.unstubAllGlobals();
});

describe("controller-backed feature requests", () => {
  it("posts a transaction with category-derived kind and description, not note", async () => {
    request.mockImplementation(async (path: string) =>
      path === "/categories" ? [category] : [],
    );
    mount(<Transactions />);
    fireEvent.click(screen.getByRole("button", { name: "Add transaction" }));
    await screen.findByRole("option", { name: "Food" });
    fireEvent.change(screen.getByRole("combobox", { name: "Category" }), {
      target: { value: "food" },
    });
    fireEvent.change(screen.getByRole("spinbutton", { name: "Value" }), {
      target: { value: "12.50" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: "Description" }), {
      target: { value: "Lunch" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/transactions",
        expect.objectContaining({
          method: "POST",
          body: expect.any(String),
        }),
      ),
    );
    const post = request.mock.calls.find(([path]) => path === "/transactions")!;
    expect(JSON.parse(post[1].body)).toEqual(
      expect.objectContaining({
        categoryId: "food",
        amount: 12.5,
        description: "Lunch",
      }),
    );
    expect(JSON.parse(post[1].body)).not.toHaveProperty("kind");
  });

  it("uses report rows/totals and sends the current version in a line DELETE body", async () => {
    const now = new Date(),
      year = now.getFullYear(),
      month = now.getMonth() + 1;
    request.mockImplementation(async (path: string) => {
      if (path === "/categories") return [category];
      if (path === `/budgets/${year}/${month}`)
        return {
          id: "budget1",
          year,
          month,
          version: 3,
          notes: "",
          lines: [
            {
              id: "line1",
              categoryId: "food",
              categoryName: "Food",
              kind: "expense",
              amount: "20.00",
              notes: "Lunches",
            },
          ],
        };
      if (path.startsWith("/reports/monthly/"))
        return {
          totals: total,
          rows: [
            {
              categoryId: "food",
              name: "Food",
              kind: "expense",
              planned: 20,
              actual: 12,
              variance: 8,
              status: "favourable",
            },
          ],
        };
      if (path.startsWith("/reports/annual/"))
        return { totals: total, months: [] };
      return null;
    });
    vi.stubGlobal("confirm", () => true);
    mount(<BudgetPage />);
    expect(await screen.findByText("Lunches")).toBeTruthy();
    expect(screen.getByText("✓ Favourable")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: "Delete" })[0]);
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith("/budgets/budget1/lines/line1", {
        method: "DELETE",
        body: JSON.stringify({ version: 3 }),
      }),
    );
  });

  it("renders server projection and posts a marketValue snapshot", async () => {
    request.mockImplementation(async (path: string) => {
      if (path === "/investments")
        return [
          {
            id: "inv1",
            name: "Savings",
            startDate: "2025-01-01",
            status: "active",
            notes: "",
          },
        ];
      if (path === "/investments/inv1")
        return {
          id: "inv1",
          name: "Savings",
          start_date: "2025-01-01",
          status: "active",
          notes: "",
          snapshots: [],
          projection: {
            parameters: { initialCapital: 100, horizonMonths: 12 },
            summary: { finalCapital: 130 },
            yearly: [{ year: 1, month: 12, closing: 130 }],
          },
        };
      return { id: "snapshot1" };
    });
    mount(<Portfolio />);
    expect(await screen.findByText("Recorded balances")).toBeTruthy();
    fireEvent.change(screen.getByRole("spinbutton", { name: "Value" }), {
      target: { value: "120" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record a balance" }));
    await waitFor(() =>
      expect(request).toHaveBeenCalledWith(
        "/investments/inv1/snapshots",
        expect.objectContaining({
          method: "POST",
          body: expect.any(String),
        }),
      ),
    );
    const post = request.mock.calls.find(
      ([path]) => path === "/investments/inv1/snapshots",
    )!;
    expect(JSON.parse(post[1].body)).toMatchObject({
      marketValue: 120,
      note: "",
    });
    expect(JSON.parse(post[1].body)).not.toHaveProperty("value");
  });
});
