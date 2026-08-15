import { expect, test, type Page } from "@playwright/test";

const expectedMetrics = [
  "REAL REVENUE",
  "ORDERS",
  "PRODUCTS LIVE",
  "CUSTOMER CONVERSATIONS",
  "AUTONOMOUS DECISIONS",
] as const;

function recordUnexpectedPageErrors(page: Page) {
  const errors: string[] = [];

  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });

  return errors;
}

test("renders the complete judge story with truthful data provenance", async ({ page }) => {
  const errors = recordUnexpectedPageErrors(page);

  await page.goto("/");

  await expect(
    page.getByRole("heading", { level: 1, name: /autonomous company/i }),
  ).toBeVisible();

  const metricRegion = page.getByRole("region", { name: "Company metrics" });
  for (const metric of expectedMetrics) {
    await expect(metricRegion.getByText(new RegExp(`^${metric}$`, "i"))).toBeVisible();
  }

  const workflow = page.getByLabel("Autonomous commerce workflow");
  await expect(workflow.getByText(/^SOURCE$/i)).toBeVisible();
  await expect(workflow.getByText(/^VALIDATE WITH HUMANS$/i)).toBeVisible();
  await expect(workflow.getByText(/^FULFILL$/i)).toBeVisible();
  await expect(workflow.getByText(/^LEARN$/i)).toBeVisible();

  await expect(page.getByText(/before human feedback/i).first()).toBeVisible();
  await expect(page.getByText(/terac feedback/i).first()).toBeVisible();
  await expect(page.getByText(/autonomous change/i).first()).toBeVisible();

  const teracLive = await page.getByText(/10 human responses/i).count();
  if (teracLive > 0) {
    await expect(page.getByText(/USB-C Fast Charging Cable 6ft/i).first()).toBeVisible();
    await expect(page.getByText(/Phone Ring Light for Selfies/i).first()).toBeVisible();
    await expect(page.getByText(/Portable Mini Fan USB/i).first()).toBeVisible();
  }

  const linqLive = await page.getByText(/^Sales agent online$/i).count();
  if (linqLive > 0) {
    const inboundVisible = await page.getByText(/^INBOUND MESSAGE$/i).count();
    const checkoutVisible = await page.getByText(/^CHECKOUT LINK SENT$/i).count();
    if (checkoutVisible > 0) {
      await expect(page.getByText(/^INBOUND MESSAGE$/i)).toBeVisible();
      await expect(page.getByText(/^INTENT DETECTED$/i)).toBeVisible();
      await expect(page.getByText(/^PRODUCT SELECTED$/i)).toBeVisible();
    } else if (inboundVisible === 0) {
      await expect(page.getByText(/^Waiting for inbound$/i)).toBeVisible();
    }
  }

  const bodyText = await page.locator("body").innerText();
  const showsRealRevenue = /Stripe\s*[—:-]?\s*REAL REVENUE/i.test(bodyText);
  const showsPendingRevenue = /Waiting\s+(?:for\s+)?live Stripe revenue/i.test(bodyText);
  expect(showsRealRevenue || showsPendingRevenue).toBe(true);

  await expect.poll(() => errors, { timeout: 1_000 }).toEqual([]);
});

test("keeps the dashboard usable when the aggregate feed fails", async ({ page }) => {
  let aggregateRequests = 0;
  await page.route("**/api/dashboard**", async (route) => {
    aggregateRequests += 1;
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: "intentional Replay isolation test" }),
    });
  });

  await page.goto("/");

  await expect(
    page.getByRole("heading", { level: 1, name: /autonomous company/i }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Company metrics" }).getByText(/^REAL REVENUE$/i),
  ).toBeVisible();
  await expect(page.locator("body")).toContainText(/Waiting/i);
  await expect(page.locator("body")).toContainText(/live Stripe revenue/i);
  await expect(page.getByText(/demo data|mock|degraded|waiting/i).first()).toBeVisible();
  await expect(page.getByText("FEED DEGRADED", { exact: true })).toBeVisible();
  expect(aggregateRequests).toBeGreaterThan(0);
});

test("has no horizontal overflow at the configured viewport", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toBeVisible();

  const overflow = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));

  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
});

test("primary controls use native interactive elements", async ({ page }) => {
  await page.goto("/");

  for (const element of await page.locator('[role="button"]').all()) {
    const tagName = await element.evaluate((node) => node.tagName.toLowerCase());
    expect(["button", "a"]).toContain(tagName);
  }

  const unnamedButtons = page.locator(
    'button:not([aria-label]):not(:has-text("Refresh")):not(:has-text("Retry")):not(:has-text("Reconnect"))',
  );
  for (const button of await unnamedButtons.all()) {
    await expect(button).not.toHaveAccessibleName("");
  }
});
