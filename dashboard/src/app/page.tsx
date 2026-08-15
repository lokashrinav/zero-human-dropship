import { DashboardShell } from "@/components/dashboard-shell";
import { getDashboardSnapshot } from "@/data";

export const dynamic = "force-dynamic";

export default async function Home() {
  const initialSnapshot = await getDashboardSnapshot();
  return <DashboardShell initialSnapshot={initialSnapshot} />;
}
