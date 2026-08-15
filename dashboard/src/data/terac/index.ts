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
import type {
	BusinessStateItem,
	PanelState,
	TeracChange,
	TeracData,
	TeracStudy,
} from "../contracts";
import { fetchJson } from "../http";

const changeTypes = new Set<TeracChange["type"]>([
	"removed",
	"replaced",
	"price",
	"copy",
	"other",
]);

const parseBusinessItem = (value: unknown): BusinessStateItem | undefined => {
	if (!isRecord(value)) return undefined;
	const id = asString(value.id);
	const name = asString(value.name);
	if (!id || !name) return undefined;

	const priceMinor = asNonNegativeInteger(value.priceMinor);
	const currency = asString(value.currency)?.toUpperCase();
	const copy = asString(value.copy);
	const active = asBoolean(value.active);
	return {
		id,
		name,
		...(priceMinor !== undefined ? { priceMinor } : {}),
		...(currency ? { currency } : {}),
		...(copy ? { copy } : {}),
		...(active !== undefined ? { active } : {}),
	};
};

const parseItems = (value: unknown) =>
	(asArray(value) ?? [])
		.map(parseBusinessItem)
		.filter((item): item is BusinessStateItem => item !== undefined);

const parseChange = (value: unknown): TeracChange | undefined => {
	if (!isRecord(value)) return undefined;
	const description = asString(value.description);
	const rawType = asString(value.type) as TeracChange["type"] | undefined;
	if (!description) return undefined;
	return {
		type: rawType && changeTypes.has(rawType) ? rawType : "other",
		description,
	};
};

const parseStudy = (value: unknown): TeracStudy | undefined => {
	if (!isRecord(value)) return undefined;
	const before = isRecord(value.before) ? value.before : undefined;
	const feedback = isRecord(value.feedback) ? value.feedback : undefined;
	const after = isRecord(value.after) ? value.after : undefined;
	const id = asString(value.id);
	const title = asString(value.title);
	const capturedAt = asIsoDate(value.capturedAt);
	const beforeSummary = asString(before?.summary);
	const feedbackResult = asString(feedback?.result);
	const sampleSize = asNonNegativeInteger(feedback?.sampleSize);
	const afterSummary = asString(after?.summary);

	if (
		!id ||
		!title ||
		!capturedAt ||
		!beforeSummary ||
		!feedbackResult ||
		sampleSize === undefined ||
		!afterSummary
	) {
		return undefined;
	}

	const rating = asNumber(feedback?.rating);
	const ratingScale = asNumber(feedback?.ratingScale);
	return {
		id,
		title,
		capturedAt,
		before: {
			summary: beforeSummary,
			items: parseItems(before?.items),
		},
		feedback: {
			sampleSize,
			result: feedbackResult,
			...(rating !== undefined ? { rating } : {}),
			...(ratingScale !== undefined ? { ratingScale } : {}),
		},
		changes: (asArray(value.changes) ?? [])
			.map(parseChange)
			.filter((change): change is TeracChange => change !== undefined),
		after: {
			summary: afterSummary,
			items: parseItems(after?.items),
		},
	};
};

const parseTerac = (payload: unknown) => {
	const values = isRecord(payload) ? asArray(payload.studies) : asArray(payload);
	if (!values) throw new Error("Terac response does not match its contract");

	const studies = values
		.map(parseStudy)
		.filter((study): study is TeracStudy => study !== undefined)
		.sort(
			(left, right) =>
				Date.parse(right.capturedAt) - Date.parse(left.capturedAt),
		);
	const updatedAt =
		(isRecord(payload) ? asIsoDate(payload.updatedAt) : undefined) ??
		studies[0]?.capturedAt;
	return { studies, updatedAt };
};

export const getTeracData = async (): Promise<PanelState<TeracData>> => {
	const { url, token } = dashboardConfig.terac;
	if (!url) {
		return {
			meta: integrationMeta(
				"pending",
				"Waiting for the real Terac MCP study result",
			),
			data: { studies: [] },
		};
	}

	try {
		const { studies, updatedAt } = parseTerac(
			await fetchJson(url, { token }),
		);
		return {
			meta: integrationMeta("live", "Connected to Terac feedback", updatedAt),
			data: { studies },
		};
	} catch (error) {
		return {
			meta: integrationMeta(
				"error",
				`Configured Terac result unavailable. ${getErrorMessage(error)}`,
			),
			data: { studies: [] },
		};
	}
};
