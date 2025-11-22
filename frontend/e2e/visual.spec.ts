import { test, expect } from "@playwright/test";

test.describe("Visual Regression Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    // Wait for app to load
    await page.waitForSelector("text=Baccarat Predictor Pro");
  });

  test("should match homepage snapshot", async ({ page }) => {
    await expect(page).toHaveScreenshot("homepage.png", {
      fullPage: true,
      maxDiffPixels: 100,
    });
  });

  test("should match prediction box snapshot", async ({ page }) => {
    const predictionBox = page.locator('[class*="Prediction"]').first();
    await expect(predictionBox).toHaveScreenshot("prediction-box.png", {
      maxDiffPixels: 50,
    });
  });

  test("should match control panel snapshot", async ({ page }) => {
    const controlPanel = page.getByText(/Game Controls/i).locator("..");
    await expect(controlPanel).toHaveScreenshot("control-panel.png", {
      maxDiffPixels: 50,
    });
  });

  test("should match roadmap snapshot", async ({ page }) => {
    const roadmap = page.getByText(/Roadmaps/i).locator("..");
    await expect(roadmap).toHaveScreenshot("roadmap.png", {
      maxDiffPixels: 100,
    });
  });
});

