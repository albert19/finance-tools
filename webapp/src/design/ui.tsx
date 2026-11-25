import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { money } from "../i18n";
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export function Message({
  children,
  retry,
}: {
  children: ReactNode;
  retry?: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="message" role="alert">
      {children}
      {retry && (
        <button type="button" onClick={retry}>
          {t("retry")}
        </button>
      )}
    </div>
  );
}
export function Figure({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "green" | "red";
}) {
  return (
    <div className={`figure ${tone || ""}`}>
      <span>{label}</span>
      <strong>{money(value)}</strong>
    </div>
  );
}
export function Sparkline({
  values,
  label,
  observations = [],
}: {
  values: number[];
  label: string;
  observations?: { x: number; value: number }[];
}) {
  if (values.length < 2) return null;
  const min = Math.min(0, ...values, ...observations.map((p) => p.value)),
    max = Math.max(...values, ...observations.map((p) => p.value)),
    range = max - min || 1;
  const points = values
    .map(
      (v, i) =>
        `${((i / (values.length - 1)) * 100).toFixed(2)},${(100 - ((v - min) / range) * 88 - 6).toFixed(2)}`,
    )
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
        points={points}
        fill="none"
        stroke="var(--blue)"
        strokeWidth="1.4"
        vectorEffect="non-scaling-stroke"
      />
      {observations.map((p, i) => (
        <circle
          key={i}
          cx={Math.max(0, Math.min(100, p.x * 100))}
          cy={100 - ((p.value - min) / range) * 88 - 6}
          r="1.4"
          fill="var(--green)"
          stroke="var(--paper)"
          strokeWidth=".5"
        >
          <title>{money(p.value)}</title>
        </circle>
      ))}
    </svg>
  );
}
export function Period({
  year,
  month,
  setYear,
  setMonth,
}: {
  year: number;
  month?: number;
  setYear: (v: number) => void;
  setMonth?: (v: number) => void;
}) {
  const { t, i18n } = useTranslation();
  return (
    <div className="period">
      {month !== undefined && setMonth && (
        <Field label={t("month")}>
          <select
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
          >
            {Array.from({ length: 12 }, (_, i) => (
              <option value={i + 1} key={i}>
                {new Intl.DateTimeFormat(i18n.language, {
                  month: "long",
                }).format(new Date(2024, i, 1))}
              </option>
            ))}
          </select>
        </Field>
      )}
      <Field label={t("year")}>
        <input
          type="number"
          min="2000"
          max="2100"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
        />
      </Field>
    </div>
  );
}
