import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ApiError } from "../api/client";
import i18n from "../i18n";
import { Login } from "./Login";

const { signIn } = vi.hoisted(() => ({ signIn: vi.fn() }));
vi.mock("../auth/Session", () => ({ useSession: () => ({ signIn }) }));

beforeEach(async () => {
  await i18n.changeLanguage("en");
});
afterEach(() => {
  cleanup();
  signIn.mockReset();
});

async function submit() {
  render(<Login />);
  fireEvent.change(screen.getByRole("textbox", { name: "Email" }), {
    target: { value: "admin@example.test" },
  });
  fireEvent.change(screen.getByLabelText("Password"), {
    target: { value: "not-a-real-password" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

it("explains a rejected preview origin instead of blaming credentials", async () => {
  signIn.mockRejectedValueOnce(new ApiError(403, {}));
  await submit();
  expect(
    await screen.findByText(/Sign-in is blocked for this browser address/),
  ).toBeTruthy();
});

it("uses the credentials message for a genuine authentication failure", async () => {
  signIn.mockRejectedValueOnce(new ApiError(401, {}));
  await submit();
  expect(await screen.findByText(/Check your email and password/)).toBeTruthy();
});

it("tells a throttled user to wait instead of blaming credentials", async () => {
  signIn.mockRejectedValueOnce(new ApiError(429, {}));
  await submit();
  expect(await screen.findByText(/Too many sign-in attempts/)).toBeTruthy();
});
