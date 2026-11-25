export type Problem = {
  title?: string;
  detail?: string;
  errors?: { field: string; code: string; message?: string }[];
};
export class ApiError extends Error {
  constructor(
    public status: number,
    public problem: Problem,
  ) {
    super(problem.detail || problem.title || `Request failed (${status})`);
  }
}
declare global {
  interface Window {
    __FINANCE_CONFIG__?: { apiBaseUrl: string };
  }
}
const base = () =>
  (window.__FINANCE_CONFIG__?.apiBaseUrl || "/api").replace(/\/$/, "");
let token: string | null = null;
let expiry = 0;
let refreshFlight: Promise<string | null> | null = null;
const channel =
  typeof BroadcastChannel !== "undefined"
    ? new BroadcastChannel("finance-auth")
    : null;
let refreshNotice: Promise<void> | null = null;
let releaseNotice: (() => void) | undefined;
channel?.addEventListener("message", (event: MessageEvent) => {
  if (event.data?.type === "refreshing") {
    refreshNotice = new Promise<void>((resolve) => {
      releaseNotice = resolve;
    });
    setTimeout(() => {
      releaseNotice?.();
      refreshNotice = null;
    }, 6000);
  }
  if (event.data?.type === "refreshed") {
    releaseNotice?.();
    refreshNotice = null;
  }
  if (event.data?.type === "logout") {
    token = null;
    expiry = 0;
    window.dispatchEvent(new Event("finance-logout"));
  }
});
export function setAccessToken(value: string | null, expiresIn?: number) {
  token = value;
  expiry = value ? Date.now() + (expiresIn || 120) * 800 : 0;
}
export function clearSession() {
  setAccessToken(null);
  channel?.postMessage({ type: "logout" });
}
function unpack(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const value = data as Record<string, unknown>;
  const access = value.accessToken;
  if (typeof access !== "string") return null;
  setAccessToken(access, Number(value.expiresIn ?? 120));
  return access;
}
export async function login(email: string, password: string) {
  const result = await raw("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!unpack(result))
    throw new Error("Login response did not contain an access token");
}
async function raw<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base()}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(path.startsWith("/auth/")
        ? { "X-Requested-With": "XMLHttpRequest" }
        : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    let problem: Problem = {};
    try {
      problem = (await response.json()) as Problem;
    } catch {
      /* non-JSON gateway error */
    }
    throw new ApiError(response.status, problem);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export async function refresh(): Promise<string | null> {
  if (refreshFlight) return refreshFlight;
  refreshFlight = (async () => {
    // A tab that refreshed just before us cannot share its access token; the
    // cookie is now rotated, so wait for it and refresh with the new cookie.
    if (refreshNotice) await refreshNotice;
    const perform = async () => {
      channel?.postMessage({ type: "refreshing" });
      try {
        return unpack(await raw("/auth/refresh", { method: "POST" }));
      } catch {
        setAccessToken(null);
        return null;
      } finally {
        channel?.postMessage({ type: "refreshed" });
      }
    };
    if (navigator.locks)
      return navigator.locks.request("finance-refresh", perform);
    return perform();
  })().finally(() => {
    refreshFlight = null;
  });
  return refreshFlight;
}
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  if (!token || Date.now() >= expiry) await refresh();
  const authorized = () =>
    raw<T>(path, {
      ...init,
      headers: {
        ...init.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  try {
    return await authorized();
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
    setAccessToken(null);
    if (!(await refresh())) throw error;
    return authorized();
  }
}
export async function logout() {
  try {
    await raw("/auth/logout", { method: "POST" });
  } finally {
    clearSession();
  }
}
export const json = (method: string, body: unknown): RequestInit => ({
  method,
  body: JSON.stringify(body),
});
