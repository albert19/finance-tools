import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

async function signIn(page: Page, path = "/") {
  const email = process.env.E2E_EMAIL;
  const passwordFile = process.env.E2E_PASSWORD_FILE;
  if (!email || !passwordFile) {
    throw new Error(
      "Set E2E_EMAIL and E2E_PASSWORD_FILE for the local account.",
    );
  }
  const password = readFileSync(passwordFile, "utf8").trimEnd();
  await page.goto(path);
  await page.getByRole("textbox", { name: "Email" }).fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("admin can sign in and navigate the personal finance screens", async ({
  page,
}) => {
  await signIn(page);
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await expect(nav).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Finance manager" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Simulator" })).toBeVisible();
  const accountTrigger = page.locator(".account-disclosure summary");
  await expect(accountTrigger).toContainText(process.env.E2E_EMAIL!);
  await accountTrigger.focus();
  await accountTrigger.press("Enter");
  await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  await accountTrigger.press("Escape");
  await expect(page.getByRole("link", { name: "Settings" })).toBeHidden();

  await nav.getByRole("link", { name: "Budget" }).click();
  await expect(page.getByRole("heading", { name: "Budget" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Monthly plan" }),
  ).toBeVisible();

  await nav.getByRole("link", { name: "Transactions" }).click();
  await expect(
    page.getByRole("heading", { name: "Transactions" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Add transaction" }),
  ).toBeVisible();

  await expect(nav.getByRole("link", { name: "Settings" })).toHaveCount(0);
  await page.locator(".account-disclosure summary").click();
  await page.getByRole("link", { name: "Settings" }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Categories" })).toBeVisible();
  await expect(page).toHaveURL(/\/settings$/);
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await nav.getByRole("link", { name: "Portfolio" }).click();
  await expect(page.getByRole("heading", { name: "Portfolio" })).toBeVisible();

  await page.locator(".account-disclosure summary").click();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("opening settings directly preserves the route through sign-in", async ({
  page,
}) => {
  await signIn(page, "/settings");
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
});

test("the mobile header stays within a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await signIn(page);
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }),
  ).toBeVisible();
  await page.locator(".account-disclosure summary").click();
  await expect(page.getByRole("link", { name: "Settings" })).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);

  await page.evaluate(() => localStorage.setItem("finance-locale", "es"));
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Gestor de finanzas" }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(320);
});
