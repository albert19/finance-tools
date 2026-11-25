import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { ApiError, json, request } from "../api/client";
import { useSession } from "../auth/Session";
import { defaults, type Parameters } from "../domain/simulation/engine";
import { Field, Message } from "../design/ui";
import i18n from "../i18n";
import { Categories } from "./Categories";
import { loadSimulationDefaults, saveSimulationDefaults } from "./settings";

const frequencies = ["monthly", "quarterly", "semiannual", "annual"] as const;
export function Settings() {
  const { t } = useTranslation(),
    { user, updateUser, signOut } = useSession();
  const [defaultsForm, setDefaultsForm] = useState(() =>
    loadSimulationDefaults(user!.id),
  );
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const [message, setMessage] = useState(""),
    [error, setError] = useState("");
  function changeDefault<K extends keyof Parameters>(
    key: K,
    value: Parameters[K],
  ) {
    setDefaultsForm((current) => ({ ...current, [key]: value }));
  }
  async function changeLocale(locale: string) {
    if (!user) return;
    try {
      await request("/me", json("PATCH", { locale }));
      window.localStorage?.setItem("finance-locale", locale);
      await i18n.changeLanguage(locale);
      updateUser({ ...user, locale });
      setError("");
    } catch {
      setError(t("requestError"));
    }
  }
  async function saveDefaults(event: FormEvent) {
    event.preventDefault();
    saveSimulationDefaults(user!.id, defaultsForm);
    setError("");
    setMessage(t("settingsSaved"));
  }
  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await request(
        "/me/password",
        json("POST", {
          currentPassword: passwords.current,
          newPassword: passwords.next,
        }),
      );
      await signOut();
    } catch (cause) {
      const status = cause instanceof ApiError ? cause.status : 0;
      setError(
        status === 403
          ? t("currentPasswordIncorrect")
          : status === 429
            ? t("tooManyAttempts")
            : t("requestError"),
      );
    }
  }
  return (
    <main className="settings-page">
      <div className="page-heading">
        <div>
          <h1>{t("settings")}</h1>
          <p>{t("settingsHint")}</p>
        </div>
      </div>
      {message && <p role="status">{message}</p>}
      {error && <Message>{error}</Message>}
      <div className="settings-layout">
        <section className="input-panel">
          <h2>{t("account")}</h2>
          <p>{user?.email}</p>
          <Field label={t("locale")}>
            <select
              value={i18n.language.slice(0, 2)}
              onChange={(e) => void changeLocale(e.target.value)}
            >
              <option value="en">English</option>
              <option value="es">Español</option>
            </select>
          </Field>
          <form
            className="category-form"
            onSubmit={(e) => void changePassword(e)}
          >
            <h3>{t("changePassword")}</h3>
            <Field label={t("currentPassword")}>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={passwords.current}
                onChange={(e) =>
                  setPasswords((value) => ({
                    ...value,
                    current: e.target.value,
                  }))
                }
              />
            </Field>
            <Field label={t("newPassword")}>
              <input
                type="password"
                autoComplete="new-password"
                minLength={12}
                required
                value={passwords.next}
                onChange={(e) =>
                  setPasswords((value) => ({ ...value, next: e.target.value }))
                }
              />
            </Field>
            <button className="primary">{t("changePassword")}</button>
            <p className="settings-password-note">{t("passwordChangeNote")}</p>
          </form>
        </section>
        <section className="input-panel">
          <h2>{t("simulationDefaults")}</h2>
          <p>{t("simulationDefaultsHint")}</p>
          <form
            className="category-form"
            onSubmit={(e) => void saveDefaults(e)}
          >
            <Field label={t("compounding")}>
              <select
                value={defaultsForm.compounding_frequency}
                onChange={(e) =>
                  changeDefault(
                    "compounding_frequency",
                    e.target.value as Parameters["compounding_frequency"],
                  )
                }
              >
                {["daily", ...frequencies].map((value) => (
                  <option value={value} key={value}>
                    {t(value)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={t("timing")}>
              <select
                value={defaultsForm.contribution_timing}
                onChange={(e) =>
                  changeDefault(
                    "contribution_timing",
                    e.target.value as Parameters["contribution_timing"],
                  )
                }
              >
                <option value="beginning">{t("beginning")}</option>
                <option value="end">{t("end")}</option>
              </select>
            </Field>
            <Field label={t("frequency")}>
              <select
                value={defaultsForm.contribution_frequency}
                onChange={(e) =>
                  changeDefault(
                    "contribution_frequency",
                    e.target.value as Parameters["contribution_frequency"],
                  )
                }
              >
                {frequencies.map((value) => (
                  <option value={value} key={value}>
                    {t(value)}
                  </option>
                ))}
              </select>
            </Field>
            <button className="primary">{t("saveDefaults")}</button>
            <button
              type="button"
              onClick={() => {
                setDefaultsForm(defaults);
                saveSimulationDefaults(user!.id, defaults);
              }}
            >
              {t("restoreDefaults")}
            </button>
          </form>
        </section>
        <Categories />
      </div>
    </main>
  );
}
