import feedback from "@/terac-feedback.json";

export function GET() {
	return Response.json(feedback, {
		headers: {
			"Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
		},
	});
}
