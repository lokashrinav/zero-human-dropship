import { describe, expect, test } from "bun:test";
import { catalog } from "@/lib/catalog";
import ranking from "@/terac-ranking.json";

describe("Terac-ranked catalog", () => {
	test("matches the approved-response product ordering", () => {
		expect(catalog.map(({ id }) => id)).toEqual(ranking.productIds);
	});

	test("preserves all ten active Stripe products and payment links", () => {
		expect(catalog).toHaveLength(10);
		expect(new Set(catalog.map(({ id }) => id)).size).toBe(10);
		expect(
			catalog.every(
				({ active, payment_link }) =>
					active && payment_link !== null && new URL(payment_link).hostname === "buy.stripe.com",
			),
		).toBe(true);
	});

	test("uses one labeled, reachable-format visualization per product", () => {
		expect(
			catalog.every(
				({ image_kind, images }) =>
					image_kind === "visualization" &&
					images.length === 1 &&
					images[0]?.startsWith(
						"https://raw.githubusercontent.com/lokashrinav/zero-human-dropship/codex/b-conversion-final/product_images/",
					) &&
					images[0].endsWith(".png"),
			),
		).toBe(true);
	});
});
