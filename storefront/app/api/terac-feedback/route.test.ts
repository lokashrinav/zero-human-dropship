import { describe, expect, test } from "bun:test";
import { GET } from "@/app/api/terac-feedback/route";

describe("Terac feedback endpoint", () => {
	test("returns approved real-study evidence with a genuine before/after change", async () => {
		const response = GET();
		const payload = await response.json();
		const study = payload.studies[0];

		expect(response.status).toBe(200);
		expect(study.id).toBe("w14sbyed2iixiz76o5ass608");
		expect(study.feedback.sampleSize).toBe(10);
		expect(study.before.items).toHaveLength(10);
		expect(study.after.items).toHaveLength(10);
		expect(study.before.items.map(({ id }: { id: string }) => id)).not.toEqual(
			study.after.items.map(({ id }: { id: string }) => id),
		);
	});
});
