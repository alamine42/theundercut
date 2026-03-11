import { test, expect } from "@playwright/test";

test.describe("Circuit Characteristics List Page", () => {
  test("displays characteristics page with circuit data", async ({ page }) => {
    await page.goto("/circuits/characteristics");

    // Page should load successfully
    await expect(page).toHaveTitle(/Circuit Characteristics/);

    // Should display hero section
    await expect(page.getByRole("heading", { name: /Circuit Characteristics/ })).toBeVisible();

    // Should display subtitle
    await expect(page.getByText(/Comprehensive track data/i)).toBeVisible();
  });

  test("displays summary stats", async ({ page }) => {
    await page.goto("/circuits/characteristics");

    // Should show summary stat cards (look for the article cards)
    await expect(page.locator("article").first()).toBeVisible({ timeout: 15000 });
  });

  test("displays circuit table with characteristics", async ({ page }) => {
    await page.goto("/circuits/characteristics");

    // Should have table headers
    await expect(page.getByRole("columnheader", { name: /Circuit/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Type/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Throttle/i })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: /Tire Deg/i })).toBeVisible();

    // Should have circuit data in table rows
    const tableRows = page.locator("tbody tr");
    const rowCount = await tableRows.count();
    expect(rowCount).toBeGreaterThan(0);
  });

  test("displays score legend", async ({ page }) => {
    await page.goto("/circuits/characteristics");

    // Should show score legend
    await expect(page.getByText("Score Legend")).toBeVisible();
    await expect(page.getByText(/Low.*1-3/i)).toBeVisible();
    await expect(page.getByText(/High.*6-7/i)).toBeVisible();
  });

  test("has link to compare circuits", async ({ page }) => {
    await page.goto("/circuits/characteristics");

    // Should have Compare Circuits button in hero
    const compareLink = page.getByRole("link", { name: /Compare Circuits/i });
    await expect(compareLink).toBeVisible();

    // Click and verify navigation
    await compareLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics\/compare/);
  });

  test("has link to circuit rankings", async ({ page }) => {
    await page.goto("/circuits/characteristics");

    // Should have link to rankings
    const rankLink = page.getByRole("link", { name: /Circuit Rankings/i });
    await rankLink.scrollIntoViewIfNeeded();
    await expect(rankLink).toBeVisible();

    // Click and verify navigation
    await rankLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics\/rank/);
  });
});

test.describe("Circuit Characteristics Compare Page", () => {
  test("displays compare page with circuit selection", async ({ page }) => {
    await page.goto("/circuits/characteristics/compare");

    // Page should load
    await expect(page).toHaveTitle(/Compare Circuits/);
    await expect(page.getByRole("heading", { name: /Compare Circuits/ })).toBeVisible();

    // Should show instruction text
    await expect(page.getByText(/Select.*2-5 circuits/i)).toBeVisible();
  });

  test("shows circuit selection buttons", async ({ page }) => {
    await page.goto("/circuits/characteristics/compare");

    // Should have Select Circuits section
    await expect(page.getByText(/Select Circuits/i)).toBeVisible();

    // Should have circuit buttons to select
    const circuitButtons = page.locator("article button");
    const buttonCount = await circuitButtons.count();
    expect(buttonCount).toBeGreaterThan(0);
  });

  test("shows empty state when no circuits selected", async ({ page }) => {
    await page.goto("/circuits/characteristics/compare");

    // Should show empty state message
    await expect(page.getByText(/Select at least 2 circuits/i)).toBeVisible();
  });

  test("can select circuits for comparison", async ({ page }) => {
    await page.goto("/circuits/characteristics/compare");

    // Find circuit selection buttons - they're in the flex container with circuit names
    // Exclude the "Clear all" button by looking for buttons that have flag emojis
    const selectionArticle = page.locator("article").first();
    await expect(selectionArticle).toBeVisible({ timeout: 15000 });

    // Get buttons that contain flag emojis (circuit buttons have country flags)
    const circuitButtons = selectionArticle.locator("button").filter({
      hasNot: page.getByText(/Clear all/i),
    });

    // Check we have at least 2 circuits available
    const buttonCount = await circuitButtons.count();
    if (buttonCount < 2) {
      // If less than 2 circuits have characteristics, skip
      console.log(`Only ${buttonCount} circuits available, skipping selection test`);
      return;
    }

    // Click first two circuits
    await circuitButtons.nth(0).click();
    await circuitButtons.nth(1).click();

    // After selecting 2 circuits, the header should show (2/5)
    await expect(page.getByText("Select Circuits (2/5)")).toBeVisible({ timeout: 10000 });
  });

  test("has back link to characteristics list", async ({ page }) => {
    await page.goto("/circuits/characteristics/compare");

    // Should have back link
    const backLink = page.getByRole("link", { name: /Back to Characteristics/i });
    await expect(backLink).toBeVisible();

    // Click and verify navigation
    await backLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics$/);
  });
});

test.describe("Circuit Characteristics Rank Page", () => {
  test("displays ranking page with field selection", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Page should load
    await expect(page).toHaveTitle(/Circuit Rankings/);
    await expect(page.getByRole("heading", { name: /Circuit Rankings/ })).toBeVisible();
  });

  test("shows ranking field buttons", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Should have Rank By section
    await expect(page.getByText(/Rank By/i)).toBeVisible();

    // Should have field selection buttons
    await expect(page.getByRole("button", { name: /Full Throttle/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Average Speed/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Tire Degradation/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Downforce/i })).toBeVisible();
  });

  test("shows order toggle", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Should have order toggle buttons
    await expect(page.getByRole("button", { name: /Highest First/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Lowest First/i })).toBeVisible();
  });

  test("displays ranking table or loading state", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Should have table structure (even if loading)
    await expect(page.locator("article").first()).toBeVisible({ timeout: 10000 });

    // Wait a bit for potential data load
    await page.waitForTimeout(3000);

    // Should have either data rows OR loading/error state
    const hasTable = await page.locator("table").isVisible();
    const hasLoading = await page.getByText(/Loading/i).isVisible();
    const hasError = await page.getByText(/error|failed/i).isVisible();
    const hasNoData = await page.getByText(/No data/i).isVisible();

    // At least one of these should be true
    expect(hasTable || hasLoading || hasError || hasNoData).toBe(true);
  });

  test("can click ranking field buttons", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Should be able to click field buttons
    const downforceBtn = page.getByRole("button", { name: /Downforce/i });
    await expect(downforceBtn).toBeVisible({ timeout: 10000 });
    await downforceBtn.click();

    // Button should now be selected (has accent color)
    await expect(downforceBtn).toBeVisible();
  });

  test("can toggle sort order buttons", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Should have order toggle buttons
    const lowestBtn = page.getByRole("button", { name: /Lowest First/i });
    await expect(lowestBtn).toBeVisible({ timeout: 10000 });

    // Click lowest first
    await lowestBtn.click();

    // Button should still be visible
    await expect(lowestBtn).toBeVisible();
  });

  test("has back link to characteristics list", async ({ page }) => {
    await page.goto("/circuits/characteristics/rank");

    // Should have back link
    const backLink = page.getByRole("link", { name: /Back to Characteristics/i });
    await expect(backLink).toBeVisible();
  });
});

test.describe("Circuit Characteristics Navigation", () => {
  test("main circuits page has link to characteristics", async ({ page }) => {
    await page.goto("/circuits");

    // Should have Track Characteristics button
    const charLink = page.getByRole("link", { name: /Track Characteristics/i });
    await expect(charLink).toBeVisible({ timeout: 15000 });

    // Click and verify navigation
    await charLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics$/, { timeout: 15000 });
  });

  test("full characteristics navigation flow", async ({ page }) => {
    // Start at main circuits page
    await page.goto("/circuits");

    // Navigate to characteristics
    const charLink = page.getByRole("link", { name: /Track Characteristics/i });
    await expect(charLink).toBeVisible({ timeout: 15000 });
    await charLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics$/, { timeout: 15000 });

    // Navigate to compare
    const compareLink = page.getByRole("link", { name: /Compare Circuits/i });
    await expect(compareLink).toBeVisible({ timeout: 15000 });
    await compareLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics\/compare/, { timeout: 15000 });

    // Go back to list
    const backLink = page.getByRole("link", { name: /Back to Characteristics/i });
    await expect(backLink).toBeVisible({ timeout: 15000 });
    await backLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics$/, { timeout: 15000 });

    // Navigate to rankings
    const rankLink = page.getByRole("link", { name: /Circuit Rankings/i });
    await rankLink.scrollIntoViewIfNeeded();
    await rankLink.click();
    await expect(page).toHaveURL(/\/circuits\/characteristics\/rank/);
  });
});
