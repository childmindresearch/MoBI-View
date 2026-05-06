import { expect, test } from "@playwright/test";

test("loads the frontend scaffold", async ({ page }) => {
  await page.goto("/");

  await expect(
    page.getByRole("heading", { name: "Real-time stream visualization" }),
  ).toBeVisible();
  await expect(
    page.getByText("Frontend scaffold ready for ws://localhost:8765"),
  ).toBeVisible();
});
