import {
	asIsoDate,
	asNonNegativeInteger,
	asString,
	getErrorMessage,
	integrationMeta,
	isRecord,
} from "../common";
import { dashboardConfig } from "../config";
import type { PanelState, RevenueData } from "../contracts";
import { fetchJson } from "../http";

const pendingRevenue = (detail: string): PanelState<RevenueData> => ({
	meta: integrationMeta("pending", detail),
	data: {
		amountMinor: null,
		currency: "USD",
		orders: null,
		statusText: "Waiting for live Stripe revenue",
	},
});

const parseRevenueEndpoint = (payload: unknown): PanelState<RevenueData> => {
	if (!isRecord(payload)) throw new Error("Revenue response must be an object");
	if (payload.source !== "stripe" || payload.livemode !== true) {
		throw new Error("Revenue endpoint did not attest to live Stripe data");
	}

	const amountMinor = asNonNegativeInteger(payload.amountMinor);
	const orders = asNonNegativeInteger(payload.orders);
	const currency = asString(payload.currency)?.toUpperCase();
	const updatedAt = asIsoDate(payload.updatedAt);

	if (amountMinor === undefined || orders === undefined || !currency || !updatedAt) {
		throw new Error("Revenue endpoint response does not match its contract");
	}
	if (amountMinor === 0 || orders === 0) {
		return pendingRevenue(
			"Live Stripe feed connected; no successful live payments yet",
		);
	}

	return {
		meta: integrationMeta("live", "Verified live-mode Stripe data", updatedAt),
		data: {
			amountMinor,
			currency,
			orders,
			statusText: "Live Stripe revenue",
		},
	};
};

type StripeCharge = {
	id: string;
	amount: number;
	amountRefunded: number;
	currency: string;
	created: number;
};

const parseStripeCharge = (value: unknown): StripeCharge | undefined => {
	if (!isRecord(value) || value.livemode !== true || value.paid !== true) {
		return undefined;
	}

	const id = asString(value.id);
	const amount = asNonNegativeInteger(value.amount);
	const amountRefunded = asNonNegativeInteger(value.amount_refunded) ?? 0;
	const currency = asString(value.currency)?.toUpperCase();
	const created = asNonNegativeInteger(value.created);

	return id && amount !== undefined && currency && created !== undefined
		? { id, amount, amountRefunded, currency, created }
		: undefined;
};

const fetchStripeCharges = async (
	secretKey: string,
	startingAfter?: string,
	page = 0,
): Promise<StripeCharge[]> => {
	if (page >= 50) {
		throw new Error("Stripe account has more than 5,000 charges; use STRIPE_REVENUE_URL");
	}

	const query = new URLSearchParams({ limit: "100" });
	if (startingAfter) query.set("starting_after", startingAfter);
	const response = await fetch(`https://api.stripe.com/v1/charges?${query}`, {
		headers: { Authorization: `Bearer ${secretKey}` },
		cache: "no-store",
		signal: AbortSignal.timeout(dashboardConfig.requestTimeoutMs),
	});

	if (!response.ok) throw new Error(`Stripe returned HTTP ${response.status}`);
	const payload = (await response.json()) as unknown;
	if (!isRecord(payload) || !Array.isArray(payload.data)) {
		throw new Error("Stripe returned an invalid charge list");
	}

	const charges = payload.data
		.map(parseStripeCharge)
		.filter((charge): charge is StripeCharge => charge !== undefined);
	const lastId = charges.at(-1)?.id;
	return payload.has_more === true && lastId
		? [
				...charges,
				...(await fetchStripeCharges(secretKey, lastId, page + 1)),
			]
		: charges;
};

const getDirectStripeRevenue = async (secretKey: string) => {
	if (!secretKey.startsWith("sk_live_") && !secretKey.startsWith("rk_live_")) {
		return pendingRevenue("Test-mode Stripe data is not counted as real revenue");
	}

	const charges = (await fetchStripeCharges(secretKey)).filter(
		(charge) => charge.amount > charge.amountRefunded,
	);
	if (charges.length === 0) {
		return pendingRevenue(
			"Live Stripe connected; no successful net-positive payments yet",
		);
	}

	const currencies = [...new Set(charges.map((charge) => charge.currency))];
	if (currencies.length > 1) {
		throw new Error("Multiple Stripe currencies require a normalized revenue endpoint");
	}

	const amountMinor = charges.reduce(
		(total, charge) => total + Math.max(0, charge.amount - charge.amountRefunded),
		0,
	);
	const updatedAt = charges[0]
		? new Date(charges[0].created * 1_000).toISOString()
		: new Date().toISOString();

	return {
		meta: integrationMeta(
			"live",
			"Read server-side from live-mode Stripe charges",
			updatedAt,
		),
		data: {
			amountMinor,
			currency: currencies[0] ?? "USD",
			orders: charges.length,
			statusText: "Live Stripe revenue",
		},
	} satisfies PanelState<RevenueData>;
};

export const getStripeRevenue = async (): Promise<PanelState<RevenueData>> => {
	const { revenueUrl, revenueToken, secretKey } = dashboardConfig.stripe;
	if (!revenueUrl && !secretKey) {
		return pendingRevenue("Waiting for live Stripe revenue");
	}

	try {
		if (revenueUrl) {
			return parseRevenueEndpoint(
				await fetchJson(revenueUrl, { token: revenueToken }),
			);
		}
		return await getDirectStripeRevenue(secretKey as string);
	} catch (error) {
		return {
			...pendingRevenue("Waiting for live Stripe revenue"),
			meta: integrationMeta("error", getErrorMessage(error)),
		};
	}
};
