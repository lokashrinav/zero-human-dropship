import type { SponsorProof } from "../contracts";

export const getPersonAProofs = (): SponsorProof[] => [
	{
		name: "Superserve",
		status: "pending",
		label: "PENDING",
		summary: "NO VERIFIED RUN",
		detail: "Superserve integration code exists, but the repository and public audit feed contain no successful sandbox run evidence.",
	},
	{
		name: "Solari",
		status: "verified",
		label: "VERIFIED",
		summary: "LIVE STOREFRONT AUDIT",
		detail: "Person A's public audit trail records a completed Solari cloud-browser storefront verification at 2026-08-15 13:36 PT.",
	},
];
