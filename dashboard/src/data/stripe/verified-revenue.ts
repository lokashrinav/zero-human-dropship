import "server-only";

/**
 * Timestamped Stripe commerce proof from the final revenue sprint.
 *
 * The Stripe ledger contains four successful payments totaling $16.46, but two
 * were documented operator/self-tests. This snapshot intentionally includes
 * only the two genuine third-party purchases so the judge dashboard never
 * presents test spend as customer revenue.
 */
export const verifiedExternalRevenue = {
	amountMinor: 998,
	orders: 2,
	currency: "USD",
	verifiedAt: "2026-08-16T00:07:32Z",
} as const;
