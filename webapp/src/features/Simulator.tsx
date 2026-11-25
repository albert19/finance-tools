import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { request, json } from "../api/client";
import { useSession } from "../auth/Session";
import { toApiParameters } from "../api/simulation";
import {
  simulate,
  type Parameters,
  type Frequency,
} from "../domain/simulation/engine";
import { loadSimulationDefaults, saveSimulationDefaults } from "./settings";
import { Field, Figure, Message, Sparkline } from "../design/ui";
import { money, number } from "../i18n";
const cashFrequencies = [
  "monthly",
  "quarterly",
  "semiannual",
  "annual",
] as const;
const allFrequencies = ["daily", ...cashFrequencies] as const;
export function Simulator() {
  const { t } = useTranslation(),
    navigate = useNavigate(),
    { user } = useSession();
  const [p, setP] = useState<Parameters>(() =>
      loadSimulationDefaults(user!.id),
    ),
    [name, setName] = useState(""),
    [error, setError] = useState(""),
    [saved, setSaved] = useState(""),
    [saving, setSaving] = useState(false);
  const change = (key: keyof Parameters, value: unknown) => {
    setSaved("");
    setP((prev) => ({ ...prev, [key]: value }));
  };
  const result = useMemo(() => {
    try {
      return simulate(p);
    } catch {
      return null;
    }
  }, [p]);
  const scenarios = useMemo(
    () =>
      result &&
      [-0.02, 0, 0.02].map(
        (delta) =>
          simulate({
            ...p,
            annual_rate: Math.max(-0.5, Math.min(1, p.annual_rate + delta)),
          }).summary.final_capital_net,
      ),
    [p, result],
  );
  const numeric = (
    key: keyof Parameters,
    label: string,
    min: number,
    max: number,
    step: number,
    factor = 1,
  ) => (
    <Field label={label}>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={Number(p[key]) * factor}
        onChange={(e) => change(key, Number(e.target.value) / factor)}
      />
    </Field>
  );
  const options = (values: readonly Frequency[]) =>
    values.map((v) => (
      <option value={v} key={v}>
        {t(v)}
      </option>
    ));
  async function save(e: FormEvent) {
    e.preventDefault();
    if (!result || !name.trim() || (!p.initial_capital && !p.contribution)) {
      setError(t("validation"));
      return;
    }
    setSaving(true);
    setError("");
    try {
      const today = new Date();
      const startDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
      await request(
        "/investments",
        json("POST", {
          name: name.trim(),
          startDate,
          parameters: toApiParameters(p),
          notes: "",
        }),
      );
      navigate("/portfolio");
    } catch {
      setError(t("requestError"));
    } finally {
      setSaving(false);
    }
  }
  return (
    <main>
      <div className="page-heading">
        <div>
          <h1>{t("simulator")}</h1>
          <p>{t("serverNotice")}</p>
        </div>
        <span className="heading-seal" aria-hidden="true">
          €
        </span>
      </div>
      <div className="sim-layout">
        <section className="input-panel" aria-label={t("simulator")}>
          <h2>{t("plan")}</h2>
          <div className="form-grid">
            {numeric("initial_capital", t("initial"), 0, 100000000, 100)}
            {numeric("contribution", t("contribution"), 0, 10000000, 25)}
            <Field label={t("frequency")}>
              <select
                value={p.contribution_frequency}
                onChange={(e) =>
                  change("contribution_frequency", e.target.value)
                }
              >
                {options(cashFrequencies)}
              </select>
            </Field>
            {numeric("horizon_months", t("years"), 1 / 12, 100, 1, 1 / 12)}
            <Field label={`${t("return")} · ${number(p.annual_rate * 100)}%`}>
              <input
                type="range"
                min="-20"
                max="25"
                step=".1"
                value={p.annual_rate * 100}
                onChange={(e) =>
                  change("annual_rate", Number(e.target.value) / 100)
                }
              />
              <input
                type="number"
                min="-50"
                max="100"
                step=".1"
                value={Number((p.annual_rate * 100).toFixed(2))}
                onChange={(e) =>
                  change("annual_rate", Number(e.target.value) / 100)
                }
              />
            </Field>
            <Field label={t("compounding")}>
              <select
                value={p.compounding_frequency}
                onChange={(e) =>
                  change("compounding_frequency", e.target.value)
                }
              >
                {options(allFrequencies)}
              </select>
            </Field>
            {numeric("inflation", t("inflation") + " %", 0, 50, 0.1, 100)}
            {numeric("ter", t("fees") + " %", 0, 10, 0.1, 100)}
            {numeric(
              "contribution_increase",
              t("increase") + " %",
              0,
              50,
              0.1,
              100,
            )}
            <Field label={t("saveAsDefaults")}>
              <button
                type="button"
                onClick={() => {
                  saveSimulationDefaults(user!.id, p);
                  setSaved(t("settingsSaved"));
                }}
              >
                {t("saveDefaults")}
              </button>
            </Field>
            <Field label={t("timing")}>
              <select
                value={p.contribution_timing}
                onChange={(e) => change("contribution_timing", e.target.value)}
              >
                <option value="end">{t("end")}</option>
                <option value="beginning">{t("beginning")}</option>
              </select>
            </Field>
          </div>
          <label className="check">
            <input
              type="checkbox"
              checked={p.apply_taxes}
              onChange={(e) => change("apply_taxes", e.target.checked)}
            />
            {t("taxes")}
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={!!p.withdrawal}
              onChange={(e) =>
                change(
                  "withdrawal",
                  e.target.checked
                    ? {
                        amount: 500,
                        frequency: "monthly",
                        start_month: Math.max(
                          0,
                          Math.floor(p.horizon_months / 2),
                        ),
                      }
                    : null,
                )
              }
            />
            {t("withdrawal")}
          </label>
          {p.withdrawal && (
            <div className="form-grid">
              <Field label={t("withdrawalAmount")}>
                <input
                  type="number"
                  min=".01"
                  step=".01"
                  value={p.withdrawal.amount}
                  onChange={(e) =>
                    change("withdrawal", {
                      ...p.withdrawal,
                      amount: Number(e.target.value),
                    })
                  }
                />
              </Field>
              <Field label={t("withdrawalStart")}>
                <input
                  type="number"
                  min="0"
                  max={p.horizon_months - 1}
                  value={p.withdrawal.start_month}
                  onChange={(e) =>
                    change("withdrawal", {
                      ...p.withdrawal,
                      start_month: Number(e.target.value),
                    })
                  }
                />
              </Field>
              <Field label={t("frequency")}>
                <select
                  value={p.withdrawal.frequency}
                  onChange={(e) =>
                    change("withdrawal", {
                      ...p.withdrawal,
                      frequency: e.target.value,
                    })
                  }
                >
                  {options(cashFrequencies)}
                </select>
              </Field>
            </div>
          )}
        </section>
        <section className="result-panel" aria-live="polite">
          {result ? (
            <>
              <div className="banknote">
                <div className="banknote-top">
                  <span>✳ {t("brand")}</span>
                  <span>
                    {t("years")} {number(p.horizon_months / 12)}
                  </span>
                </div>
                <div className="banknote-core">
                  <span>{t("projected")}</span>
                  <strong>{money(result.summary.final_capital)}</strong>
                </div>
                <div className="banknote-bottom">
                  <span>
                    {t("net")} <b>{money(result.summary.final_capital_net)}</b>
                  </span>
                  <span aria-hidden="true">€</span>
                </div>
              </div>
              <Sparkline
                values={[
                  p.initial_capital,
                  ...result.monthly.map((r) => r.closing),
                ]}
                label={t("projection")}
              />
              <div className="figures">
                <Figure
                  label={t("invested")}
                  value={result.summary.total_contributed}
                />
                <Figure
                  label={t("gains")}
                  value={result.summary.interest_earned}
                  tone="green"
                />
                <Figure
                  label={t("real")}
                  value={result.summary.real_final_capital_net}
                />
              </div>
              <h2>{t("scenario")}</h2>
              <div className="scenarios">
                {scenarios?.map((v, i) => (
                  <div key={i} className={i === 1 ? "selected" : ""}>
                    <span>{t(["lower", "baseline", "higher"][i])}</span>
                    <strong>{money(v)}</strong>
                  </div>
                ))}
              </div>
              <form className="save-investment" onSubmit={(e) => void save(e)}>
                <Field label={t("investmentName")}>
                  <input
                    required
                    maxLength={120}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </Field>
                <button className="primary" disabled={saving}>
                  {t("saveInvestment")}
                </button>
              </form>
              {saved && <p role="status">{saved}</p>}
              {saved && <p role="status">{saved}</p>}
              {error && <Message>{error}</Message>}
            </>
          ) : (
            <Message>{t("validation")}</Message>
          )}
        </section>
      </div>
      {result && (
        <details className="breakdown">
          <summary>{t("details")}</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {[
                    "year",
                    "opening",
                    "contribution",
                    "interest",
                    "fees",
                    "withdrawn",
                    "closing",
                  ].map((k) => (
                    <th key={k}>{t(k)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.yearly.map((r) => (
                  <tr key={r.index}>
                    <th>{r.index}</th>
                    {[
                      r.opening,
                      r.contribution,
                      r.interest,
                      r.fees,
                      r.withdrawal,
                      r.closing,
                    ].map((v, i) => (
                      <td key={i}>{money(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </main>
  );
}
