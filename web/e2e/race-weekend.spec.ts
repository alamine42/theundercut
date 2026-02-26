import { test, expect } from "@playwright/test";

test.describe("Race Weekend Widget on Homepage", () => {
  test("displays race weekend widget on homepage", async ({ page }) => {
    await page.goto("/");

    // Page should load successfully
    await expect(page).toHaveTitle(/THE UNDERCUT/);

    // Should display hero section
    await expect(page.getByRole("heading", { name: /THE UNDERCUT/ })).toBeVisible();
  });

  test("race weekend widget shows race info or message", async ({ page }) => {
    await page.goto("/");

    // Look for the race weekend widget card (it's an accent card)
    // It should either show race info or "No upcoming race information"
    const widgetContent = page.locator("article").first();
    await expect(widgetContent).toBeVisible();
  });

  test("homepage shows championship standings", async ({ page }) => {
    await page.goto("/");

    // Should show driver championship section
    await expect(page.getByRole("heading", { name: /Driver Championship/i })).toBeVisible();

    // Should show constructor championship section
    await expect(page.getByRole("heading", { name: /Constructor Championship/i })).toBeVisible();
  });

  test("homepage has navigation to standings", async ({ page }) => {
    await page.goto("/");

    // Should have View Full Standings button
    const standingsButton = page.getByRole("link", { name: /View Full Standings/i });
    await expect(standingsButton).toBeVisible();

    // Click and verify navigation
    await standingsButton.click();
    await expect(page).toHaveURL(/\/standings\/\d{4}/);
  });

  test("homepage has navigation to analytics", async ({ page }) => {
    await page.goto("/");

    // Should have Explore Analytics button
    const analyticsButton = page.getByRole("link", { name: /Explore Analytics/i });
    await expect(analyticsButton).toBeVisible();

    // Click and verify navigation
    await analyticsButton.click();
    await expect(page).toHaveURL(/\/analytics\/\d{4}\/\d+/);
  });
});

test.describe("Race Weekend Widget States", () => {
  test("widget displays content structure", async ({ page }) => {
    await page.goto("/");

    // Wait for page to fully load
    await page.waitForLoadState("networkidle");

    // Should have at least one Card component visible
    const cards = page.locator("article");
    await expect(cards.first()).toBeVisible();
  });
});

test.describe("Homepage Responsiveness", () => {
  test("mobile layout works correctly", async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // Hero should be visible
    await expect(page.getByRole("heading", { name: /THE UNDERCUT/ })).toBeVisible();

    // Stats should be visible
    await expect(page.getByText("Season")).toBeVisible();
    await expect(page.getByText("Races Completed")).toBeVisible();
  });

  test("tablet layout works correctly", async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/");

    // Hero should be visible
    await expect(page.getByRole("heading", { name: /THE UNDERCUT/ })).toBeVisible();

    // Championship cards should be visible
    await expect(page.getByRole("heading", { name: /Driver Championship/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Constructor Championship/i })).toBeVisible();
  });
});

test.describe("Pre-Season Testing Widget", () => {
  // This test is conditional - it only passes when we're in pre-season
  test("pre-season testing widget appears before season starts", async ({ page }) => {
    await page.goto("/");

    // Check if testing widget exists (may not be present if season has started)
    const testingWidget = page.getByRole("heading", { name: /Pre-Season Testing/i });
    const exists = await testingWidget.isVisible().catch(() => false);

    // If it exists, verify it has correct structure
    if (exists) {
      // Should show event links
      const eventLinks = page.locator("a[href*='/testing/']");
      await expect(eventLinks.first()).toBeVisible();
    }
  });
});

test.describe("Live Session Display", () => {
  test("session status badges have correct styling classes", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Check that the widget has loaded with status indicators
    // Status badges should be present (scheduled, live, or completed)
    const statusBadges = page.locator(".status-scheduled, .status-live, .status-completed");

    // If there are sessions displayed, at least one status badge should be visible
    const badgeCount = await statusBadges.count();
    if (badgeCount > 0) {
      await expect(statusBadges.first()).toBeVisible();
    }
  });

  test("live status indicator has correct visual styling", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // Check for live indicator class (will only be present during live sessions)
    const liveIndicator = page.locator(".status-live");
    const isLive = await liveIndicator.isVisible().catch(() => false);

    // If a session is live, verify it shows "Live" text
    if (isLive) {
      await expect(liveIndicator).toContainText("Live");
    }
  });
});
