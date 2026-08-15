import type { DataMode, IntegrationMeta } from "./contracts";

export const isRecord = (value: unknown): value is Record<string, unknown> =>
	typeof value === "object" && value !== null && !Array.isArray(value);

export const asString = (value: unknown) =>
	typeof value === "string" && value.trim() ? value.trim() : undefined;

export const asNumber = (value: unknown) => {
	const number = typeof value === "number" ? value : Number.NaN;
	return Number.isFinite(number) ? number : undefined;
};

export const asNonNegativeInteger = (value: unknown) => {
	const number = asNumber(value);
	return number !== undefined && number >= 0 ? Math.floor(number) : undefined;
};

export const asBoolean = (value: unknown) =>
	typeof value === "boolean" ? value : undefined;

export const asIsoDate = (value: unknown) => {
	const dateString = asString(value);
	if (!dateString) return undefined;
	const milliseconds = Date.parse(dateString);
	return Number.isNaN(milliseconds)
		? undefined
		: new Date(milliseconds).toISOString();
};

export const asArray = (value: unknown) =>
	Array.isArray(value) ? value : undefined;

export const getErrorMessage = (error: unknown) =>
	error instanceof Error ? error.message : "Unexpected integration error";

const labelForMode = (mode: DataMode): IntegrationMeta["label"] => {
	if (mode === "live") return "LIVE";
	if (mode === "demo") return "DEMO DATA";
	if (mode === "error") return "DEGRADED";
	return "WAITING";
};

export const integrationMeta = (
	mode: DataMode,
	detail?: string,
	updatedAt?: string,
	fallback?: "demo",
): IntegrationMeta => ({
	mode,
	label: labelForMode(mode),
	fetchedAt: new Date().toISOString(),
	...(updatedAt ? { updatedAt } : {}),
	...(detail ? { detail } : {}),
	...(fallback ? { fallback } : {}),
});

export const joinUrl = (baseUrl: string, path: string) =>
	`${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
