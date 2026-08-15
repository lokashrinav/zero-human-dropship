import {
	asArray,
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
	AutonomousLoopStage,
	CeoDecision,
	DecisionsData,
	PanelState,
} from "../contracts";
import { fetchJson } from "../http";

const decisionKinds = new Set<CeoDecision["kind"]>([
	"repriced_product",
	"changed_copy",
	"listed_product",
	"removed_product",
	"changed_promotion",
	"terac_reorder",
	"other",
]);

const decisionStages = new Set<AutonomousLoopStage>([
	"source",
	"validate",
	"list",
	"sell",
	"fulfill",
	"learn",
]);

const stageForKind = (kind: CeoDecision["kind"]): AutonomousLoopStage => {
	if (kind === "listed_product" || kind === "changed_copy") return "list";
	if (
		kind === "removed_product" ||
		kind === "changed_promotion" ||
		kind === "terac_reorder"
	) {
		return "learn";
	}
	if (kind === "repriced_product") return "learn";
	return "source";
};

const parseDecision = (value: unknown): CeoDecision | undefined => {
	if (!isRecord(value)) return undefined;
	const id = asString(value.id);
	const timestamp = asIsoDate(value.timestamp);
	const reason = asString(value.reason);
	const action = asString(value.action);
	const rawKind = asString(value.kind) as CeoDecision["kind"] | undefined;
	const kind = rawKind && decisionKinds.has(rawKind) ? rawKind : "other";
	const rawStage = asString(value.stage) as AutonomousLoopStage | undefined;
	const stage =
		rawStage && decisionStages.has(rawStage) ? rawStage : stageForKind(kind);
	const outcome = asString(value.outcome);

	if (!id || !timestamp || !reason || !action) return undefined;
	return {
		id,
		timestamp,
		agent: asString(value.agent) ?? "CEO AGENT",
		title: asString(value.title) ?? kind.replaceAll("_", " ").toUpperCase(),
		kind,
		reason,
		action,
		...(outcome ? { outcome } : {}),
		stage,
	};
};

const nativeKindForAction = (action: string): CeoDecision["kind"] => {
	if (action === "reprice") return "repriced_product";
	if (action === "shift_focus") return "changed_promotion";
	if (action === "drop_product") return "removed_product";
	return "other";
};

const nativeStageForAction = (action: string): AutonomousLoopStage => {
	if (action === "shift_focus") return "sell";
	if (action === "source_product") return "source";
	return "learn";
};

const nativeTitleForAction = (action: string) => {
	if (action === "reprice") return "REPRICED PRODUCT";
	if (action === "shift_focus") return "SHIFTED CHANNEL FOCUS";
	if (action === "no_action") return "HELD BUSINESS STATE";
	if (action === "drop_product") return "REMOVED PRODUCT";
	return action.replaceAll("_", " ").toUpperCase();
};

const nativeActionDescription = (value: Record<string, unknown>, action: string) => {
	const status = asString(value.status)?.toUpperCase();
	const suffix = status ? ` · ${status}` : "";
	if (action === "reprice") {
		const productId = asString(value.product_id);
		const priceMinor = asNonNegativeInteger(value.new_price_cents);
		if (productId && priceMinor !== undefined) {
			return `Set ${productId} to $${(priceMinor / 100).toFixed(2)}${suffix}`;
		}
	}
	if (action === "shift_focus") {
		const channel = asString(value.channel);
		if (channel) return `Dispatched ${channel.replaceAll("_", " ")}${suffix}`;
	}
	if (action === "no_action") return `Held catalog and pricing${suffix}`;
	return `${action.replaceAll("_", " ")}${suffix}`;
};

const parseNativeCycle = (value: unknown): CeoDecision[] => {
	if (!isRecord(value)) return [];
	const agent = asString(value.agent);
	const message = asString(value.message);
	const timestampSeconds = asNumber(value.ts);
	if (
		!agent ||
		!message ||
		timestampSeconds === undefined ||
		!/^CEO(?: AGENT)?$/i.test(agent) ||
		!message.startsWith("Claude Code cycle:")
	) {
		return [];
	}

	const jsonStart = message.indexOf("{");
	if (jsonStart < 0) return [];
	let cycle: unknown;
	try {
		cycle = JSON.parse(message.slice(jsonStart));
	} catch {
		return [];
	}
	if (!isRecord(cycle)) return [];
	const actions = asArray(cycle.actions) ?? [];
	const timestamp = new Date(timestampSeconds * 1_000).toISOString();
	return actions.flatMap((rawAction, index) => {
		if (!isRecord(rawAction)) return [];
		const actionName = asString(rawAction.action);
		const reason = asString(rawAction.reason);
		if (!actionName || !reason) return [];
		return [{
			id: `person-a-${Math.floor(timestampSeconds * 1_000)}-${index}-${actionName}`,
			timestamp,
			agent: "CEO AGENT",
			title: nativeTitleForAction(actionName),
			kind: nativeKindForAction(actionName),
			reason,
			action: nativeActionDescription(rawAction, actionName),
			stage: nativeStageForAction(actionName),
		} satisfies CeoDecision];
	});
};

const parseDecisionEntries = (value: unknown): CeoDecision[] => {
	const normalized = parseDecision(value);
	return normalized ? [normalized] : parseNativeCycle(value);
};

const parseDecisions = (payload: unknown) => {
	const values = isRecord(payload) ? asArray(payload.decisions) : asArray(payload);
	if (!values) {
		throw new Error("CEO decisions response does not match its contract");
	}

	const decisions = values
		.flatMap(parseDecisionEntries)
		.sort(
			(left, right) =>
				Date.parse(right.timestamp) - Date.parse(left.timestamp),
		);
	const updatedAt =
		(isRecord(payload) ? asIsoDate(payload.updatedAt) : undefined) ??
		decisions[0]?.timestamp;
	return { decisions, updatedAt };
};

export const getDecisionsData = async (): Promise<PanelState<DecisionsData>> => {
	const { url, token } = dashboardConfig.decisions;
	if (!url) {
		return {
			meta: integrationMeta(
				"pending",
				"Waiting for a verified Person A CEO decision feed",
			),
			data: { decisions: [] },
		};
	}

	try {
		const { decisions, updatedAt } = parseDecisions(
			await fetchJson(url, { token }),
		);
		return {
			meta: integrationMeta("live", "Connected to CEO decision logs", updatedAt),
			data: { decisions },
		};
	} catch (error) {
		return {
			meta: integrationMeta(
				"error",
				`Configured CEO decision feed unavailable. ${getErrorMessage(error)}`,
			),
			data: { decisions: [] },
		};
	}
};
