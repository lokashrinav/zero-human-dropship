import { describe, expect, test } from "bun:test";
import { orderProductsByIdRanking } from "@/lib/product-ranking";

const products = [{ id: "alpha" }, { id: "beta" }, { id: "gamma" }, { id: "delta" }];

describe("orderProductsByIdRanking", () => {
	test("moves ranked products into the requested order", () => {
		expect(orderProductsByIdRanking(products, ["gamma", "alpha"]).map(({ id }) => id)).toEqual([
			"gamma",
			"alpha",
			"beta",
			"delta",
		]);
	});

	test("preserves the relative order of unranked products", () => {
		expect(orderProductsByIdRanking(products, ["delta"]).map(({ id }) => id)).toEqual([
			"delta",
			"alpha",
			"beta",
			"gamma",
		]);
	});

	test("does not mutate the source product list", () => {
		orderProductsByIdRanking(products, ["delta", "gamma"]);
		expect(products.map(({ id }) => id)).toEqual(["alpha", "beta", "gamma", "delta"]);
	});
});
