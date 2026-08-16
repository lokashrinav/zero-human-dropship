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
import { verifiedExternalRevenue } from "./verified-revenue";

const pendingRevenue = (detail: string): PanelState<RevenueData> => ({
	meta: integrationMeta("pending", detail),
	data: {
		amountMinor: null,
		currency: "USD",
		orders: null,
		statusText: "Waiting for live Stripe revenue",
	},
});

const liveRevenue = (
	amountMinor: number,
	orders: number,
	currency: string,
	updatedAt: string,
	detail: string,
): PanelState<RevenueData> => ({
	meta: integrationMeta("live", detail, updatedAt),
	data: {
		amountMinor,
		currency,
		orders,
		statusText:
			amountMinor > 0 ? "Verified genuine Stripe revenue" : "No live Stripe revenue yet",
	},
});

const parseRevenueEndpoint = (
	payload: unknown,
	revenueUrl: string,
): PanelState<RevenueData> => {
	if (!isRecord(payload)) throw new Error("Revenue response must be an object");
	if (payload.source === "stripe" && payload.livemode === true) {
		const amountMinor = asNonNegativeInteger(payload.amountMinor);
		const orders = asNonNegativeInteger(payload.orders);
		const currency = asString(payload.currency)?.toUpperCase();
		const updatedAt = asIsoDate(payload.updatedAt);
		if (amountMinor === undefined || orders === undefined || !currency || !updatedAt) {
			throw new Error("Revenue endpoint response does not match its contract");
		}
		return liveRevenue(
			amountMinor,
			orders,
			currency,
			updatedAt,
			"Verified live-mode Stripe data",
		);
	}

	let endpoint: URL;
	try {
		endpoint = new URL(revenueUrl);
	} catch {
		throw new Error("Revenue endpoint URL is invalid");
	}
	if (endpoint.protocol !== "https:" || endpoint.pathname !== "/api/stats") {
		throw new Error("Revenue endpoint did not attest to live Stripe data");
	}
	if (asString(payload.error)) {
		throw new Error("Person A Stripe stats endpoint reported an error");
	}

	const amountMinor = asNonNegativeInteger(payload.gross_revenue_cents);
	const orders = asNonNegativeInteger(payload.orders);
	const charges = Array.isArray(payload.charges) ? payload.charges : undefined;
	if (amountMinor === undefined || orders === undefined || !charges) {
		throw new Error("Person A Stripe stats response does not match its contract");
	}
	const chargeTimes = charges.flatMap((charge) => {
		if (!isRecord(charge)) return [];
		const amount = asNonNegativeInteger(charge.amount_cents);
		const created = asNonNegativeInteger(charge.created);
		return amount !== undefined && created !== undefined ? [{ amount, created }] : [];
	});
	if ((amountMinor > 0 || orders > 0) && !chargeTimes.some((charge) => charge.amount > 0)) {
		throw new Error("Person A Stripe stats did not include a successful charge");
	}
	if ((amountMinor === 0) !== (orders === 0)) {
		throw new Error("Person A Stripe stats returned inconsistent totals");
	}
	const newestCharge = chargeTimes.sort((left, right) => right.created - left.created)[0];
	return liveRevenue(
		amountMinor,
		orders,
		"USD",
		newestCharge ? new Date(newestCharge.created * 1_000).toISOString() : new Date().toISOString(),
		"Read server-side from Person A live Stripe stats",
	);
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
		return liveRevenue(
			0,
			0,
			"USD",
			new Date().toISOString(),
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

	return liveRevenue(
		amountMinor,
		charges.length,
		currencies[0] ?? "USD",
		updatedAt,
		"Read server-side from live-mode Stripe charges",
	);
};

export const getStripeRevenue = async (): Promise<PanelState<RevenueData>> => {
	const { revenueUrl, revenueToken, secretKey } = dashboardConfig.stripe;
	if (!revenueUrl && !secretKey) {
		return liveRevenue(
			verifiedExternalRevenue.amountMinor,
			verifiedExternalRevenue.orders,
			verifiedExternalRevenue.currency,
			verifiedExternalRevenue.verifiedAt,
			"Verified genuine-customer Stripe snapshot; documented self-tests excluded",
		);
	}

	try {
		if (revenueUrl) {
			return parseRevenueEndpoint(
				await fetchJson(revenueUrl, { token: revenueToken }),
				revenueUrl,
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
