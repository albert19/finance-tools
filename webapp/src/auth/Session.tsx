import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { request, refresh, login, logout, clearSession } from "../api/client";
import type { User } from "../api/types";
import i18n from "../i18n";
type SessionContext = {
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  updateUser: (u: User) => void;
};
const Context = createContext<SessionContext | null>(null);
export const useSession = () => {
  const value = useContext(Context);
  if (!value) throw new Error("Session provider missing");
  return value;
};
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [ready, setReady] = useState(false);
  useEffect(() => {
    let active = true;
    refresh()
      .then((access) => (access ? request<User>("/me") : null))
      .then((u) => {
        if (!active) return;
        setUser(u);
        if (u?.locale && !window.localStorage?.getItem("finance-locale"))
          void i18n.changeLanguage(u.locale);
      })
      .catch(() => {
        if (active) clearSession();
      })
      .finally(() => {
        if (active) setReady(true);
      });
    const onLogout = () => setUser(null);
    window.addEventListener("finance-logout", onLogout);
    return () => {
      active = false;
      window.removeEventListener("finance-logout", onLogout);
    };
  }, []);
  return (
    <Context.Provider
      value={{
        user,
        ready,
        signIn: async (email, password) => {
          await login(email, password);
          try {
            setUser(await request<User>("/me"));
          } catch (e) {
            clearSession();
            throw e;
          }
        },
        signOut: async () => {
          try {
            await logout();
          } finally {
            setUser(null);
          }
        },
        updateUser: setUser,
      }}
    >
      {children}
    </Context.Provider>
  );
}
