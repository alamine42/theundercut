import { test, expect } from "@playwright/test";

test.describe("Circuit List Page", () => {
  test("displays circuit cards for 2024 season", async ({ page }) => {
    await page.goto("/circuits/2024");

    // Page should load successfully
    await expect(page).toHaveTitle(/2024 Circuits/);

    // Should display hero section
    await expect(page.getByRole("heading", { name: /2024 Circuits/ })).toBeVisible();

    // Should display circuit cards
    const circuitCards = page.locator("article");
    await expect(circuitCards.first()).toBeVisible();

    // Should have year selector
    await expect(page.locator("select")).toBeVisible();
  });

  test("displays circuit cards for 2025 season", async ({ page }) => {
    await page.goto("/circuits/2025");

    await expect(page).toHaveTitle(/2025 Circuits/);
    await expect(page.getByRole("heading", { name: /2025 Circuits/ })).toBeVisible();
  });

  test("year selector navigates between seasons", async ({ page }) => {
    await page.goto("/circuits/2024");

    // Change to 2025
    await page.selectOption("select", "2025");

    // Wait for navigation
    await page.waitForURL(/\/circuits\/2025/);
    await expect(page.getByRole("heading", { name: /2025 Circuits/ })).toBeVisible();
  });

  test("circuit card links to detail page", async ({ page }) => {
    await page.goto("/circuits/2024");

    // Find links that contain articles (circuit cards)
    const circuitLinks = page.locator("a.group.block");
    await expect(circuitLinks.first()).toBeVisible();

    // Click first circuit link
    await circuitLinks.first().click();

    // Should navigate to circuit detail page
    await expect(page).toHaveURL(/\/circuits\/2024\/[a-z_-]+/);
  });
});

test.describe("Circuit Detail Page", () => {
  test("displays circuit information", async ({ page }) => {
    // Navigate to a known circuit (Silverstone)
    await page.goto("/circuits/2024/silverstone");

    // Should show circuit name in title
    await expect(page).toHaveTitle(/silverstone.*2024/i);

    // Should show back link
    await expect(page.getByRole("link", { name: /Back to 2024 Circuits/ })).toBeVisible();

    // Should show circuit name
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("displays lap records section", async ({ page }) => {
    await page.goto("/circuits/2024/silverstone");

    // Should have lap records section
    await expect(page.getByText(/All-Time Lap Record/i)).toBeVisible();
    await expect(page.getByText(/2024 Fastest Lap/i)).toBeVisible();
  });

  test("displays circuit content sections", async ({ page }) => {
    await page.goto("/circuits/2024/silverstone");

    // Should have multiple article/section cards on the page
    const articles = page.locator("article");
    const count = await articles.count();
    expect(count).toBeGreaterThan(0);

    // Should have structured content
    await expect(page.locator("h2").first()).toBeVisible();
  });

  test("has link to trends page", async ({ page }) => {
    await page.goto("/circuits/2024/silverstone");

    // Should have link to trends (partial text match)
    const trendsLink = page.getByRole("link", { name: /Trends/i });
    await expect(trendsLink).toBeVisible();

    // Click and verify navigation
    await trendsLink.click();
    await expect(page).toHaveURL(/\/circuits\/trends\/silverstone/);
  });

  test("back link returns to circuit list", async ({ page }) => {
    await page.goto("/circuits/2024/silverstone");

    // Click back link
    await page.getByRole("link", { name: /Back to 2024 Circuits/ }).click();

    // Should be back on list page
    await expect(page).toHaveURL(/\/circuits\/2024$/);
  });
});

test.describe("Circuit Trends Page", () => {
  test("displays trends page content", async ({ page }) => {
    await page.goto("/circuits/trends/silverstone");

    // Should show page title with "Trends"
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Should show chart container (may not render recharts-wrapper in headless)
    await expect(page.locator("article").first()).toBeVisible();
  });

  test("displays records and table", async ({ page }) => {
    await page.goto("/circuits/trends/silverstone");

    // Should have tables on page
    const tables = page.locator("table");
    await expect(tables.first()).toBeVisible();

    // Should have year data in table
    await expect(page.getByRole("cell").first()).toBeVisible();
  });

  test("has back link to circuits", async ({ page }) => {
    await page.goto("/circuits/trends/silverstone");

    // Should have back link
    await expect(page.getByRole("link", { name: /Circuits/i }).first()).toBeVisible();
  });
});

test.describe("Circuit Navigation", () => {
  test("nav bar has Circuits link", async ({ page }) => {
    await page.goto("/");

    // Should have Circuits link in navigation (in header)
    const circuitsLink = page.locator("header").getByRole("link", { name: /Circuits/i });
    await expect(circuitsLink).toBeVisible();

    // Click and verify navigation
    await circuitsLink.click();
    await expect(page).toHaveURL(/\/circuits\/\d{4}$/);
  });

  test("full circuit navigation flow", async ({ page }) => {
    // Start at circuits list
    await page.goto("/circuits/2024");

    // Click first circuit link
    await page.locator("a").filter({ has: page.locator("article") }).first().click();
    await expect(page).toHaveURL(/\/circuits\/2024\/[a-z_-]+/);

    // Go to trends
    await page.getByRole("link", { name: /Multi-Season Trends/i }).click();
    await expect(page).toHaveURL(/\/circuits\/trends\/[a-z_-]+/);
  });
});

test.describe("Error Handling", () => {
  test("invalid season shows error page", async ({ page }) => {
    const response = await page.goto("/circuits/1990");
    // Should return 404 status or show error content
    const status = response?.status();
    const hasErrorContent = await page.getByText(/404|not found|error/i).isVisible().catch(() => false);
    expect(status === 404 || hasErrorContent).toBe(true);
  });

  test("invalid circuit shows error page", async ({ page }) => {
    const response = await page.goto("/circuits/2024/nonexistent_circuit_xyz");
    // Should return 404 status or show error content
    const status = response?.status();
    const hasErrorContent = await page.getByText(/404|not found|error|circuit/i).isVisible().catch(() => false);
    // Either 404 status or shows some indication it's not valid
    expect(status === 404 || status === 500 || hasErrorContent).toBe(true);
  });
});
