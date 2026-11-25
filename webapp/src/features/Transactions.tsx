import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { z } from "zod";
import { request, json } from "../api/client";
import { type Category, type Transaction } from "../api/types";
import { Field, Figure, Message, Period } from "../design/ui";
import { money } from "../i18n";
const today = () => {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};
const transactionSchema = z.object({
  date: z.iso.date(),
  categoryId: z.string().min(1),
  amount: z.coerce.number().positive().finite(),
  description: z.string().max(255),
});
export function Transactions() {
  const { t } = useTranslation(),
    cache = useQueryClient(),
    now = new Date();
  const [year, setYear] = useState(now.getFullYear()),
    [month, setMonth] = useState(now.getMonth() + 1);
  const [filter, setFilter] = useState("all"),
    [editing, setEditing] = useState<string | null>(null),
    [open, setOpen] = useState(false),
    [error, setError] = useState("");
  const [form, setForm] = useState({
    date: today(),
    kind: "expense" as "income" | "expense",
    categoryId: "",
    amount: "",
    description: "",
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => request<Category[]>("/categories"),
  });
  const transactions = useQuery({
    queryKey: ["transactions", year, month, filter],
    queryFn: () =>
      request<Transaction[]>(
        `/transactions?year=${year}&month=${month}${filter !== "all" ? `&kind=${filter}` : ""}`,
      ),
  });
  const rows = transactions.data ?? [],
    cats = categories.data ?? [];
  const total = (kind: string) =>
    rows
      .filter((v) => v.kind === kind)
      .reduce((sum, v) => sum + Number(v.amount), 0);
  function start(value?: Transaction) {
    setEditing(value?.id ?? null);
    setForm(
      value
        ? {
            date: value.date.slice(0, 10),
            kind: value.kind,
            categoryId: value.categoryId,
            amount: String(value.amount),
            description: value.description || "",
          }
        : {
            date: today(),
            kind: "expense",
            categoryId: "",
            amount: "",
            description: "",
          },
    );
    setOpen(true);
    setError("");
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    const parsed = transactionSchema.safeParse(form);
    if (
      !parsed.success ||
      cats.find((c) => c.id === parsed.data.categoryId)?.kind !== form.kind
    ) {
      setError(t("validation"));
      return;
    }
    try {
      await request(
        editing ? `/transactions/${editing}` : "/transactions",
        json(editing ? "PUT" : "POST", parsed.data),
      );
      setOpen(false);
      setError("");
      await cache.invalidateQueries({ queryKey: ["transactions"] });
    } catch {
      setError(t("requestError"));
    }
  }
  async function remove(id: string) {
    if (!confirm(t("confirmDelete"))) return;
    try {
      await request(`/transactions/${id}`, { method: "DELETE" });
      await cache.invalidateQueries({ queryKey: ["transactions"] });
    } catch {
      setError(t("requestError"));
    }
  }
  return (
    <main>
      <div className="page-heading">
        <div>
          <h1>{t("transactions")}</h1>
          <p>{t("tagline")}</p>
        </div>
        <button className="primary" onClick={() => start()}>
          {t("addTransaction")}
        </button>
      </div>
      <div className="toolbar">
        <Period
          year={year}
          month={month}
          setYear={setYear}
          setMonth={setMonth}
        />
        <Field label={t("type")}>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">{t("all")}</option>
            <option value="income">{t("income")}</option>
            <option value="expense">{t("expense")}</option>
          </select>
        </Field>
      </div>
      {open && (
        <form className="editor" onSubmit={(e) => void submit(e)}>
          <h2>{editing ? t("edit") : t("addTransaction")}</h2>
          <div className="form-grid">
            <Field label={t("date")}>
              <input
                type="date"
                required
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
              />
            </Field>
            <Field label={t("type")}>
              <select
                value={form.kind}
                onChange={(e) =>
                  setForm({
                    ...form,
                    kind: e.target.value as "income" | "expense",
                    categoryId: "",
                  })
                }
              >
                <option value="expense">{t("expense")}</option>
                <option value="income">{t("income")}</option>
              </select>
            </Field>
            <Field label={t("category")}>
              <select
                required
                value={form.categoryId}
                onChange={(e) =>
                  setForm({ ...form, categoryId: e.target.value })
                }
              >
                <option value="">{t("category")}</option>
                {cats
                  .filter((c) => c.kind === form.kind && !c.archived)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label={t("value")}>
              <input
                type="number"
                min=".01"
                step=".01"
                required
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
              />
            </Field>
            <Field label={t("description")}>
              <input
                maxLength={255}
                value={form.description}
                onChange={(e) =>
                  setForm({ ...form, description: e.target.value })
                }
              />
            </Field>
          </div>
          <div className="actions">
            <button className="primary">{t("save")}</button>
            <button type="button" onClick={() => setOpen(false)}>
              {t("cancel")}
            </button>
          </div>
        </form>
      )}
      {error && <Message>{error}</Message>}
      {transactions.isPending ? (
        <p role="status">{t("loading")}</p>
      ) : transactions.isError ? (
        <Message retry={() => void transactions.refetch()}>
          {t("loadError")}
        </Message>
      ) : (
        <>
          <div className="figures">
            <Figure
              label={t("totalIncome")}
              value={total("income")}
              tone="green"
            />
            <Figure
              label={t("totalExpenses")}
              value={total("expense")}
              tone="red"
            />
            <Figure
              label={t("balance")}
              value={total("income") - total("expense")}
            />
          </div>
          {rows.length === 0 ? (
            <div className="empty-state">{t("noTransactions")}</div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t("date")}</th>
                    <th>{t("category")}</th>
                    <th>{t("description")}</th>
                    <th>{t("value")}</th>
                    <th>
                      <span className="sr-only">{t("edit")}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((v) => (
                    <tr key={v.id}>
                      <td>{v.date.slice(0, 10)}</td>
                      <td>{v.categoryName}</td>
                      <td>{v.description}</td>
                      <td
                        className={
                          v.kind === "income" ? "positive" : "negative"
                        }
                      >
                        {v.kind === "income" ? "+" : "−"}
                        {money(Number(v.amount))}
                      </td>
                      <td className="row-actions">
                        <button
                          className="text-button"
                          onClick={() => start(v)}
                        >
                          {t("edit")}
                        </button>
                        <button
                          className="text-button destructive"
                          onClick={() => void remove(v.id)}
                        >
                          {t("delete")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </main>
  );
}
