import "server-only";
import { getCatalogData } from "./catalog";
import { getDecisionsData } from "./decisions";
import type {
	AutonomousLoopStage,
	CeoDecision,
	DashboardSnapshot,
	LinqEvent,
} from "./contracts";
import { getLinqData } from "./linq";
import { getSponsorProofs } from "./sponsors";
import { getStripeRevenue } from "./stripe";
import { getTeracData } from "./terac";

export type {
	AutonomousLoopStage,
	BusinessStateItem,
	CatalogData,
	CatalogProduct,
	CeoDecision,
	DashboardMetrics,
	DashboardSnapshot,
	DataMode,
	DecisionsData,
	IntegrationMeta,
	LinqData,
	LinqEvent,
	LinqEventType,
	PanelState,
	RevenueData,
	SponsorName,
	SponsorProof,
	TeracChange,
	TeracData,
	TeracStudy,
} from "./contracts";

type StageSignal = {
	timestamp: string;
	stage: AutonomousLoopStage;
};

const latestStage = (events: LinqEvent[], decisions: CeoDecision[]) => {
	const signals: StageSignal[] = [
		...events.map(({ timestamp, stage }) => ({ timestamp, stage })),
		...decisions.map(({ timestamp, stage }) => ({ timestamp, stage })),
	];
	return (
		signals.sort(
			(left, right) =>
				Date.parse(right.timestamp) - Date.parse(left.timestamp),
		)[0]?.stage ?? null
	);
};

export const getDashboardSnapshot = async (): Promise<DashboardSnapshot> => {
	const [revenue, linq, decisions, terac, catalog] = await Promise.all([
		getStripeRevenue(),
		getLinqData(),
		getDecisionsData(),
		getTeracData(),
		getCatalogData(),
	]);
	const sponsors = await getSponsorProofs({
		revenue,
		linq,
		decisions,
		terac,
		catalog,
	});
	const livePanels = [revenue, linq, decisions, terac, catalog].filter(
		(panel) => panel.meta.mode === "live",
	);

	return {
		generatedAt: new Date().toISOString(),
		isReceivingLiveData: livePanels.length > 0,
		activeStage: latestStage(linq.data.events, decisions.data.decisions),
		metrics: {
			revenueMinor: revenue.data.amountMinor,
			revenueCurrency: revenue.data.currency,
			orders: revenue.data.orders,
			productsLive: catalog.data.activeCount,
			customerConversations: linq.data.conversations,
			autonomousDecisions: decisions.data.decisions.length,
		},
		revenue,
		linq,
		decisions,
		terac,
		catalog,
		sponsors,
	};
};
