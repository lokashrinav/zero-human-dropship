import type { CatalogData } from "../contracts";

export const catalogFixture: CatalogData = {
	products: [
		{
			id: "demo-desk-vacuum",
			name: "Pocket Desk Vacuum",
			priceMinor: 1_000,
			currency: "USD",
			source: "DEMO supplier feed",
			active: true,
			promoted: true,
		},
		{
			id: "demo-cable-kit",
			name: "Magnetic Cable Kit",
			priceMinor: 1_200,
			currency: "USD",
			source: "DEMO supplier feed",
			active: true,
			promoted: true,
		},
		{
			id: "demo-travel-organizer",
			name: "Tech Travel Organizer",
			priceMinor: 2_400,
			currency: "USD",
			source: "DEMO supplier feed",
			active: false,
			promoted: false,
		},
	],
	productCount: 3,
	activeCount: 2,
	promotedProducts: [],
};

catalogFixture.promotedProducts = catalogFixture.products.filter(
	(product) => product.active && product.promoted,
);
