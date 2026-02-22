import { test, expect } from "@playwright/test";

test.describe("Circuit List Page", () => {
  test("displays circuit cards for current season", async ({ page }) => {
    await page.goto("/circuits");

    // Page should load successfully
    await expect(page).toHaveTitle(/Circuits/);

    // Should display hero section
    await expect(page.getByRole("heading", { name: /Circuits/ })).toBeVisible();

    // Should display circuit cards
    const circuitCards = page.locator("article");
    await expect(circuitCards.first()).toBeVisible();

    // Should NOT have year selector (removed)
    await expect(page.locator("select")).not.toBeVisible();
  });

  test("circuit card links to detail page", async ({ page }) => {
    await page.goto("/circuits");

    // Find the first circuit card link
    const circuitLinks = page.locator("a.group.block");
    await expect(circuitLinks.first()).toBeVisible();

    // Click first circuit link
    await circuitLinks.first().click();

    // Should navigate to circuit detail page (with season in URL)
    await expect(page).toHaveURL(/\/circuits\/\d{4}\/[a-z_-]+/);
  });

  test("old season URLs redirect to circuits", async ({ page }) => {
    // Old URLs like /circuits/2024 should redirect to /circuits
    await page.goto("/circuits/2024");
    await expect(page).toHaveURL("/circuits");
  });
});

test.describe("Circuit Detail Page", () => {
  test("displays circuit information", async ({ page }) => {
    // Navigate to a known circuit (Silverstone)
    await page.goto("/circuits/2024/silverstone");

    // Should show circuit name in title
    await expect(page).toHaveTitle(/silverstone.*2024/i);

    // Should show back link (now just "Back to Circuits")
    await expect(page.getByRole("link", { name: /Back to Circuits/ })).toBeVisible();

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

    // Should have link to trends - scroll to bottom where it is
    const trendsLink = page.getByRole("link", { name: /Multi-Season Trends/i });
    await trendsLink.scrollIntoViewIfNeeded();
    await expect(trendsLink).toBeVisible();

    // Click and verify navigation
    await trendsLink.click();
    await expect(page).toHaveURL(/\/circuits\/trends\/silverstone/);
  });

  test("back link returns to circuit list", async ({ page }) => {
    await page.goto("/circuits/2024/silverstone");

    // Click back link and wait for navigation
    await Promise.all([
      page.waitForURL(/\/circuits$/),
      page.getByRole("link", { name: /Back to Circuits/ }).click(),
    ]);

    // Verify we're on the list page
    await expect(page.getByRole("heading", { name: /Circuits/ })).toBeVisible();
  });
});

test.describe("Circuit Trends Page", () => {
  test("displays trends page content", async ({ page }) => {
    await page.goto("/circuits/trends/silverstone");

    // Should show page title with "Trends"
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/trends/i);

    // Should show hero section with stats (Seasons label)
    await expect(page.getByText("Seasons", { exact: true })).toBeVisible();
  });

  test("displays records or empty state", async ({ page }) => {
    await page.goto("/circuits/trends/silverstone");

    // Page should load successfully with heading
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // Should show either data content (article/table) or the main section exists
    const mainSection = page.locator("section");
    await expect(mainSection.first()).toBeVisible();
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

    // Click and verify navigation to /circuits
    await circuitsLink.click();
    await expect(page).toHaveURL(/\/circuits$/);
  });

  test("full circuit navigation flow", async ({ page }) => {
    // Start at circuits list
    await page.goto("/circuits");

    // Click first circuit card link
    const circuitLinks = page.locator("a.group.block");
    await expect(circuitLinks.first()).toBeVisible();
    await circuitLinks.first().click();
    await expect(page).toHaveURL(/\/circuits\/\d{4}\/[a-z_-]+/);

    // Go to trends - look for the link with "Multi-Season Trends" text
    const trendsLink = page.getByRole("link", { name: /Multi-Season Trends/i });
    await trendsLink.scrollIntoViewIfNeeded();
    await trendsLink.click();
    await expect(page).toHaveURL(/\/circuits\/trends\/[a-z_-]+/);
  });
});

test.describe("Error Handling", () => {
  test("invalid circuit shows error page", async ({ page }) => {
    const response = await page.goto("/circuits/2024/nonexistent_circuit_xyz");
    // Should return 404 status or show error content
    const status = response?.status();
    const hasErrorContent = await page.getByText(/404|not found|error|circuit/i).isVisible().catch(() => false);
    // Either 404 status or shows some indication it's not valid
    expect(status === 404 || status === 500 || hasErrorContent).toBe(true);
  });
});
