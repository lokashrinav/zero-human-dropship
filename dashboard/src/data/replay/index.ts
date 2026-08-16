import type { SponsorProof } from "../contracts";

const DASHBOARD_REPLAY_REPORT =
 "https://qa.replay.io/projects/proj-zero-human-control-room-vercel-app-msuwwep3/test-runs/ts-msuwwf79-zzu4";

export const getReplayProof = (): SponsorProof => ({
 name: "Replay",
 status: "verified",
 label: "VERIFIED",
 summary: "5 JOURNEYS · NO P0/P1",
 detail: `Actual Replay QA run ts-msuwwf79-zzu4 completed with 5 journeys and no material P0/P1 findings. ${DASHBOARD_REPLAY_REPORT}`,
});
