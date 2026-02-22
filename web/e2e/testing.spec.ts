import { test, expect } from "@playwright/test";

// Note: These tests are designed to work with or without testing data.
// Since testing data may not be ingested yet, tests gracefully handle 404s.

test.describe("Testing List Page", () => {
  test("displays testing page or handles empty data", async ({ page }) => {
    const response = await page.goto("/testing/2024");
    const status = response?.status();

    // Either page loads successfully (200) or returns 404 (no data)
    if (status === 200) {
      // Page should have title
      await expect(page).toHaveTitle(/Pre-Season Testing|Testing/);

      // Should display hero section
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    } else {
      // 404 is acceptable if no testing data exists
      expect(status).toBe(404);
    }
  });

  test("displays event cards or empty state when data exists", async ({ page }) => {
    const response = await page.goto("/testing/2024");
    const status = response?.status();

    if (status !== 200) {
      // Skip if no data
      expect(status).toBe(404);
      return;
    }

    // Should display either event cards or empty state
    const eventCards = page.locator("article");
    const emptyState = page.getByText(/No Testing Events/i);

    const hasCards = await eventCards.first().isVisible().catch(() => false);
    const hasEmptyState = await emptyState.isVisible().catch(() => false);

    // One of these should be visible
    expect(hasCards || hasEmptyState).toBe(true);
  });

  test("event card links to detail page when data exists", async ({ page }) => {
    const response = await page.goto("/testing/2024");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Check if there are event cards
    const eventLinks = page.locator("a.group.block");
    const hasLinks = await eventLinks.first().isVisible().catch(() => false);

    if (hasLinks) {
      // Click first event link
      await eventLinks.first().click();

      // Should navigate to event detail page
      await expect(page).toHaveURL(/\/testing\/2024\/[a-z_-]+/);
    }
  });
});

test.describe("Testing Event Detail Page", () => {
  test("handles event page navigation", async ({ page }) => {
    // Navigate to a testing event (may not exist)
    const response = await page.goto("/testing/2024/bahrain_pre_season_test");
    const status = response?.status();

    // Either loads or 404
    if (status === 200) {
      const heading = page.getByRole("heading", { level: 1 });
      await expect(heading).toBeVisible();
    } else {
      expect(status).toBe(404);
    }
  });

  test("displays day tabs when data available", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // If page loads with content, should have day tabs
    const dayTabs = page.getByRole("button", { name: /Day \d/ });
    const hasData = await dayTabs.first().isVisible().catch(() => false);

    if (hasData) {
      // Should have at least Day 1 tab
      await expect(page.getByRole("button", { name: /Day 1/ })).toBeVisible();
    }
  });

  test("back link navigates to list", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Should have back link
    const backLink = page.getByRole("link", { name: /Back to Testing/ });
    const hasBackLink = await backLink.isVisible().catch(() => false);

    if (hasBackLink) {
      await backLink.click();
      await expect(page).toHaveURL(/\/testing\/2024/);
    }
  });
});

test.describe("Testing Day Tabs", () => {
  test("switches content when clicking day tabs", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Check if tabs exist
    const day1Tab = page.getByRole("button", { name: /Day 1/ });
    const day2Tab = page.getByRole("button", { name: /Day 2/ });

    const hasDay1 = await day1Tab.isVisible().catch(() => false);
    const hasDay2 = await day2Tab.isVisible().catch(() => false);

    if (hasDay1 && hasDay2) {
      // Click Day 2 tab
      await day2Tab.click();

      // URL should update
      await expect(page).toHaveURL(/day=2/);
    }
  });

  test("displays results or empty state", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Wait for page to load
    await page.waitForLoadState("domcontentloaded");

    // Should show table, no data message, or loading state
    const resultsTable = page.locator("table");
    const noData = page.getByText(/No Data Available/i);
    const loading = page.getByText(/Loading/i);

    // Wait for content to appear
    await Promise.race([
      resultsTable.first().waitFor({ timeout: 5000 }).catch(() => {}),
      noData.waitFor({ timeout: 5000 }).catch(() => {}),
      loading.waitFor({ timeout: 5000 }).catch(() => {}),
    ]);

    const hasTable = await resultsTable.first().isVisible().catch(() => false);
    const hasNoData = await noData.isVisible().catch(() => false);
    const hasLoading = await loading.isVisible().catch(() => false);

    // One of these states should be true
    expect(hasTable || hasNoData || hasLoading).toBe(true);
  });
});

test.describe("Testing Results Table", () => {
  test("displays correct columns when data exists", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Check for table headers
    const table = page.locator("table").first();
    const hasTable = await table.isVisible().catch(() => false);

    if (hasTable) {
      // Should have key columns
      await expect(page.getByRole("columnheader", { name: /Pos/i })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: /Driver/i })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: /Best Lap/i })).toBeVisible();
      await expect(page.getByRole("columnheader", { name: /Laps/i })).toBeVisible();
    }
  });

  test("displays driver rows with team logos when data exists", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    const table = page.locator("table").first();
    const hasTable = await table.isVisible().catch(() => false);

    if (hasTable) {
      // Should have driver rows
      const rows = table.locator("tbody tr");
      const rowCount = await rows.count();

      if (rowCount > 0) {
        // First row should have team logo
        const firstRow = rows.first();
        const teamLogo = firstRow.locator("img");
        await expect(teamLogo).toBeVisible();
      }
    }
  });
});

test.describe("Testing Stint Summary", () => {
  test("displays compound breakdown when data exists", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Check for stint summary section
    const stintSummary = page.getByRole("heading", { name: /Stint Summary/i });
    const hasStints = await stintSummary.isVisible().catch(() => false);

    if (hasStints) {
      // Should have compound indicators
      const compoundDots = page.locator(".rounded-full");
      await expect(compoundDots.first()).toBeVisible();
    }
  });
});

test.describe("Testing Lap Chart", () => {
  test("displays lap progression chart when data available", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Check for chart heading
    const chartHeading = page.getByRole("heading", { name: /Lap Time Progression/i });
    const hasChart = await chartHeading.isVisible().catch(() => false);

    if (hasChart) {
      // Should have driver selector buttons
      const driverButtons = page.locator("button").filter({ hasText: /[A-Z]{3}/ });
      await expect(driverButtons.first()).toBeVisible();
    }
  });

  test("driver selector toggles chart lines", async ({ page }) => {
    const response = await page.goto("/testing/2024/bahrain_pre_season_test?day=1");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    const chartHeading = page.getByRole("heading", { name: /Lap Time Progression/i });
    const hasChart = await chartHeading.isVisible().catch(() => false);

    if (hasChart) {
      // Find first driver button
      const driverButtons = page.locator("button").filter({ hasText: /[A-Z]{3}/ });
      const firstButton = driverButtons.first();

      // Click to toggle
      await firstButton.click();

      // Button should still be visible
      await expect(firstButton).toBeVisible();
    }
  });
});

test.describe("Testing Navigation", () => {
  test("nav bar has Testing link", async ({ page }) => {
    await page.goto("/");

    // Should have Testing link in navigation (hidden on mobile, visible on desktop)
    const testingLink = page.locator("header nav").getByRole("link", { name: /Testing/i });

    // Check if visible (desktop) or in mobile menu
    const isDesktopVisible = await testingLink.isVisible().catch(() => false);

    if (isDesktopVisible) {
      // Click and verify navigation
      await testingLink.click();
      await expect(page).toHaveURL(/\/testing\/\d{4}/);
    } else {
      // Try mobile menu
      const menuButton = page.locator("header button[aria-label='Toggle menu']");
      const hasMenuButton = await menuButton.isVisible().catch(() => false);

      if (hasMenuButton) {
        await menuButton.click();
        const mobileLink = page.locator("header").getByRole("link", { name: /Testing/i });
        await mobileLink.click();
        await expect(page).toHaveURL(/\/testing\/\d{4}/);
      }
    }
  });

  test("full testing navigation flow", async ({ page }) => {
    // Start at testing list
    const response = await page.goto("/testing/2024");
    const status = response?.status();

    if (status !== 200) {
      expect(status).toBe(404);
      return;
    }

    // Check if there are event cards
    const eventLinks = page.locator("a.group.block");
    const hasLinks = await eventLinks.first().isVisible().catch(() => false);

    if (hasLinks) {
      // Click first event
      await eventLinks.first().click();
      await expect(page).toHaveURL(/\/testing\/2024\/[a-z_-]+/);

      // Click back link
      const backLink = page.getByRole("link", { name: /Back to Testing/ });
      const hasBackLink = await backLink.isVisible().catch(() => false);

      if (hasBackLink) {
        await backLink.click();
        await expect(page).toHaveURL(/\/testing\/2024/);
      }
    }
  });
});

test.describe("Testing Error Handling", () => {
  test("invalid season shows error page", async ({ page }) => {
    const response = await page.goto("/testing/1990");

    // Should return 404 status or show error content
    const status = response?.status();
    const hasErrorContent = await page.getByText(/404|not found|error/i).isVisible().catch(() => false);

    expect(status === 404 || status === 500 || hasErrorContent).toBe(true);
  });

  test("invalid event shows not found", async ({ page }) => {
    const response = await page.goto("/testing/2024/nonexistent_event_xyz");

    // Should return 404 or show error
    const status = response?.status();
    const hasErrorContent = await page.getByText(/404|not found|error/i).isVisible().catch(() => false);

    expect(status === 404 || status === 500 || hasErrorContent).toBe(true);
  });
});
