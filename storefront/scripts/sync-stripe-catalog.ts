import { writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const STRIPE_API_VERSION = "2026-06-24.dahlia";
const DEFAULT_SHIPPING_COUNTRIES = ["US"] as const;
const applyChanges = process.argv.includes("--apply");
const secretKey = process.env.STRIPE_SECRET_KEY;

if (!secretKey) {
	throw new Error("Missing STRIPE_SECRET_KEY. Store it in ignored .env.local before running this script.");
}

if (!secretKey.startsWith("sk_live_") && !secretKey.startsWith("rk_live_")) {
	throw new Error("STRIPE_SECRET_KEY must be a live-mode key.");
}

type StripeList<T> = { data: T[]; has_more: boolean };
type StripeProduct = {
	id: string;
	active: boolean;
	created: number;
	default_price: string | null;
	description: string | null;
	images: string[];
	livemode: boolean;
	metadata: Record<string, string>;
	name: string;
};
type StripePrice = {
	id: string;
	active: boolean;
	created: number;
	currency: string;
	livemode: boolean;
	product: string;
	recurring: unknown | null;
	type: "one_time" | "recurring";
	unit_amount: number | null;
};
type StripePaymentLink = {
	id: string;
	active: boolean;
	livemode: boolean;
	shipping_address_collection: { allowed_countries: string[] } | null;
	url: string;
};
type StripeLineItem = {
	price: { id: string; product: string };
	quantity: number | null;
};

const stripeRequest = async <T>(
	path: string,
	options?: { body?: URLSearchParams; method?: "GET" | "POST" },
) => {
	const response = await fetch(`https://api.stripe.com${path}`, {
		method: options?.method ?? "GET",
		headers: {
			Authorization: `Bearer ${secretKey}`,
			"Stripe-Version": STRIPE_API_VERSION,
			...(options?.body ? { "Content-Type": "application/x-www-form-urlencoded" } : {}),
		},
		body: options?.body,
	});

	if (!response.ok) {
		const requestId = response.headers.get("request-id") ?? "unknown";
		throw new Error(`Stripe API request failed (${response.status}, request ${requestId}).`);
	}

	return (await response.json()) as T;
};

const listAll = async <T>(path: string, params: Record<string, string>) => {
	const results: T[] = [];
	let startingAfter: string | undefined;

	do {
		const search = new URLSearchParams({ ...params, limit: "100" });
		if (startingAfter) search.set("starting_after", startingAfter);
		const page = await stripeRequest<StripeList<T>>(`${path}?${search.toString()}`);
		results.push(...page.data);
		startingAfter = page.has_more
			? ((page.data.at(-1) as { id?: string } | undefined)?.id ?? undefined)
			: undefined;
		if (page.has_more && !startingAfter) throw new Error(`Stripe pagination failed for ${path}.`);
	} while (startingAfter);

	return results;
};

const products = await listAll<StripeProduct>("/v1/products", { active: "true" });
const prices = await listAll<StripePrice>("/v1/prices", { active: "true", type: "one_time" });
const paymentLinks = await listAll<StripePaymentLink>("/v1/payment_links", { active: "true" });

if (products.some((product) => !product.livemode) || prices.some((price) => !price.livemode)) {
	throw new Error("Stripe returned non-live catalog objects while using a live key.");
}

const linkDetails = await Promise.all(
	paymentLinks.map(async (link) => ({
		link,
		lineItems: (
			await stripeRequest<StripeList<StripeLineItem>>(`/v1/payment_links/${link.id}/line_items?limit=100`)
		).data,
	})),
);

const priceForProduct = (product: StripeProduct) => {
	const candidates = prices
		.filter(
			(price) =>
				price.product === product.id &&
				price.active &&
				price.type === "one_time" &&
				price.recurring === null &&
				price.unit_amount !== null,
		)
		.sort((a, b) => b.created - a.created);
	return candidates.find((price) => price.id === product.default_price) ?? candidates[0] ?? null;
};

const exactLinkForPrice = (priceId: string) =>
	linkDetails.find(
		({ link, lineItems }) =>
			link.active &&
			lineItems.length === 1 &&
			lineItems[0]?.price.id === priceId &&
			lineItems[0].quantity === 1,
	) ?? null;

const ensureShipping = async (link: StripePaymentLink) => {
	const currentCountries = link.shipping_address_collection?.allowed_countries ?? [];
	if (currentCountries.length > 0) return link;
	if (!applyChanges) return link;

	const body = new URLSearchParams();
	DEFAULT_SHIPPING_COUNTRIES.map((country, index) =>
		body.set(`shipping_address_collection[allowed_countries][${index}]`, country),
	);
	return stripeRequest<StripePaymentLink>(`/v1/payment_links/${link.id}`, { body, method: "POST" });
};

const createPaymentLink = async (product: StripeProduct, price: StripePrice) => {
	if (!applyChanges) return null;
	const body = new URLSearchParams({
		"line_items[0][price]": price.id,
		"line_items[0][quantity]": "1",
		"metadata[kova_catalog_product]": product.id,
		"metadata[kova_catalog_price]": price.id,
		submit_type: "pay",
	});
	DEFAULT_SHIPPING_COUNTRIES.map((country, index) =>
		body.set(`shipping_address_collection[allowed_countries][${index}]`, country),
	);
	return stripeRequest<StripePaymentLink>("/v1/payment_links", { body, method: "POST" });
};

const planned = products.map((product) => {
	const price = priceForProduct(product);
	const existing = price ? exactLinkForPrice(price.id) : null;
	return {
		product,
		price,
		existing,
		action: !price
			? "blocked:no-active-one-time-price"
			: !existing
				? "create-payment-link"
				: existing.link.shipping_address_collection?.allowed_countries.length
					? "reuse-verified-link"
					: "update-link-shipping",
	};
});

console.log(
	JSON.stringify(
		{
			mode: applyChanges ? "apply" : "dry-run",
			activeProducts: products.length,
			activeOneTimePrices: prices.length,
			activePaymentLinks: paymentLinks.length,
			plans: planned.map(({ product, price, existing, action }) => ({
				productId: product.id,
				productName: product.name,
				priceId: price?.id ?? null,
				currency: price?.currency ?? null,
				unitAmount: price?.unit_amount ?? null,
				paymentLinkId: existing?.link.id ?? null,
				shippingCountries: existing?.link.shipping_address_collection?.allowed_countries ?? [],
				action,
			})),
		},
		null,
		2,
	),
);

if (!applyChanges) process.exit(0);

const blocked = planned.filter(({ price }) => !price);
if (blocked.length > 0) {
	throw new Error(
		`${blocked.length} active Stripe product(s) have no active one-time price; catalog not written.`,
	);
}

const catalog = await Promise.all(
	planned.map(async ({ product, price, existing }) => {
		if (!price) throw new Error(`Missing price for ${product.id}.`);
		if (price.currency !== "usd")
			throw new Error(`Unsupported non-USD price ${price.id}; catalog not written.`);
		const paymentLink = existing
			? await ensureShipping(existing.link)
			: await createPaymentLink(product, price);
		if (!paymentLink) throw new Error(`Payment Link was not created for ${product.id}.`);
		const shippingCountries = paymentLink.shipping_address_collection?.allowed_countries ?? [];
		if (shippingCountries.length === 0)
			throw new Error(`Payment Link ${paymentLink.id} does not collect shipping.`);

		return {
			id: product.id,
			name: product.name,
			images: product.images,
			image_kind: product.metadata.image_kind === "visualization" ? "visualization" : "source",
			stripe_id: product.id,
			payment_link: paymentLink.url,
			price: (price.unit_amount ?? 0) / 100,
			description: product.description ?? "",
			active: product.active,
		};
	}),
);

await writeFile(
	resolve(import.meta.dir, "../catalog.json"),
	`${JSON.stringify(catalog, null, "\t")}\n`,
	"utf8",
);

console.log(
	JSON.stringify(
		{
			catalogWritten: true,
			products: catalog.length,
			paymentLinksVerified: catalog.length,
			shippingCountries: DEFAULT_SHIPPING_COUNTRIES,
		},
		null,
		2,
	),
);
