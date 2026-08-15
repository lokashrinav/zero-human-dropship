import { expect, test } from "@playwright/test";

type PanelMeta = {
  mode: "live" | "demo" | "pending" | "error";
  label: "LIVE" | "DEMO DATA" | "WAITING" | "DEGRADED";
  fallback?: "demo";
};

type Snapshot = {
  generatedAt: string;
  isReceivingLiveData: boolean;
  metrics: {
    revenueMinor: number | null;
    orders: number | null;
  };
  revenue: {
    meta: PanelMeta;
    data: { amountMinor: number | null; orders: number | null; statusText: string };
  };
  linq: {
    meta: PanelMeta;
    data: {
      conversations: number;
      recommendations: number;
      paymentLinksSent: number;
      events: unknown[];
      phoneNumber: string | null;
    };
  };
  decisions: {
    meta: PanelMeta;
    data: { decisions: Array<{ id: string; outcome?: string }> };
  };
  terac: {
    meta: PanelMeta;
    data: {
      studies: Array<{
        feedback: {
          sampleSize: number;
          highestRatedProduct?: { name: string; averageLikelihood: number };
          lowestRatedProducts?: Array<{ name: string; averageLikelihood: number }>;
        };
        changes: Array<{ description: string }>;
      }>;
    };
  };
  catalog: {
    meta: PanelMeta;
    data: {
      productCount: number;
      activeCount: number;
      products: Array<{ active: boolean; url?: string }>;
    };
  };
  sponsors: Array<{ name: string; status: string; label: string }>;
};

test("aggregate endpoint returns an independently labeled snapshot", async ({ request }) => {
  const response = await request.get("/api/dashboard");
  expect(response.status()).toBe(200);
  expect(response.headers()["cache-control"]).toContain("no-store");

  const snapshot = (await response.json()) as Snapshot;
  expect(Number.isNaN(Date.parse(snapshot.generatedAt))).toBe(false);

  for (const panel of [
    snapshot.revenue,
    snapshot.linq,
    snapshot.decisions,
    snapshot.terac,
    snapshot.catalog,
  ]) {
    expect(["live", "demo", "pending", "error"]).toContain(panel.meta.mode);
    expect(["LIVE", "DEMO DATA", "WAITING", "DEGRADED"]).toContain(panel.meta.label);
    if (panel.meta.fallback) expect(panel.meta.fallback).toBe("demo");
  }

  expect(snapshot.sponsors.map((sponsor) => sponsor.name).sort()).toEqual(
    ["Band", "Linq", "Pioneer", "Render", "Replay", "Stripe", "Terac"],
  );

  const pioneer = snapshot.sponsors.find((sponsor) => sponsor.name === "Pioneer");
  expect(pioneer).toMatchObject({ status: "verified", label: "VERIFIED" });
  expect(snapshot.catalog.meta.mode).toBe("live");
  expect(snapshot.catalog.data.productCount).toBe(10);
  expect(snapshot.catalog.data.activeCount).toBe(10);
  expect(snapshot.catalog.data.products).toHaveLength(10);
  expect(snapshot.catalog.data.products.every((product) => product.active)).toBe(true);
  expect(
    snapshot.catalog.data.products.every((product) =>
      product.url?.startsWith("https://buy.stripe.com/"),
    ),
  ).toBe(true);

  if (snapshot.linq.meta.mode === "live") {
    expect(snapshot.linq.data.phoneNumber).toMatch(/415.?305.?0091/);
    expect(snapshot.linq.data.conversations).toBeGreaterThanOrEqual(0);
    expect(snapshot.linq.data.recommendations).toBeGreaterThanOrEqual(0);
    expect(snapshot.linq.data.paymentLinksSent).toBeGreaterThanOrEqual(0);
    expect(snapshot.linq.data.events.length).toBeGreaterThan(0);
  } else {
    expect(snapshot.linq.data.conversations).toBe(0);
    expect(snapshot.linq.data.events).toEqual([]);
  }

  if (snapshot.decisions.meta.mode === "live") {
    expect(snapshot.decisions.data.decisions.length).toBeGreaterThan(0);
  } else {
    expect(snapshot.decisions.data.decisions).toEqual([]);
  }

  if (snapshot.terac.meta.mode === "live") {
    const study = snapshot.terac.data.studies[0];
    expect(study.feedback.sampleSize).toBe(10);
    expect(study.feedback.highestRatedProduct).toMatchObject({
      name: "USB-C Fast Charging Cable 6ft",
      averageLikelihood: 3.9,
    });
    expect(study.feedback.lowestRatedProducts).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "Phone Ring Light for Selfies", averageLikelihood: 2.5 }),
        expect.objectContaining({ name: "Portable Mini Fan USB", averageLikelihood: 2.5 }),
      ]),
    );
    expect(study.changes[0]?.description).toMatch(/USB-C Cable moved from position 2 to 1/i);
    expect(snapshot.sponsors.find((sponsor) => sponsor.name === "Terac")).toMatchObject({
      status: "verified",
      label: "VERIFIED",
    });
  } else {
    expect(snapshot.terac.data.studies).toEqual([]);
  }
});

test("never serializes fixture revenue as real revenue", async ({ request }) => {
  const response = await request.get("/api/dashboard");
  const snapshot = (await response.json()) as Snapshot;

  if (snapshot.revenue.meta.mode === "live") {
    expect(snapshot.revenue.data.amountMinor).toBeGreaterThan(0);
    expect(snapshot.revenue.data.orders).toBeGreaterThan(0);
    expect(snapshot.revenue.data.statusText).toMatch(/live Stripe revenue/i);
  } else {
    expect(snapshot.revenue.data.amountMinor).toBeNull();
    expect(snapshot.revenue.data.orders).toBeNull();
    expect(snapshot.metrics.revenueMinor).toBeNull();
    expect(snapshot.metrics.orders).toBeNull();
    expect(snapshot.revenue.data.statusText).toMatch(/waiting for live Stripe revenue/i);
  }

  const serialized = JSON.stringify(snapshot);
  expect(serialized).not.toMatch(/(?:sk|rk)_(?:live|test)_/i);
  expect(serialized).not.toContain("Bearer ");
});
