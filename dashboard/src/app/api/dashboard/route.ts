import { getDashboardSnapshot } from "@/data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
	const snapshot = await getDashboardSnapshot();
	return Response.json(snapshot, {
		headers: {
			"Cache-Control": "no-store, max-age=0",
		},
	});
}
