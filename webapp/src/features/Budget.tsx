import { useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { request, json, ApiError } from "../api/client";
import {
  type Budget,
  type BudgetLine,
  type Category,
  type MonthlyReport,
  type AnnualReport,
} from "../api/types";
import { Field, Figure, Message, Period } from "../design/ui";
import { money } from "../i18n";

type Comparison = {
  plannedIncome: number;
  actualIncome: number;
  plannedExpense: number;
  actualExpense: number;
  plannedNet: number;
  actualNet: number;
};
const metrics = ["Income", "Expense", "Net"] as const;
function totalsWithNet(
  totals: AnnualReport["totals"] | MonthlyReport["totals"],
): Comparison {
  return {
    plannedIncome: Number(totals.plannedIncome),
    actualIncome: Number(totals.actualIncome),
    plannedExpense: Number(totals.plannedExpense),
    actualExpense: Number(totals.actualExpense),
    plannedNet: Number(totals.plannedIncome) - Number(totals.plannedExpense),
    actualNet: Number(totals.actualIncome) - Number(totals.actualExpense),
  };
}
function ComparisonChart({
  periods,
  labels,
  title,
}: {
  periods: Comparison[];
  labels: string[];
  title: string;
}) {
  const { t } = useTranslation();
  const width = 720,
    band = 104,
    top = 25,
    half = 34;
  return (
    <figure className="budget-chart">
      <figcaption>{title}</figcaption>
      <div className="budget-chart-key">
        <span className="budget-key-planned">{t("planned")}</span>
        <span className="budget-key-actual">{t("actual")}</span>
      </div>
      <svg
        viewBox={`0 0 ${width} ${band * 3}`}
        role="img"
        aria-label={title}
        preserveAspectRatio="xMidYMid meet"
      >
        {metrics.map((metric, index) => {
          const plannedKey = `planned${metric}` as keyof Comparison,
            actualKey = `actual${metric}` as keyof Comparison;
          const scale = Math.max(
            1,
            ...periods.flatMap((p) => [
              Math.abs(p[plannedKey]),
              Math.abs(p[actualKey]),
            ]),
          );
          const baseline = index * band + top + half;
          return (
            <g key={metric}>
              <text x="4" y={index * band + 16} className="budget-chart-label">
                {t(
                  metric === "Income"
                    ? "totalIncome"
                    : metric === "Expense"
                      ? "totalExpenses"
                      : "balance",
                )}
              </text>
              <line
                x1="110"
                x2="710"
                y1={baseline}
                y2={baseline}
                className="budget-chart-axis"
              />
              {periods.map((p, i) => {
                const x = 110 + ((i + 0.5) * 600) / periods.length;
                return (
                  <g key={i}>
                    {([plannedKey, actualKey] as const).map((key, j) => {
                      const value = p[key],
                        height = (Math.abs(value) / scale) * half;
                      return (
                        <rect
                          key={key}
                          x={x + (j ? 1 : -12)}
                          y={value >= 0 ? baseline - height : baseline}
                          width="11"
                          height={height}
                          className={
                            j ? "budget-bar-actual" : "budget-bar-planned"
                          }
                        >
                          <title>{`${labels[i]} · ${t(metric === "Income" ? "totalIncome" : metric === "Expense" ? "totalExpenses" : "balance")} · ${t(j ? "actual" : "planned")}: ${money(value)}`}</title>
                        </rect>
                      );
                    })}
                    <text
                      x={x}
                      y={index * band + 101}
                      textAnchor="middle"
                      className="budget-chart-month"
                    >
                      {labels[i]}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
export function BudgetPage() {
  const { t, i18n } = useTranslation(),
    cache = useQueryClient(),
    now = new Date();
  const [year, setYear] = useState(now.getFullYear()),
    [month, setMonth] = useState(now.getMonth() + 1),
    [error, setError] = useState("");
  const [categoryName, setCategoryName] = useState(""),
    [categoryKind, setCategoryKind] = useState<"income" | "expense">("expense");
  const [lineCategory, setLineCategory] = useState(""),
    [lineAmount, setLineAmount] = useState(""),
    [lineNote, setLineNote] = useState("");
  const [editingCategory, setEditingCategory] = useState<string | null>(null),
    [lineEditing, setLineEditing] = useState<string | null>(null);
  const [notes, setNotes] = useState(""),
    [notesEditing, setNotesEditing] = useState(false);
  const [copySource, setCopySource] = useState("");
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => request<Category[]>("/categories"),
  });
  const budget = useQuery({
    queryKey: ["budget", year, month],
    queryFn: async () => {
      try {
        return await request<Budget>(`/budgets/${year}/${month}`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
  const monthly = useQuery({
    queryKey: ["report-monthly", year, month],
    queryFn: () => request<MonthlyReport>(`/reports/monthly/${year}/${month}`),
  });
  const annual = useQuery({
    queryKey: ["report-annual", year],
    queryFn: () => request<AnnualReport>(`/reports/annual/${year}`),
  });
  const sources = useQuery({
    queryKey: ["budget-sources"],
    queryFn: () => request<Budget[]>("/budgets"),
    enabled: budget.data === null,
  });
  const cats = categories.data ?? [],
    lines = budget.data?.lines ?? [];
  const availableSources = (sources.data ?? []).filter(
    (b) => Number(b.year) !== year || Number(b.month) !== month,
  );
  const selectedSource = availableSources.find(
    (b) => `${b.year}-${b.month}` === copySource,
  );
  const monthLabel = (m: number) =>
    new Intl.DateTimeFormat(i18n.language, { month: "short" }).format(
      new Date(2024, m - 1, 1),
    );
  async function mutate(path: string, init: RequestInit) {
    setError("");
    try {
      await request(path, init);
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["budget"] }),
        cache.invalidateQueries({ queryKey: ["budget-sources"] }),
        cache.invalidateQueries({ queryKey: ["categories"] }),
        cache.invalidateQueries({ queryKey: ["report-monthly"] }),
        cache.invalidateQueries({ queryKey: ["report-annual"] }),
      ]);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        await cache.invalidateQueries({ queryKey: ["budget"] });
        setError(t("budgetConflict"));
      } else setError(t("requestError"));
    }
  }
  function create(copy: boolean) {
    if (copy && !selectedSource) return;
    void mutate(
      "/budgets",
      json("POST", {
        year,
        month,
        ...(copy
          ? {
              copyFrom: {
                year: Number(selectedSource!.year),
                month: Number(selectedSource!.month),
              },
            }
          : {}),
      }),
    );
  }
  function submitCategory(e: FormEvent) {
    e.preventDefault();
    if (!categoryName.trim()) return;
    void mutate(
      editingCategory ? `/categories/${editingCategory}` : "/categories",
      json(
        editingCategory ? "PATCH" : "POST",
        editingCategory
          ? { name: categoryName.trim() }
          : { name: categoryName.trim(), kind: categoryKind },
      ),
    );
    setEditingCategory(null);
    setCategoryName("");
  }
  function submitLine(e: FormEvent) {
    e.preventDefault();
    if (
      !budget.data ||
      !lineCategory ||
      !lineAmount.trim() ||
      Number(lineAmount) < 0 ||
      !Number.isFinite(Number(lineAmount))
    ) {
      setError(t("validation"));
      return;
    }
    void mutate(
      lineEditing
        ? `/budgets/${budget.data.id}/lines/${lineEditing}`
        : `/budgets/${budget.data.id}/lines`,
      json(lineEditing ? "PUT" : "POST", {
        categoryId: lineCategory,
        amount: Number(lineAmount),
        notes: lineNote,
        version: budget.data.version,
      }),
    );
    setLineEditing(null);
    setLineCategory("");
    setLineAmount("");
    setLineNote("");
  }
  function editLine(line: BudgetLine) {
    setLineEditing(line.id);
    setLineCategory(line.categoryId);
    setLineAmount(String(line.amount));
    setLineNote(line.notes || "");
  }
  return (
    <main>
      <div className="page-heading">
        <div>
          <h1>{t("budget")}</h1>
          <p>{t("tagline")}</p>
        </div>
        <Period
          year={year}
          month={month}
          setYear={setYear}
          setMonth={setMonth}
        />
      </div>
      {error && <Message>{error}</Message>}
      <div className="figures">
        <Figure
          label={t("totalIncome")}
          value={Number(monthly.data?.totals.actualIncome || 0)}
          tone="green"
        />
        <Figure
          label={t("totalExpenses")}
          value={Number(monthly.data?.totals.actualExpense || 0)}
          tone="red"
        />
        <Figure
          label={t("balance")}
          value={Number(monthly.data?.totals.actualNet || 0)}
        />
      </div>
      {monthly.data && (
        <ComparisonChart
          title={t("monthlyComparison")}
          periods={[totalsWithNet(monthly.data.totals)]}
          labels={[monthLabel(month)]}
        />
      )}
      <div className="budget-layout">
        <section className="ledger">
          <div className="section-heading">
            <h2>{t("plan")}</h2>
          </div>
          {budget.isPending ? (
            <p role="status">{t("loading")}</p>
          ) : budget.isError ? (
            <Message retry={() => void budget.refetch()}>
              {t("loadError")}
            </Message>
          ) : !budget.data ? (
            <div className="empty-state">
              <p>{t("noBudget")}</p>
              <div className="actions">
                <button className="primary" onClick={() => create(false)}>
                  {t("createPlan")}
                </button>
                <Field label={t("copySource")}>
                  <select
                    value={copySource}
                    onChange={(e) => setCopySource(e.target.value)}
                    disabled={!availableSources.length}
                  >
                    <option value="">{t("selectBudget")}</option>
                    {availableSources.map((b) => (
                      <option key={b.id} value={`${b.year}-${b.month}`}>
                        {monthLabel(Number(b.month))} {b.year}
                      </option>
                    ))}
                  </select>
                </Field>
                <button disabled={!selectedSource} onClick={() => create(true)}>
                  {t("copyFrom")}
                </button>
              </div>
              {sources.isPending && <p role="status">{t("loading")}</p>}
              {sources.isError && (
                <Message retry={() => void sources.refetch()}>
                  {t("loadError")}
                </Message>
              )}
              {sources.isSuccess && !availableSources.length && (
                <p>{t("noCopySources")}</p>
              )}
            </div>
          ) : (
            <>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>{t("category")}</th>
                      <th>{t("planned")}</th>
                      <th>{t("note")}</th>
                      <th>
                        <span className="sr-only">{t("edit")}</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {lines.map((l) => (
                      <tr key={l.id}>
                        <td>{l.categoryName}</td>
                        <td>{money(Number(l.amount))}</td>
                        <td>{l.notes}</td>
                        <td className="row-actions">
                          <button
                            className="text-button"
                            onClick={() => editLine(l)}
                          >
                            {t("edit")}
                          </button>
                          <button
                            className="text-button destructive"
                            onClick={() => {
                              if (confirm(t("confirmDelete")))
                                void mutate(
                                  `/budgets/${budget.data!.id}/lines/${l.id}`,
                                  json("DELETE", {
                                    version: budget.data!.version,
                                  }),
                                );
                            }}
                          >
                            {t("delete")}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <form className="inline-form" onSubmit={submitLine}>
                <h3>{lineEditing ? t("edit") : t("addLine")}</h3>
                <Field label={t("category")}>
                  <select
                    required
                    value={lineCategory}
                    onChange={(e) => setLineCategory(e.target.value)}
                  >
                    <option value="">{t("category")}</option>
                    {cats
                      .filter((c) => !c.archived)
                      .map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name} ({t(c.kind)})
                        </option>
                      ))}
                  </select>
                </Field>
                <Field label={t("planned")}>
                  <input
                    type="number"
                    min="0"
                    step=".01"
                    required
                    value={lineAmount}
                    onChange={(e) => setLineAmount(e.target.value)}
                  />
                </Field>
                <Field label={t("note")}>
                  <input
                    value={lineNote}
                    onChange={(e) => setLineNote(e.target.value)}
                  />
                </Field>
                <button className="primary">
                  {lineEditing ? t("save") : t("addLine")}
                </button>
                {lineEditing && (
                  <button
                    type="button"
                    onClick={() => {
                      setLineEditing(null);
                      setLineAmount("");
                    }}
                  >
                    {t("cancel")}
                  </button>
                )}
              </form>
              <div className="notes">
                <h3>{t("note")}</h3>
                {notesEditing ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      void mutate(
                        `/budgets/${budget.data!.id}`,
                        json("PATCH", { notes, version: budget.data?.version }),
                      );
                      setNotesEditing(false);
                    }}
                  >
                    <textarea
                      aria-label={t("note")}
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                    />
                    <button className="primary">{t("save")}</button>
                    <button
                      type="button"
                      onClick={() => setNotesEditing(false)}
                    >
                      {t("cancel")}
                    </button>
                  </form>
                ) : (
                  <>
                    <p>{budget.data.notes || t("empty")}</p>
                    <button
                      className="text-button"
                      onClick={() => {
                        setNotes(budget.data?.notes || "");
                        setNotesEditing(true);
                      }}
                    >
                      {t("edit")}
                    </button>
                  </>
                )}
              </div>
              <button
                className="text-button destructive"
                onClick={() => {
                  if (confirm(t("confirmDelete")))
                    void mutate(`/budgets/${budget.data!.id}`, {
                      method: "DELETE",
                    });
                }}
              >
                {t("delete")} {t("plan")}
              </button>
            </>
          )}
          <h2>{t("difference")}</h2>
          {monthly.isError ? (
            <Message retry={() => void monthly.refetch()}>
              {t("loadError")}
            </Message>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    {[
                      "category",
                      "planned",
                      "actual",
                      "difference",
                      "status",
                    ].map((k) => (
                      <th key={k}>{t(k)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {monthly.data?.rows.map((line) => (
                    <tr key={line.categoryId}>
                      <td>{line.name}</td>
                      <td>{money(line.planned)}</td>
                      <td>{money(line.actual)}</td>
                      <td>{money(line.variance)}</td>
                      <td>
                        {t(
                          line.status === "favourable"
                            ? "favourable"
                            : line.status === "unfavourable"
                              ? "unfavourable"
                              : "onBudget",
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        <aside className="category-panel">
          <h2>{t("categories")}</h2>
          {categories.isError && (
            <Message retry={() => void categories.refetch()}>
              {t("loadError")}
            </Message>
          )}
          {cats.map((c) => (
            <div className="category-row" key={c.id}>
              <span>
                {c.name}{" "}
                <small>
                  {t(c.kind)}
                  {Boolean(c.archived) && ` · ${t("archived")}`}
                </small>
              </span>
              <div>
                <button
                  className="text-button"
                  onClick={() => {
                    setEditingCategory(c.id);
                    setCategoryName(c.name);
                  }}
                >
                  {t("edit")}
                </button>
                <button
                  className="text-button"
                  aria-label={`${t(c.archived ? "unarchive" : "archive")} ${c.name}`}
                  onClick={() =>
                    void mutate(
                      `/categories/${c.id}`,
                      json("PATCH", { archived: !c.archived }),
                    )
                  }
                >
                  {t(c.archived ? "unarchive" : "archive")}
                </button>
                <button
                  className="text-button destructive"
                  onClick={() => {
                    if (confirm(t("confirmDelete")))
                      void mutate(`/categories/${c.id}`, { method: "DELETE" });
                  }}
                >
                  {t("delete")}
                </button>
              </div>
            </div>
          ))}
          <form className="category-form" onSubmit={submitCategory}>
            <Field label={t("name")}>
              <input
                required
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
              />
            </Field>
            {!editingCategory && (
              <Field label={t("type")}>
                <select
                  value={categoryKind}
                  onChange={(e) =>
                    setCategoryKind(e.target.value as "income" | "expense")
                  }
                >
                  <option value="expense">{t("expense")}</option>
                  <option value="income">{t("income")}</option>
                </select>
              </Field>
            )}
            <div className="actions">
              <button className="primary">
                {editingCategory ? t("save") : t("addCategory")}
              </button>
              {editingCategory && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingCategory(null);
                    setCategoryName("");
                  }}
                >
                  {t("cancel")}
                </button>
              )}
            </div>
          </form>
          <button
            className="text-button"
            onClick={() =>
              void mutate("/categories/defaults", { method: "POST" })
            }
          >
            {t("defaults")}
          </button>
        </aside>
      </div>
      <details className="breakdown">
        <summary>
          {t("annualView")} — {year}
        </summary>
        {annual.isPending ? (
          <p role="status">{t("loading")}</p>
        ) : annual.isError ? (
          <Message retry={() => void annual.refetch()}>
            {t("loadError")}
          </Message>
        ) : (
          annual.data && (
            <>
              <div className="figures">
                <Figure
                  label={t("totalIncome")}
                  value={Number(annual.data.totals.actualIncome || 0)}
                  tone="green"
                />
                <Figure
                  label={t("totalExpenses")}
                  value={Number(annual.data.totals.actualExpense || 0)}
                  tone="red"
                />
                <Figure
                  label={t("balance")}
                  value={
                    Number(annual.data.totals.actualIncome || 0) -
                    Number(annual.data.totals.actualExpense || 0)
                  }
                />
              </div>
              <ComparisonChart
                title={t("annualComparison")}
                periods={annual.data.months.map((m) => totalsWithNet(m.totals))}
                labels={annual.data.months.map((m) => monthLabel(m.month))}
              />
              <div className="table-scroll">
                <table>
                  <caption>{t("annualMonthlyTable")}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t("month")}</th>
                      {metrics.flatMap((metric) =>
                        ["planned", "actual"].map((key) => (
                          <th scope="col" key={`${metric}-${key}`}>
                            {t(
                              metric === "Income"
                                ? "totalIncome"
                                : metric === "Expense"
                                  ? "totalExpenses"
                                  : "balance",
                            )}{" "}
                            · {t(key)}
                          </th>
                        )),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {annual.data.months.map((m) => {
                      const totals = totalsWithNet(m.totals);
                      return (
                        <tr key={m.month}>
                          <th scope="row">{monthLabel(m.month)}</th>
                          {metrics.flatMap((metric) => [
                            <td key={`${metric}-planned`}>
                              {money(totals[`planned${metric}`])}
                            </td>,
                            <td key={`${metric}-actual`}>
                              {money(totals[`actual${metric}`])}
                            </td>,
                          ])}
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr>
                      <th scope="row">{t("annualTotal")}</th>
                      {metrics.flatMap((metric) => {
                        const totals = totalsWithNet(annual.data!.totals);
                        return [
                          <td key={`${metric}-planned`}>
                            {money(totals[`planned${metric}`])}
                          </td>,
                          <td key={`${metric}-actual`}>
                            {money(totals[`actual${metric}`])}
                          </td>,
                        ];
                      })}
                    </tr>
                  </tfoot>
                </table>
              </div>
              <div className="table-scroll annual-variance">
                <table>
                  <caption>{t("annualCategoryVariance")}</caption>
                  <thead>
                    <tr>
                      {[
                        "category",
                        "type",
                        "planned",
                        "actual",
                        "difference",
                        "status",
                      ].map((k) => (
                        <th scope="col" key={k}>
                          {t(k)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(annual.data.rows ?? []).map((row) => (
                      <tr key={row.categoryId}>
                        <th scope="row">{row.name}</th>
                        <td>{t(row.kind)}</td>
                        <td>{money(row.planned)}</td>
                        <td>{money(row.actual)}</td>
                        <td>{money(row.variance)}</td>
                        <td>
                          {t(
                            row.status === "favourable"
                              ? "favourable"
                              : row.status === "unfavourable"
                                ? "unfavourable"
                                : "onBudget",
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )
        )}
      </details>
    </main>
  );
}
