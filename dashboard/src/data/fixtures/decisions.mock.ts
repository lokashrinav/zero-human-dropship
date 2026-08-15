import type { DecisionsData } from "../contracts";

const minutesAgo = (minutes: number) =>
	new Date(Date.now() - minutes * 60_000).toISOString();

export const decisionsFixture = (): DecisionsData => ({
	decisions: [
		{
			id: "demo-decision-price",
			timestamp: minutesAgo(7),
			agent: "CEO AGENT",
			title: "REPRICED PRODUCT",
			kind: "repriced_product",
			reason:
				"Mock Terac panel willingness-to-pay clustered below the original price.",
			action: "$14 → $10",
			stage: "learn",
		},
		{
			id: "demo-decision-list",
			timestamp: minutesAgo(18),
			agent: "CEO AGENT",
			title: "PROMOTED PRODUCT",
			kind: "changed_promotion",
			reason:
				"Mock feedback ranked portability as the strongest purchase driver.",
			action: "Pocket Desk Vacuum moved to featured slot",
			stage: "list",
		},
	],
});
