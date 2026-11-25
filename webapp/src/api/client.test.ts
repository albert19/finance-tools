import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { clearSession, login, request, setAccessToken, json } from "./client";
let refreshes = 0;
const server = setupServer(
  http.post("http://localhost:3000/api/auth/login", () =>
    HttpResponse.json({ accessToken: "login-token", expiresIn: 120 }),
  ),
  http.post("http://localhost:3000/api/auth/refresh", () => {
    refreshes++;
    return HttpResponse.json({ accessToken: "renewed", expiresIn: 120 });
  }),
  http.get("http://localhost:3000/api/me", ({ request: req }) =>
    req.headers.get("authorization") === "Bearer renewed" ||
    req.headers.get("authorization") === "Bearer login-token"
      ? HttpResponse.json({ id: "1", email: "person@example.org" })
      : HttpResponse.json({ title: "Unauthorized" }, { status: 401 }),
  ),
);
beforeAll(() => {
  window.__FINANCE_CONFIG__ = { apiBaseUrl: "http://localhost:3000/api" };
  server.listen({ onUnhandledRequest: "error" });
});
afterEach(() => {
  server.resetHandlers();
  setAccessToken(null);
  refreshes = 0;
});
afterAll(() => {
  server.close();
  clearSession();
});
describe("API session", () => {
  it("sends credentials and keeps the returned access token in memory", async () => {
    await login("person@example.org", "password");
    expect((await request<{ email: string }>("/me")).email).toBe(
      "person@example.org",
    );
    expect(refreshes).toBe(0);
  });
  it("refreshes once for concurrent requests", async () => {
    const [first, second] = await Promise.all([
      request<{ id: string }>("/me"),
      request<{ id: string }>("/me"),
    ]);
    expect(first.id).toBe("1");
    expect(second.id).toBe("1");
    expect(refreshes).toBe(1);
  });
  it("sends the CSRF header and cookie credentials to auth endpoints", async () => {
    let checked = false;
    server.use(
      http.post("http://localhost:3000/api/auth/login", ({ request: req }) => {
        expect(req.headers.get("X-Requested-With")).toBe("XMLHttpRequest");
        expect(req.credentials).toBe("include");
        checked = true;
        return HttpResponse.json({
          accessToken: "login-token",
          expiresIn: 120,
        });
      }),
    );
    await login("person@example.org", "password");
    expect(checked).toBe(true);
    expect(json("DELETE", { version: 3 })).toEqual({
      method: "DELETE",
      body: '{"version":3}',
    });
  });
});
