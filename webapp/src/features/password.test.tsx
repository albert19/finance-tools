import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "../api/client";
import i18n from "../i18n";
import { Settings } from "./Settings";

const { request, signOut } = vi.hoisted(() => ({
  request: vi.fn(),
  signOut: vi.fn(),
}));
vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return { ...original, request };
});
vi.mock("../auth/Session", () => ({
  useSession: () => ({
    user: { id: "u1", email: "a@example.test", roles: [], locale: "en" },
    updateUser: vi.fn(),
    signOut,
  }),
}));

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => {
  cleanup();
  request.mockReset();
  signOut.mockReset();
});

async function changePassword(status: number) {
  request.mockImplementation(async (path: string) => {
    if (path === "/me/password") throw new ApiError(status, {});
    return [];
  });
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <Settings />
    </QueryClientProvider>,
  );
  fireEvent.change(screen.getByLabelText("Current password"), {
    target: { value: "old-password-value" },
  });
  fireEvent.change(screen.getByLabelText("New password"), {
    target: { value: "new-password-value" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Change password" }));
}

it("reports a wrong current password (403) without signing out", async () => {
  await changePassword(403);
  expect(
    await screen.findByText("The current password is incorrect."),
  ).toBeTruthy();
  expect(signOut).not.toHaveBeenCalled();
});

it("asks the user to wait when password changes are throttled", async () => {
  await changePassword(429);
  expect(await screen.findByText(/Too many attempts/)).toBeTruthy();
});
