import type {
	APIProductGetByIdResult,
	APIProductsBrowseQueryParams,
	APIProductsBrowseResult,
} from "commerce-kit";
import catalogJson from "@/catalog.json";
import { orderProductsByIdRanking } from "@/lib/product-ranking";
import teracRanking from "@/terac-ranking.json";

export type CatalogEntry = {
	id: string;
	name: string;
	slug: string;
	summary: string;
	description: string;
	images: string[];
	image_kind: "source" | "visualization";
	stripe_id: string | null;
	payment_link: string | null;
	cost?: number;
	price: number;
	active: boolean;
	mode: "development" | "live";
};

type RawCatalogEntry = Omit<
	CatalogEntry,
	"id" | "slug" | "summary" | "description" | "active" | "mode" | "image_kind"
> & {
	id?: string;
	slug?: string;
	summary?: string;
	description?: string;
	active?: boolean;
	mode?: CatalogEntry["mode"];
	image_kind?: unknown;
};

export type CatalogProduct = NonNullable<APIProductGetByIdResult> & {
	catalogMode: CatalogEntry["mode"];
	paymentLink: string | null;
	imageKind: CatalogEntry["image_kind"];
};

const isStripePaymentLink = (value: string | null) => {
	if (!value) return false;
	try {
		const url = new URL(value);
		return url.protocol === "https:" && url.hostname === "buy.stripe.com";
	} catch {
		return false;
	}
};

const slugify = (value: string) =>
	value
		.toLowerCase()
		.replace(/^development product\s*[—-]\s*/i, "")
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/(^-|-$)/g, "");

const normalizeEntry = (entry: RawCatalogEntry): CatalogEntry => ({
	...entry,
	id: entry.id ?? entry.stripe_id ?? slugify(entry.name),
	slug: entry.slug?.trim() || slugify(entry.name),
	summary:
		entry.summary?.trim() ||
		entry.description?.trim() ||
		"Product details and fulfillment terms are confirmed before purchase.",
	description: entry.description?.trim() || entry.summary?.trim() || "",
	image_kind: entry.image_kind === "visualization" ? "visualization" : "source",
	active: entry.active ?? true,
	mode:
		(entry.mode === "live" || entry.active === true) &&
		entry.stripe_id?.startsWith("prod_") &&
		isStripePaymentLink(entry.payment_link)
			? "live"
			: "development",
	payment_link: isStripePaymentLink(entry.payment_link) ? entry.payment_link : null,
});

export const catalog = orderProductsByIdRanking(
	(catalogJson as RawCatalogEntry[]).map(normalizeEntry).filter((entry) => entry.active),
	teracRanking.productIds,
);

const toCommerceProduct = (entry: CatalogEntry, index: number) => {
	const now = "2026-08-15T00:00:00.000Z";
	const id = entry.id || `catalog-${index + 1}`;
	const variantId = `${id}-default`;
	return {
		id,
		name: entry.name,
		createdAt: now,
		updatedAt: now,
		type: "product",
		slug: entry.slug,
		status: "published",
		flags: null,
		storeId: "local-catalog",
		summary: entry.summary,
		content: null,
		images: entry.images,
		badge: entry.mode === "development" ? "DEVELOPMENT" : null,
		bundleDiscountPercentage: null,
		bundlePriceMode: "fixed",
		bundleFixedPriceAmount: null,
		bundleAmountOffAmount: null,
		seo: null,
		stripeTaxCode: null,
		categoryId: null,
		brandId: null,
		category: null,
		productTaxRate: null,
		productCollections: [],
		bundleGroups: [],
		bundleProducts: [],
		tr: [],
		variants: [
			{
				id: variantId,
				createdAt: now,
				updatedAt: now,
				storeId: "local-catalog",
				description: entry.summary,
				price: String(Math.round(entry.price * 100)),
				images: entry.images,
				sku: null,
				barcode: null,
				calculatedPrice: null,
				stock: entry.mode === "live" ? null : 0,
				depth: null,
				width: null,
				height: null,
				weight: null,
				digital: null,
				shippable: true,
				externalId: entry.stripe_id,
				productId: id,
				attributes: null,
				originalPrice: String(Math.round(entry.price * 100)),
				combinations: [],
				prices: [],
			},
		],
		subscriptionPlanProducts: [],
		volumePricingTiers: [],
		catalogMode: entry.mode,
		paymentLink: entry.payment_link,
		imageKind: entry.image_kind,
	} as unknown as CatalogProduct;
};

export const catalogProducts = catalog.map(toCommerceProduct);

export const browseCatalog = (params: APIProductsBrowseQueryParams = {}): APIProductsBrowseResult => {
	const offset = params.offset ?? 0;
	const limit = params.limit ?? catalogProducts.length;
	let products = [...catalogProducts];
	if (params.query) {
		const query = params.query.toLowerCase();
		products = products.filter((product) =>
			`${product.name} ${product.summary ?? ""}`.toLowerCase().includes(query),
		);
	}
	if (params.orderBy === "name") {
		products.sort((a, b) => a.name.localeCompare(b.name));
	}
	if (params.orderBy === "price") {
		products.sort((a, b) => Number(a.variants[0]?.price ?? 0) - Number(b.variants[0]?.price ?? 0));
	}
	if (params.orderDirection === "desc") products.reverse();
	return {
		data: products.slice(offset, offset + limit),
		meta: {
			count: products.length,
			countPublished: products.length,
			countDraft: 0,
			countHidden: 0,
			nextCursor: undefined,
		},
	} as unknown as APIProductsBrowseResult;
};

export const getCatalogProduct = (idOrSlug: string) =>
	catalogProducts.find((product) => product.id === idOrSlug || product.slug === idOrSlug) ?? null;

export const getCatalogPurchase = (product: unknown) => {
	if (!product || typeof product !== "object" || !("catalogMode" in product)) return null;
	const catalogMode = product.catalogMode === "live" ? "live" : "development";
	const paymentLink =
		"paymentLink" in product && typeof product.paymentLink === "string" ? product.paymentLink : null;
	const imageKind =
		"imageKind" in product && product.imageKind === "visualization" ? "visualization" : "source";
	return { catalogMode, paymentLink, imageKind } as const;
};

export const getCatalogStatus = () => ({
	count: catalog.length,
	liveCount: catalog.filter((entry) => entry.mode === "live").length,
	mode: catalog.some((entry) => entry.mode === "live") ? "catalog" : "development",
});
