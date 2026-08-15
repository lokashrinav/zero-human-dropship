import {
	asArray,
	asIsoDate,
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

const parseDecisions = (payload: unknown) => {
	const values = isRecord(payload) ? asArray(payload.decisions) : asArray(payload);
	if (!values) {
		throw new Error("CEO decisions response does not match its contract");
	}

	const decisions = values
		.map(parseDecision)
		.filter((decision): decision is CeoDecision => decision !== undefined)
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
