import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useSession } from "../auth/Session";
import { ApiError } from "../api/client";
import { Field, Message } from "../design/ui";
export function Login() {
  const { t } = useTranslation(),
    { signIn } = useSession();
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<
      "loginError" | "loginOriginError" | "loginThrottled" | null
    >(null);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (cause) {
      const status = cause instanceof ApiError ? cause.status : 0;
      setError(
        status === 403
          ? "loginOriginError"
          : status === 429
            ? "loginThrottled"
            : "loginError",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-mark" aria-hidden="true">
        €
      </div>
      <form className="login-form" onSubmit={submit}>
        <div className="brand">✳ {t("brand")}</div>
        <h1>{t("tagline")}</h1>
        <p>{t("loginHint")}</p>
        <Field label={t("email")}>
          <input
            autoComplete="username"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label={t("password")}>
          <input
            autoComplete="current-password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {error && <Message>{t(error)}</Message>}
        <button className="primary" disabled={busy}>
          {busy ? t("loading") : t("signIn")}
        </button>
      </form>
    </main>
  );
}
