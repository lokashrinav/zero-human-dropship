import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import {
	asArray,
	asBoolean,
	asIsoDate,
	asNonNegativeInteger,
	asNumber,
	asString,
	getErrorMessage,
	integrationMeta,
	isRecord,
} from "../common";
import { dashboardConfig } from "../config";
import type { CatalogData, CatalogProduct, PanelState } from "../contracts";
import { fetchJson } from "../http";

const emptyCatalog: CatalogData = {
	products: [],
	productCount: 0,
	activeCount: 0,
	promotedProducts: [],
};

const legacyPriceMinor = (value: Record<string, unknown>) => {
	const cents = asNonNegativeInteger(value.price_cents);
	if (cents !== undefined) return cents;
	const dollars = asNumber(value.price);
	return dollars !== undefined && dollars >= 0 ? Math.round(dollars * 100) : undefined;
};

const parseProduct = (
	value: unknown,
	index: number,
): CatalogProduct | undefined => {
	if (!isRecord(value)) return undefined;
	const id =
		asString(value.id) ??
		asString(value.stripe_id) ??
		asString(value.product_id);
	const name = asString(value.name);
	const priceMinor =
		value.priceMinor === null
			? null
			: (asNonNegativeInteger(value.priceMinor) ?? legacyPriceMinor(value) ?? null);
	const currency = asString(value.currency)?.toUpperCase() ?? "USD";
	const source =
		asString(value.source) ??
		(asString(value.cj_product_id) ? "CJ" : "Person A catalog");
	const active = asBoolean(value.active) ?? true;
	const promoted = asBoolean(value.promoted) ?? (active && index < 3);

	if (
		!id ||
		!name ||
		!currency ||
		!source ||
		active === undefined ||
		promoted === undefined
	) {
		return undefined;
	}

	const url =
		asString(value.url) ??
		asString(value.payment_link) ??
		asString(value.payment_link_url);
	const images = asArray(value.images);
	const imageUrl =
		asString(value.imageUrl) ?? (images ? asString(images[0]) : undefined);
	return {
		id,
		name,
		priceMinor,
		currency,
		source,
		active,
		promoted,
		...(url ? { url } : {}),
		...(imageUrl ? { imageUrl } : {}),
	};
};

const parseCatalog = (payload: unknown) => {
	const values = isRecord(payload) ? asArray(payload.products) : asArray(payload);
	if (!values) throw new Error("Catalog response does not match its contract");
	const products = values
		.map(parseProduct)
		.filter((product): product is CatalogProduct => product !== undefined);

	return {
		data: {
			products,
			productCount: products.length,
			activeCount: products.filter((product) => product.active).length,
			promotedProducts: products.filter(
				(product) => product.active && product.promoted,
			),
		} satisfies CatalogData,
		updatedAt: isRecord(payload) ? asIsoDate(payload.updatedAt) : undefined,
	};
};

const readCatalogFile = async (jsonPath: string) => {
	const resolvedPath = path.isAbsolute(jsonPath)
		? jsonPath
		: path.resolve(/* turbopackIgnore: true */ process.cwd(), jsonPath);
	const [contents, fileStats] = await Promise.all([
		readFile(resolvedPath, "utf8"),
		stat(resolvedPath),
	]);
	const payload: unknown = JSON.parse(contents);
	const catalog = parseCatalog(payload);
	return {
		...catalog,
		updatedAt: catalog.updatedAt ?? fileStats.mtime.toISOString(),
	};
};

export const getCatalogData = async (): Promise<PanelState<CatalogData>> => {
	const { url, token, jsonPath } = dashboardConfig.catalog;
	if (!url && !jsonPath) {
		return {
			meta: integrationMeta("pending", "Waiting for a verified catalog source"),
			data: emptyCatalog,
		};
	}

	try {
		const { data, updatedAt } = url
			? parseCatalog(await fetchJson(url, { token }))
			: await readCatalogFile(jsonPath as string);
		return {
			meta: integrationMeta(
				"live",
				url ? "Connected to catalog endpoint" : "Reading configured catalog.json",
				updatedAt,
			),
			data,
		};
	} catch (error) {
		return {
			meta: integrationMeta(
				"error",
				`Verified catalog source unavailable. ${getErrorMessage(error)}`,
			),
			data: emptyCatalog,
		};
	}
};
