import type { TeracData } from "../contracts";

export const teracFixture: TeracData = {
	studies: [
		{
			id: "demo-terac-price-study",
			title: "Price and positioning test",
			capturedAt: "2026-08-15T18:00:00.000Z",
			before: {
				summary: "Original mock catalog state",
				items: [
					{
						id: "demo-desk-vacuum",
						name: "Pocket Desk Vacuum",
						priceMinor: 1_400,
						currency: "USD",
						copy: "Powerful cleaning anywhere.",
						active: true,
					},
				],
			},
			feedback: {
				sampleSize: 8,
				result:
					"Mock panel preferred a $9–11 price and copy focused on desk crumbs.",
				rating: 4.4,
				ratingScale: 5,
			},
			changes: [
				{
					type: "price",
					description: "$14 → $10",
				},
				{
					type: "copy",
					description: "Copy refocused on fast desk cleanup.",
				},
			],
			after: {
				summary: "Autonomously updated mock business state",
				items: [
					{
						id: "demo-desk-vacuum",
						name: "Pocket Desk Vacuum",
						priceMinor: 1_000,
						currency: "USD",
						copy: "Clear desk crumbs in seconds.",
						active: true,
					},
				],
			},
		},
	],
};
