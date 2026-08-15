import { describe, expect, test } from "bun:test";
import { GET } from "@/app/api/ceo-decisions/route";

describe("CEO decisions endpoint", () => {
	test("returns the Terac-derived catalog decision", async () => {
		const response = GET();
		const payload = await response.json();
		const decision = payload.decisions[0];

		expect(response.status).toBe(200);
		expect(decision.kind).toBe("terac_reorder");
		expect(decision.action).toContain("position 2 to 1");
		expect(decision.outcome).toBeUndefined();
	});
});
