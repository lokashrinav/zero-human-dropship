import { asIsoDate, getErrorMessage, isRecord } from "../common";
import type {
	CatalogData,
	DecisionsData,
	LinqData,
	PanelState,
	RevenueData,
	SponsorName,
	SponsorProof,
	TeracData,
} from "../contracts";
import { dashboardConfig } from "../config";
import { fetchJson } from "../http";
import { getPersonAProofs } from "../person-a-proof";
import { getPioneerProof } from "../pioneer";

type CorePanels = {
	revenue: PanelState<RevenueData>;
	linq: PanelState<LinqData>;
	terac: PanelState<TeracData>;
	decisions: PanelState<DecisionsData>;
	catalog: PanelState<CatalogData>;
};

const sourceProof = (
	name: SponsorName,
	activeLabel: string,
	panel: PanelState<unknown>,
): SponsorProof => {
	if (panel.meta.mode === "live") {
		return { name, status: "active", label: activeLabel };
	}
	if (panel.meta.mode === "error") {
		return {
			name,
			status: "degraded",
			label: "DEGRADED",
			detail: panel.meta.detail,
		};
	}
	return { name, status: "pending", label: "PENDING" };
};

type ProbeOptions = {
	name: SponsorName;
	activeLabel: string;
	url?: string;
	token?: string;
	replay?: boolean;
};

const probeProof = async (options: ProbeOptions): Promise<SponsorProof> => {
	if (!options.url) {
		return { name: options.name, status: "pending", label: "PENDING" };
	}

	try {
		const payload = await fetchJson(options.url, { token: options.token });
		if (!isRecord(payload)) throw new Error("Proof endpoint must return an object");
		if (options.replay) {
			const verifiedAt = asIsoDate(payload.verifiedAt);
			if (payload.verified !== true || !verifiedAt) {
				throw new Error("Replay proof is not verified");
			}
			return {
				name: options.name,
				status: "verified",
				label: options.activeLabel,
				detail: `Verified ${verifiedAt}`,
			};
		}

		if (payload.ok !== true) throw new Error("Proof endpoint is not healthy");
		return { name: options.name, status: "active", label: options.activeLabel };
	} catch (error) {
		return {
			name: options.name,
			status: "degraded",
			label: "DEGRADED",
			detail: getErrorMessage(error),
		};
	}
};

const isRenderUrl = (value: string | undefined) => {
	if (!value) return false;
	try {
		return new URL(value).hostname.endsWith(".onrender.com");
	} catch {
		return false;
	}
};

export const getSponsorProofs = async (
	panels: CorePanels,
): Promise<SponsorProof[]> => {
	const { bandUrl, bandToken, renderUrl, renderToken, replayUrl, replayToken } =
		dashboardConfig.proof;
	const [renderProbe, replay] = await Promise.all([
		probeProof({
			name: "Render",
			activeLabel: "WORKFLOW EXECUTION",
			url: renderUrl,
			token: renderToken,
		}),
		probeProof({
			name: "Replay",
			activeLabel: "QA VERIFIED",
			url: replayUrl,
			token: replayToken,
			replay: true,
		}),
	]);
	const render =
		panels.linq.meta.mode === "live" &&
		(isRenderUrl(dashboardConfig.linq.baseUrl) ||
			isRenderUrl(dashboardConfig.linq.statusUrl) ||
			isRenderUrl(dashboardConfig.linq.eventsUrl))
			? {
					name: "Render",
					status: "verified",
					label: "VERIFIED",
					summary: "LIVE LINQ SERVICE",
					detail: "The configured Linq service is responding from a public onrender.com deployment.",
				} satisfies SponsorProof
			: renderProbe;
	const liveCheckoutLinks = panels.catalog.data.products.filter(
		(product) =>
			product.active && product.url?.startsWith("https://buy.stripe.com/"),
	).length;
	const stripe =
		panels.revenue.meta.mode === "live"
			? sourceProof("Stripe", "REAL REVENUE", panels.revenue)
			: panels.catalog.meta.mode === "live" && liveCheckoutLinks > 0
				? {
						name: "Stripe",
						status: "active",
						label: "REAL COMMERCE",
						summary: `${liveCheckoutLinks} LIVE PAYMENT LINKS`,
						detail:
							"Verified live Stripe products and checkout links. Revenue remains separate until a successful live payment exists.",
					} satisfies SponsorProof
				: sourceProof("Stripe", "REAL REVENUE", panels.revenue);
	const linq = sourceProof("Linq", "LIVE", panels.linq);
	if (linq.status === "pending") {
		linq.label = "DEPLOYMENT PENDING";
		linq.detail = panels.linq.meta.detail;
	}
	const band: SponsorProof = {
		name: "Band",
		status: "disabled",
		label: "DISABLED",
		detail:
			bandUrl || bandToken
				? "Band remains intentionally disabled; configured values are not probed."
				: "Band is intentionally disabled and is not part of the active company loop.",
	};
	const terac: SponsorProof =
		panels.terac.meta.mode === "live"
			? {
					name: "Terac",
					status: "verified",
					label: "VERIFIED",
					summary: "REAL HUMAN FEEDBACK",
					detail: panels.terac.meta.detail,
				}
			: sourceProof("Terac", "REAL HUMAN FEEDBACK", panels.terac);

	return [
		terac,
		stripe,
		getPioneerProof(),
		linq,
		band,
		render,
		replay,
		...getPersonAProofs(),
	];
};
