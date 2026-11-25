import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { request } from "../api/client";
import { useSession } from "../auth/Session";
import { Login } from "../features/Login";
import { Simulator } from "../features/Simulator";
import { Portfolio } from "../features/Portfolio";
import { BudgetPage } from "../features/Budget";
import { Transactions } from "../features/Transactions";
import { Settings } from "../features/Settings";
import { Message } from "../design/ui";
import i18n from "../i18n";
export function App() {
  const { t } = useTranslation(),
    { user, ready, signOut, updateUser } = useSession();
  const [error, setError] = useState(""),
    queryClient = useQueryClient();
  if (!ready)
    return (
      <div className="boot" role="status">
        {t("loading")}
      </div>
    );
  if (!user) return <Login />;
  async function changeLocale(locale: string) {
    window.localStorage?.setItem("finance-locale", locale);
    await i18n.changeLanguage(locale);
    if (user) {
      try {
        await request("/me", {
          method: "PATCH",
          body: JSON.stringify({ locale }),
        });
        updateUser({ ...user, locale });
      } catch {
        setError(t("requestError"));
      }
    }
  }
  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/simulator" aria-label={t("brand")}>
          ✳ {t("brand")}
        </NavLink>
        <nav aria-label="Main navigation">
          {(["simulator", "portfolio", "budget", "transactions"] as const).map(
            (page) => (
              <NavLink to={`/${page}`} key={page}>
                {t(page)}
              </NavLink>
            ),
          )}
        </nav>
        <div className="account">
          <details
            className="account-disclosure"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.currentTarget.open = false;
                event.currentTarget.querySelector("summary")?.focus();
              }
            }}
          >
            <summary aria-label={`${t("accountMenu")}: ${user.email}`}>
              <span className="account-name">{user.email}</span>
              <span aria-hidden="true" className="account-chevron">
                ⌄
              </span>
            </summary>
            <div className="account-menu">
              <NavLink
                to="/settings"
                onClick={(event) =>
                  event.currentTarget
                    .closest("details")
                    ?.removeAttribute("open")
                }
              >
                {t("settings")}
              </NavLink>
              <label className="account-language" htmlFor="locale">
                <span>{t("locale")}</span>
                <select
                  id="locale"
                  value={i18n.language.slice(0, 2)}
                  onChange={(event) => void changeLocale(event.target.value)}
                >
                  <option value="en">EN</option>
                  <option value="es">ES</option>
                </select>
              </label>
              <button
                type="button"
                className="text-button"
                onClick={(event) => {
                  event.currentTarget
                    .closest("details")
                    ?.removeAttribute("open");
                  void signOut()
                    .catch(() => setError(t("logoutError")))
                    .finally(() => queryClient.clear());
                }}
              >
                {t("signOut")}
              </button>
            </div>
          </details>
        </div>
      </header>
      {error && <Message>{error}</Message>}
      <div className="content">
        <Routes>
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/budget" element={<BudgetPage />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/simulator" replace />} />
        </Routes>
      </div>
      <footer className="footer">
        <span>✳ {t("brand")}</span>
        <span>{t("serverNotice")}</span>
      </footer>
    </div>
  );
}
