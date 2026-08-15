import { dashboardConfig } from "./config";

type JsonRequestOptions = {
	token?: string;
	timeoutMs?: number;
};

export const fetchJson = async (url: string, options: JsonRequestOptions = {}) => {
	const response = await fetch(url, {
		headers: {
			Accept: "application/json",
			...(options.token
				? { Authorization: `Bearer ${options.token}` }
				: {}),
		},
		cache: "no-store",
		signal: AbortSignal.timeout(
			options.timeoutMs ?? dashboardConfig.requestTimeoutMs,
		),
	});

	if (!response.ok) {
		throw new Error(`Integration returned HTTP ${response.status}`);
	}

	return (await response.json()) as unknown;
};
