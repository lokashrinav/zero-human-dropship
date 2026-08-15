import type { SponsorProof } from "../contracts";

// Credential-free, immutable evidence copied from the verified local run at:
// pioneer-product-intelligence/data/recent_runs.jsonl
export const pioneerVerifiedEvidence = {
	verifiedAt: "2026-08-15T19:20:56.289815Z",
	modelId: "openai/gpt-oss-120b",
	model: "GPT-OSS 120B",
	validatorId: "fastino/gliner2-large-v1",
	validator: "Fastino GLiNER2",
	productsConsidered: 3,
	topRanking: "demo-cable (95)",
	latencyMs: 18_679,
	fastinoValidation: "PASS",
	inference: "PASS",
	pipeline: "PASS",
	serviceLive: false,
} as const;

export const getPioneerProof = (): SponsorProof => ({
	name: "Pioneer",
	status: "verified",
	label: "VERIFIED",
	summary: "GPT-OSS 120B · GLINER2 PASS",
	detail: [
		"VERIFIED REAL RUN — not a live service.",
		`Inference ${pioneerVerifiedEvidence.inference}; pipeline ${pioneerVerifiedEvidence.pipeline}; Fastino ${pioneerVerifiedEvidence.fastinoValidation}.`,
		`Top ranked ${pioneerVerifiedEvidence.topRanking}.`,
		`Verified ${pioneerVerifiedEvidence.verifiedAt}.`,
	].join(" "),
});
