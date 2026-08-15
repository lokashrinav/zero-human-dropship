import decisions from "@/ceo-decisions.json";

export function GET() {
	return Response.json(decisions, {
		headers: {
			"Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
		},
	});
}
