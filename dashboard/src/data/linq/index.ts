import {
	asArray,
	asBoolean,
	asIsoDate,
	asNonNegativeInteger,
	asString,
	getErrorMessage,
	integrationMeta,
	isRecord,
	joinUrl,
} from "../common";
import { dashboardConfig } from "../config";
import type {
	AutonomousLoopStage,
	LinqData,
	LinqEvent,
	LinqEventType,
	PanelState,
} from "../contracts";
import { fetchJson } from "../http";

const VERIFIED_LINQ_PHONE = "+1 415-305-0091";

const eventTypes = new Set<LinqEventType>([
	"inbound_message",
	"sales_agent",
	"product_selected",
	"recommendation",
	"payment_link_sent",
	"payment_completed",
	"order_fulfilled",
	"feedback_received",
	"other",
]);

const stages = new Set<AutonomousLoopStage>([
	"source",
	"validate",
	"list",
	"sell",
	"fulfill",
	"learn",
]);

const eventTypeAliases: Record<string, LinqEventType> = {
	inbound_message: "inbound_message",
	intent_detected: "sales_agent",
	product_selected: "product_selected",
	product_recommended: "recommendation",
	checkout_link_sent: "payment_link_sent",
	customer_response: "inbound_message",
	conversion: "payment_completed",
};

const stageForEvent = (type: LinqEventType): AutonomousLoopStage => {
	if (type === "product_selected" || type === "recommendation") return "list";
	if (type === "payment_completed" || type === "order_fulfilled") return "fulfill";
	if (type === "feedback_received") return "learn";
	return "sell";
};

const directionForEvent = (type: LinqEventType): LinqEvent["direction"] => {
	if (type === "inbound_message" || type === "feedback_received") return "inbound";
	if (type === "payment_link_sent" || type === "recommendation") return "outbound";
	return "internal";
};

const headlineForEvent = (type: LinqEventType) =>
	type.replaceAll("_", " ").toUpperCase();

const stageForRawEvent = (
	rawType: string | undefined,
	type: LinqEventType,
): AutonomousLoopStage => {
	if (rawType?.startsWith("band_review_")) return "validate";
	if (rawType === "product_considered") return "source";
	if (rawType === "catalog_reloaded" || rawType === "catalog_reload_failed") {
		return "source";
	}
	return stageForEvent(type);
};

const detailForEvent = (value: Record<string, unknown>) => {
	const explicit = asString(value.detail);
	if (explicit) return explicit;
	const data = isRecord(value.data) ? value.data : undefined;
	return (
		asString(data?.name) ??
		asString(data?.reason) ??
		asString(data?.primary_product_id) ??
		asString(data?.product_id) ??
		asString(value.source)
	);
};

const parseEvent = (value: unknown): LinqEvent | undefined => {
	if (!isRecord(value)) return undefined;
	const id = asString(value.id) ?? asString(value.event_id);
	const timestamp = asIsoDate(value.timestamp) ?? asIsoDate(value.occurred_at);
	const rawType = asString(value.type);
	const aliasedType = rawType ? eventTypeAliases[rawType] : undefined;
	const type =
		aliasedType ??
		(rawType && eventTypes.has(rawType as LinqEventType)
			? (rawType as LinqEventType)
			: "other");
	const rawStage = asString(value.stage) as AutonomousLoopStage | undefined;
	const stage =
		rawStage && stages.has(rawStage) ? rawStage : stageForRawEvent(rawType, type);
	const rawDirection = asString(value.direction);
	const direction =
		rawDirection === "inbound" ||
		rawDirection === "internal" ||
		rawDirection === "outbound"
			? rawDirection
			: directionForEvent(type);

	if (!id || !timestamp) return undefined;
	return {
		id,
		timestamp,
		type,
		stage,
		headline:
			asString(value.headline) ??
			(rawType ? rawType.replaceAll("_", " ").toUpperCase() : headlineForEvent(type)),
		...(detailForEvent(value) ? { detail: detailForEvent(value) } : {}),
		direction,
	};
};

const parseStatus = (payload: unknown) => {
	if (!isRecord(payload)) throw new Error("Linq status must be an object");
	const status = isRecord(payload.status) ? payload.status : payload;
	const online = asBoolean(status.online);
	const conversations = asNonNegativeInteger(status.conversations);
	const recommendations = asNonNegativeInteger(status.recommendations);
	const paymentLinksSent = asNonNegativeInteger(status.paymentLinksSent);
	const updatedAt = asIsoDate(status.updatedAt);
	const phone = isRecord(status.phoneNumber) ? status.phoneNumber : undefined;
	const rawPhoneNumber = phone?.public === true ? asString(phone.display) : undefined;
	const phoneDigits = rawPhoneNumber?.replace(/\D/g, "");
	const phoneNumber =
		phoneDigits?.length === 11 && phoneDigits.startsWith("1")
			? `+1 ${phoneDigits.slice(1, 4)}-${phoneDigits.slice(4, 7)}-${phoneDigits.slice(7)}`
			: (rawPhoneNumber ?? null);

	if (
		online === undefined ||
		conversations === undefined ||
		recommendations === undefined ||
		paymentLinksSent === undefined ||
		!updatedAt
	) {
		throw new Error("Linq status response does not match its contract");
	}

	return {
		online,
		phoneNumber,
		conversations,
		recommendations,
		paymentLinksSent,
		updatedAt,
	};
};

const parseEvents = (payload: unknown) => {
	const values = isRecord(payload) ? asArray(payload.events) : asArray(payload);
	if (!values) throw new Error("Linq events response does not match its contract");

	const events = values
		.map(parseEvent)
		.filter((event): event is LinqEvent => event !== undefined)
		.sort(
			(left, right) =>
				Date.parse(right.timestamp) - Date.parse(left.timestamp),
		);

	return [...new Map(events.map((event) => [event.id, event])).values()];
};

const emptyState = (
	mode: "pending" | "error",
	detail: string,
): PanelState<LinqData> => ({
	meta: integrationMeta(mode, detail),
	data: {
		online: null,
		phoneNumber: VERIFIED_LINQ_PHONE,
		conversations: 0,
		recommendations: 0,
		paymentLinksSent: 0,
		events: [],
	},
});

export const getLinqData = async (): Promise<PanelState<LinqData>> => {
	const { baseUrl, statusUrl, eventsUrl, token } = dashboardConfig.linq;
	const resolvedStatusUrl = statusUrl ?? (baseUrl ? joinUrl(baseUrl, "/api/status") : undefined);
	const resolvedEventsUrl =
		eventsUrl ??
		(baseUrl ? joinUrl(baseUrl, "/api/events?cursor=0&limit=100") : undefined);

	if (!resolvedStatusUrl && !resolvedEventsUrl) {
		return emptyState(
			"pending",
			"Real Linq account verified; public deployment and webhook are pending",
		);
	}

	try {
		const [statusPayload, eventsPayload] = await Promise.all([
			resolvedStatusUrl
				? fetchJson(resolvedStatusUrl, { token })
				: Promise.resolve(undefined),
			resolvedEventsUrl
				? fetchJson(resolvedEventsUrl, { token })
				: Promise.resolve(undefined),
		]);
		const status = statusPayload
			? parseStatus(statusPayload)
			: {
					online: null,
					phoneNumber: null,
					conversations: 0,
					recommendations: 0,
					paymentLinksSent: 0,
					updatedAt: undefined,
				};
		const events = eventsPayload ? parseEvents(eventsPayload) : [];
		const latestEventAt = events[0]?.timestamp;
		const updatedAt = [status.updatedAt, latestEventAt]
			.filter((date): date is string => Boolean(date))
			.sort((left, right) => Date.parse(right) - Date.parse(left))[0];

		return {
			meta: integrationMeta("live", "Connected to Linq", updatedAt),
			data: {
				online: status.online,
				phoneNumber: status.phoneNumber,
				conversations: status.conversations,
				recommendations: status.recommendations,
				paymentLinksSent: status.paymentLinksSent,
				events,
			},
		};
	} catch (error) {
		return emptyState(
			"error",
			`Configured Linq deployment unavailable. ${getErrorMessage(error)}`,
		);
	}
};
