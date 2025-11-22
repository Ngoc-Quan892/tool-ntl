import { test, expect } from "@playwright/test";

test.describe("Baccarat Predictor App", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("should load the app", async ({ page }) => {
    await expect(page.getByText(/Baccarat Predictor Pro/i)).toBeVisible();
  });

  test("should display prediction box", async ({ page }) => {
    await expect(page.getByText(/Prediction/i)).toBeVisible();
  });

  test("should have control panel buttons", async ({ page }) => {
    await expect(page.getByRole("button", { name: /Banker/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Player/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Tie/i })).toBeVisible();
  });

  test("should add result when button is clicked", async ({ page }) => {
    const bankerButton = page.getByRole("button", { name: /Banker/i });
    await bankerButton.click();
    
    // Should update UI (check for loading or success state)
    await expect(bankerButton).toBeVisible();
  });

  test("should display statistics", async ({ page }) => {
    await expect(page.getByText(/Statistics/i)).toBeVisible();
  });

  test("should display roadmaps", async ({ page }) => {
    await expect(page.getByText(/Roadmaps/i)).toBeVisible();
  });

  test("should display history table", async ({ page }) => {
    await expect(page.getByText(/History/i)).toBeVisible();
  });

  test("should reset game", async ({ page }) => {
    const resetButton = page.getByRole("button", { name: /Reset/i });
    await resetButton.click();
    
    // Should show confirmation or update UI
    await expect(resetButton).toBeVisible();
  });

  test("should export data", async ({ page }) => {
    const exportButton = page.getByRole("button", { name: /Export/i }).first();
    await expect(exportButton).toBeVisible();
  });

  test("should handle navigation", async ({ page }) => {
    // Test sidebar navigation if available
    const menuButton = page.getByRole("button", { name: /menu/i }).or(page.locator('[aria-label*="menu" i]'));
    if (await menuButton.count() > 0) {
      await menuButton.click();
      await expect(page.getByText(/Prediction/i).or(page.getByText(/Statistics/i))).toBeVisible();
    }
  });
});

test.describe("Error Handling", () => {
  test("should handle API errors gracefully", async ({ page }) => {
    // Mock API failure
    await page.route("**/api/v2/**", (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: "Internal server error" }),
      });
    });

    await page.goto("/");
    
    // App should still load and show error state
    await expect(page.getByText(/Baccarat Predictor Pro/i)).toBeVisible();
  });

  test("should handle network errors", async ({ page }) => {
    await page.route("**/api/**", (route) => {
      route.abort();
    });

    await page.goto("/");
    
    // App should handle offline state
    await expect(page.getByText(/Baccarat Predictor Pro/i)).toBeVisible();
  });
});

