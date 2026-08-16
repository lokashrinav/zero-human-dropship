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
  await expect(page.getByRole("link", { name: "OPEN LIVE STORE" })).toHaveAttribute(
    "href",
    "https://storefront-omega-three.vercel.app/",
  );

  const metricRegion = page.getByRole("region", { name: "Company metrics" });
  for (const metric of expectedMetrics) {
    await expect(metricRegion.getByText(new RegExp(`^${metric}$`, "i"))).toBeVisible();
  }

  const gallery = page.getByRole("region", { name: "Shop the live company" });
  await expect(gallery).toBeVisible();
  await expect(gallery.locator("[data-product-id]" )).toHaveCount(10);
  await expect(gallery.getByText(/^LIVE$/)).toHaveCount(10);
  await expect(gallery.getByRole("link", { name: /^View product /i })).toHaveCount(10);
  await expect(gallery.getByRole("link", { name: /^Buy now /i })).toHaveCount(10);
  await expect(gallery.locator("img")).toHaveCount(10);
  await expect(gallery.locator(".shop-card__image--fallback")).toHaveCount(0);
  const renderedProductIds = await gallery.locator("[data-product-id]").evaluateAll((cards) =>
    cards.map((card) => card.getAttribute("data-product-id")),
  );
  expect(new Set(renderedProductIds).size).toBe(10);

  const viewProductHrefs = await gallery.getByRole("link", { name: /^View product /i }).evaluateAll(
    (links) => links.map((link) => (link as HTMLAnchorElement).href),
  );
  expect(viewProductHrefs.every((href) => href.startsWith("https://storefront-omega-three.vercel.app/product/"))).toBe(true);
  const buyNowHrefs = await gallery.getByRole("link", { name: /^Buy now /i }).evaluateAll(
    (links) => links.map((link) => (link as HTMLAnchorElement).href),
  );
  expect(buyNowHrefs.every((href) => href.startsWith("https://buy.stripe.com/"))).toBe(true);

  await expect(page.getByRole("link", { name: "OPEN FULL STORE" })).toHaveAttribute(
    "href",
    "https://storefront-omega-three.vercel.app/",
  );
  await expect(page.getByRole("link", { name: "TEXT AI SHOPPER" })).toHaveAttribute(
    "href",
    "sms:+14153050091",
  );

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
    const flow = page.getByLabel("Recent Linq inbound to decision to outbound flow");
    await expect(flow).toBeVisible();
    await expect(flow.locator("li").first()).toBeVisible();
  }

  const bodyText = await page.locator("body").innerText();
  const showsRealRevenue = /Stripe\s*[—:-]?\s*REAL REVENUE/i.test(bodyText);
  const showsPendingRevenue = /Waiting\s+(?:for\s+)?live Stripe revenue/i.test(bodyText);
  expect(showsRealRevenue || showsPendingRevenue).toBe(true);
  await expect(page.getByText(/^Solari$/i)).toBeVisible();
  await expect(page.getByText(/^Superserve$/i)).toBeVisible();

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
