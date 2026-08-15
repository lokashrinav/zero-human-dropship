const value = (name: string) => {
	const raw = process.env[name]?.trim();
	return raw ? raw : undefined;
};

const numberValue = (name: string, fallback: number) => {
	const parsed = Number(value(name));
	return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const VERIFIED_STOREFRONT_CATALOG_URL =
	"https://storefront-omega-three.vercel.app/api/catalog";

export const dashboardConfig = {
	requestTimeoutMs: numberValue("DASHBOARD_REQUEST_TIMEOUT_MS", 4_000),
	stripe: {
		secretKey: value("STRIPE_SECRET_KEY"),
		revenueUrl: value("STRIPE_REVENUE_URL"),
		revenueToken: value("STRIPE_REVENUE_TOKEN"),
	},
	linq: {
		baseUrl: value("LINQ_BASE_URL"),
		statusUrl: value("LINQ_STATUS_URL"),
		eventsUrl: value("LINQ_EVENTS_URL"),
		token: value("LINQ_API_TOKEN"),
	},
	decisions: {
		url: value("CEO_DECISIONS_URL"),
		token: value("CEO_DECISIONS_TOKEN"),
	},
	terac: {
		url: value("TERAC_FEEDBACK_URL"),
		token: value("TERAC_FEEDBACK_TOKEN"),
	},
	catalog: {
		url: value("CATALOG_URL") ?? VERIFIED_STOREFRONT_CATALOG_URL,
		token: value("CATALOG_TOKEN"),
		jsonPath: value("CATALOG_JSON_PATH"),
	},
	proof: {
		bandUrl: value("BAND_STATUS_URL"),
		bandToken: value("BAND_STATUS_TOKEN"),
		renderUrl: value("RENDER_STATUS_URL"),
		renderToken: value("RENDER_STATUS_TOKEN"),
		replayUrl: value("REPLAY_VERIFICATION_URL"),
		replayToken: value("REPLAY_VERIFICATION_TOKEN"),
	},
} as const;
