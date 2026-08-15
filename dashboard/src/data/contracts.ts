export type DataMode = "live" | "demo" | "pending" | "error";

export type IntegrationMeta = {
	mode: DataMode;
	label: "LIVE" | "DEMO DATA" | "WAITING" | "DEGRADED";
	fetchedAt: string;
	updatedAt?: string;
	detail?: string;
	fallback?: "demo";
};

export type PanelState<T> = {
	meta: IntegrationMeta;
	data: T;
};

export type RevenueData = {
	amountMinor: number | null;
	currency: string;
	orders: number | null;
	statusText: string;
};

export type AutonomousLoopStage =
	| "source"
	| "validate"
	| "list"
	| "sell"
	| "fulfill"
	| "learn";

export type LinqEventType =
	| "inbound_message"
	| "sales_agent"
	| "product_selected"
	| "recommendation"
	| "payment_link_sent"
	| "payment_completed"
	| "order_fulfilled"
	| "feedback_received"
	| "other";

export type LinqEvent = {
	id: string;
	timestamp: string;
	type: LinqEventType;
	stage: AutonomousLoopStage;
	headline: string;
	detail?: string;
	direction: "inbound" | "internal" | "outbound";
};

export type LinqData = {
	online: boolean | null;
	phoneNumber: string | null;
	conversations: number;
	recommendations: number;
	paymentLinksSent: number;
	events: LinqEvent[];
};

export type CeoDecision = {
	id: string;
	timestamp: string;
	agent: string;
	title: string;
	kind:
		| "repriced_product"
		| "changed_copy"
		| "listed_product"
		| "removed_product"
		| "changed_promotion"
		| "terac_reorder"
		| "other";
	reason: string;
	action: string;
	outcome?: string;
	stage: AutonomousLoopStage;
};

export type DecisionsData = {
	decisions: CeoDecision[];
};

export type BusinessStateItem = {
	id: string;
	name: string;
	position?: number;
	priceMinor?: number;
	currency?: string;
	copy?: string;
	active?: boolean;
};

export type TeracChange = {
	type: "removed" | "replaced" | "price" | "copy" | "product_order" | "other";
	description: string;
};

export type TeracRatedProduct = {
	id: string;
	name: string;
	averageLikelihood: number;
};

export type TeracStudy = {
	id: string;
	title: string;
	capturedAt: string;
	before: {
		summary: string;
		items: BusinessStateItem[];
	};
	feedback: {
		sampleSize: number;
		result: string;
		rating?: number;
		ratingScale?: number;
		highestRatedProduct?: TeracRatedProduct;
		lowestRatedProducts?: TeracRatedProduct[];
	};
	changes: TeracChange[];
	after: {
		summary: string;
		items: BusinessStateItem[];
	};
};

export type TeracData = {
	studies: TeracStudy[];
};

export type CatalogProduct = {
	id: string;
	name: string;
	priceMinor: number | null;
	currency: string;
	source: string;
	active: boolean;
	promoted: boolean;
	url?: string;
	imageUrl?: string;
};

export type CatalogData = {
	products: CatalogProduct[];
	productCount: number;
	activeCount: number;
	promotedProducts: CatalogProduct[];
};

export type SponsorName =
	| "Terac"
	| "Stripe"
	| "Pioneer"
	| "Linq"
	| "Band"
	| "Render"
	| "Replay";

export type SponsorProof = {
	name: SponsorName;
	status: "active" | "verified" | "pending" | "disabled" | "degraded";
	label: string;
	summary?: string;
	detail?: string;
};

export type DashboardMetrics = {
	revenueMinor: number | null;
	revenueCurrency: string;
	orders: number | null;
	productsLive: number;
	customerConversations: number;
	autonomousDecisions: number;
};

export type DashboardSnapshot = {
	generatedAt: string;
	isReceivingLiveData: boolean;
	activeStage: AutonomousLoopStage | null;
	metrics: DashboardMetrics;
	revenue: PanelState<RevenueData>;
	linq: PanelState<LinqData>;
	decisions: PanelState<DecisionsData>;
	terac: PanelState<TeracData>;
	catalog: PanelState<CatalogData>;
	sponsors: SponsorProof[];
};
