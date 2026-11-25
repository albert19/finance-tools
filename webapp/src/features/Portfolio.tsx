import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { request, json } from "../api/client";
import {
  type Investment,
  type PerformanceComparison,
  type Snapshot,
} from "../api/types";
import { Field, Message } from "../design/ui";
import { money } from "../i18n";

function ComparisonChart({
  comparison,
  label,
}: {
  comparison: PerformanceComparison;
  label: string;
}) {
  const { projection, points } = comparison;
  const horizon = Math.max(1, projection.parameters.horizonMonths);
  const projected = [
    { month: 0, closing: projection.parameters.initialCapital },
    ...(projection.monthly?.length ? projection.monthly : projection.yearly),
  ];
  if (projected.length < 2) return null;
  const balances = [
    ...projected.map((p) => p.closing),
    ...points.map((p) => p.actual),
  ];
  const min = Math.min(0, ...balances),
    range = Math.max(...balances) - min || 1;
  const x = (month: number) =>
    Math.max(0, Math.min(100, (month / horizon) * 100));
  const y = (value: number) => 94 - ((value - min) / range) * 88;
  const line = (series: { month: number; closing: number }[]) =>
    series
      .map((p) => `${x(p.month).toFixed(2)},${y(p.closing).toFixed(2)}`)
      .join(" ");
  return (
    <svg
      className="chart"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      <line
        x1="0"
        x2="100"
        y1="94"
        y2="94"
        stroke="var(--silver)"
        strokeWidth=".3"
      />
      <polyline
        points={line(projected)}
        fill="none"
        stroke="var(--blue)"
        strokeWidth="1.4"
        vectorEffect="non-scaling-stroke"
      />
      {points.length > 1 && (
        <polyline
          points={line(
            points.map((p) => ({ month: p.monthsElapsed, closing: p.actual })),
          )}
          fill="none"
          stroke="var(--green)"
          strokeWidth="1.4"
          vectorEffect="non-scaling-stroke"
        />
      )}
      {points.map((p) => (
        <circle
          key={p.date}
          cx={x(p.monthsElapsed)}
          cy={y(p.actual)}
          r="1.4"
          fill="var(--green)"
          stroke="var(--paper)"
          strokeWidth=".5"
        >
          <title>{`${p.date}: ${money(p.actual)}`}</title>
        </circle>
      ))}
    </svg>
  );
}

export function Portfolio() {
  const { t, i18n } = useTranslation(),
    cache = useQueryClient();
  const list = useQuery({
    queryKey: ["investments"],
    queryFn: () => request<Investment[]>("/investments"),
  });
  const [selected, setSelected] = useState<string | null>(null),
    [editing, setEditing] = useState(false);
  const [name, setName] = useState(""),
    [date, setDate] = useState(() => {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    });
  const [value, setValue] = useState(""),
    [note, setNote] = useState(""),
    [error, setError] = useState("");
  const entries = list.data ?? [];
  const id =
    selected && entries.some((v) => v.id === selected)
      ? selected
      : entries[0]?.id;
  const detail = useQuery({
    queryKey: ["investment", id],
    enabled: !!id,
    queryFn: () => request<Investment>(`/investments/${id}`),
  });
  const comparison = useQuery({
    queryKey: ["investment-comparison", id],
    enabled: !!id,
    queryFn: () =>
      request<PerformanceComparison>(`/investments/${id}/comparison`),
  });
  const investment = detail.data ?? entries.find((v) => v.id === id);
  const projection = detail.data?.projection;
  const latest = comparison.data?.points?.at(-1);
  const percent = (value: number) =>
    new Intl.NumberFormat(i18n.language === "es" ? "es-ES" : "en-IE", {
      style: "percent",
      maximumFractionDigits: 2,
      signDisplay: "exceptZero",
    }).format(value);
  const statusKey = {
    "No data yet": "comparisonNoData",
    "Ahead of plan": "comparisonAhead",
    "On track": "comparisonOnTrack",
    "Behind plan": "comparisonBehind",
  } as const;
  const update = useMutation({
    mutationFn: ({ path, init }: { path: string; init: RequestInit }) =>
      request(path, init),
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["investments"] });
      void cache.invalidateQueries({ queryKey: ["investment", id] });
      void cache.invalidateQueries({ queryKey: ["investment-comparison"] });
      setError("");
    },
    onError: () => setError(t("requestError")),
  });
  function snapshot(e: FormEvent) {
    e.preventDefault();
    if (
      !id ||
      !value.trim() ||
      !Number.isFinite(Number(value)) ||
      Number(value) < 0
    ) {
      setError(t("validation"));
      return;
    }
    void update
      .mutateAsync({
        path: `/investments/${id}/snapshots`,
        init: json("POST", { date, marketValue: Number(value), note }),
      })
      .then(() => {
        setValue("");
        setNote("");
      })
      .catch(() => {
        /* error displayed by mutation */
      });
  }
  return (
    <main>
      <div className="page-heading">
        <div>
          <h1>{t("portfolio")}</h1>
          <p>{t("portfolioHint")}</p>
        </div>
        <Link className="outlined" to="/simulator">
          {t("saveInvestment")}
        </Link>
      </div>
      {list.isPending ? (
        <p role="status">{t("loading")}</p>
      ) : list.isError ? (
        <Message retry={() => void list.refetch()}>{t("loadError")}</Message>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          {t("noInvestments")} <Link to="/simulator">{t("simulator")}</Link>
        </div>
      ) : (
        <div className="portfolio-layout">
          <aside className="investment-list" aria-label={t("portfolio")}>
            {entries.map((v) => (
              <button
                key={v.id}
                type="button"
                aria-current={id === v.id ? "true" : undefined}
                onClick={() => {
                  setSelected(v.id);
                  setEditing(false);
                }}
              >
                {v.name}
                <span>↗</span>
              </button>
            ))}
          </aside>
          <section className="investment-detail">
            {detail.isError && (
              <Message retry={() => void detail.refetch()}>
                {t("loadError")}
              </Message>
            )}
            {investment && (
              <>
                {editing ? (
                  <form
                    className="inline-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      update.mutate({
                        path: `/investments/${id}`,
                        init: json("PATCH", { name }),
                      });
                      setEditing(false);
                    }}
                  >
                    <Field label={t("investmentName")}>
                      <input
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                      />
                    </Field>
                    <button className="primary">{t("save")}</button>
                    <button type="button" onClick={() => setEditing(false)}>
                      {t("cancel")}
                    </button>
                  </form>
                ) : (
                  <div className="section-heading">
                    <h2>{investment.name}</h2>
                    <div>
                      <button
                        className="text-button"
                        onClick={() => {
                          setName(investment.name);
                          setEditing(true);
                        }}
                      >
                        {t("edit")}
                      </button>
                      <button
                        className="text-button destructive"
                        onClick={() => {
                          if (confirm(t("confirmDelete"))) {
                            update.mutate({
                              path: `/investments/${id}`,
                              init: { method: "DELETE" },
                            });
                            setSelected(null);
                          }
                        }}
                      >
                        {t("delete")}
                      </button>
                    </div>
                  </div>
                )}
                {projection && (
                  <div className="portfolio-projection">
                    <span>{t("projected")}</span>
                    <strong>{money(projection.summary.finalCapital)}</strong>
                  </div>
                )}
                {comparison.isPending ? (
                  <p role="status">{t("loadingComparison")}</p>
                ) : comparison.isError ? (
                  <Message retry={() => void comparison.refetch()}>
                    {t("comparisonError")}
                  </Message>
                ) : (
                  comparison.data?.points &&
                  comparison.data.projection && (
                    <section
                      className="portfolio-comparison"
                      aria-label={t("performanceComparison")}
                    >
                      <h3>{t("performanceComparison")}</h3>
                      <p className="comparison-status">
                        {t("status")}:{" "}
                        <strong>{t(statusKey[comparison.data.status])}</strong>
                      </p>
                      {latest ? (
                        <div className="comparison-metrics">
                          <div>
                            <span>
                              {t("actualAtDate", { date: latest.date })}
                            </span>
                            <strong>{money(latest.actual)}</strong>
                          </div>
                          <div>
                            <span>
                              {t("projectedAtDate", { date: latest.date })}
                            </span>
                            <strong>{money(latest.projected)}</strong>
                          </div>
                          <div>
                            <span>{t("deviation")}</span>
                            <strong
                              className={
                                latest.deviation > 0
                                  ? "positive"
                                  : latest.deviation < 0
                                    ? "negative"
                                    : ""
                              }
                            >
                              {latest.deviationPct === null
                                ? t("notAvailable")
                                : percent(latest.deviationPct)}
                            </strong>
                          </div>
                        </div>
                      ) : (
                        <p>{t("comparisonEmpty")}</p>
                      )}
                      <div className="comparison-rates">
                        <span>
                          {t("actualXirr")}:{" "}
                          <strong>
                            {comparison.data.actualXirr === null
                              ? t("notAvailable")
                              : percent(comparison.data.actualXirr)}
                          </strong>
                        </span>
                        <span>
                          {t("expectedRate")}:{" "}
                          <strong>
                            {percent(comparison.data.expectedRate)}
                          </strong>
                        </span>
                      </div>
                      <ComparisonChart
                        comparison={comparison.data}
                        label={t("comparisonChart")}
                      />
                      <div className="chart-key">
                        <span>{t("projection")}</span>
                        <span>{t("actual")}</span>
                      </div>
                      {comparison.data.points.length > 0 && (
                        <details className="comparison-history">
                          <summary>{t("comparisonHistory")}</summary>
                          <div className="table-scroll">
                            <table>
                              <thead>
                                <tr>
                                  <th>{t("date")}</th>
                                  <th>{t("projection")}</th>
                                  <th>{t("actual")}</th>
                                  <th>{t("deviation")}</th>
                                </tr>
                              </thead>
                              <tbody>
                                {comparison.data.points.map((p) => (
                                  <tr key={p.date}>
                                    <td>{p.date}</td>
                                    <td>{money(p.projected)}</td>
                                    <td>{money(p.actual)}</td>
                                    <td>
                                      {p.deviationPct === null
                                        ? t("notAvailable")
                                        : percent(p.deviationPct)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </details>
                      )}
                    </section>
                  )
                )}
                <h3>{t("snapshots")}</h3>
                {!investment.snapshots?.length && <p>{t("empty")}</p>}
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>{t("date")}</th>
                        <th>{t("value")}</th>
                        <th>{t("note")}</th>
                        <th>
                          <span className="sr-only">{t("delete")}</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {investment.snapshots?.map((s: Snapshot) => (
                        <tr key={s.id}>
                          <td>{s.date}</td>
                          <td>{money(Number(s.marketValue))}</td>
                          <td>{s.note}</td>
                          <td>
                            <button
                              className="text-button destructive"
                              onClick={() => {
                                if (confirm(t("confirmDelete")))
                                  update.mutate({
                                    path: `/investments/${id}/snapshots/${s.id}`,
                                    init: { method: "DELETE" },
                                  });
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
                <form className="inline-form" onSubmit={snapshot}>
                  <h3>{t("addSnapshot")}</h3>
                  <Field label={t("date")}>
                    <input
                      type="date"
                      required
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                    />
                  </Field>
                  <Field label={t("value")}>
                    <input
                      type="number"
                      min="0"
                      step=".01"
                      required
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                    />
                  </Field>
                  <Field label={t("note")}>
                    <input
                      value={note}
                      onChange={(e) => setNote(e.target.value)}
                    />
                  </Field>
                  <button className="primary" disabled={update.isPending}>
                    {t("addSnapshot")}
                  </button>
                </form>
              </>
            )}
          </section>
        </div>
      )}
      {error && <Message>{error}</Message>}
    </main>
  );
}
