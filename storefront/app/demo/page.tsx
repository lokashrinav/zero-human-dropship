import { Bot, CheckCircle2, CircleDashed, CreditCard, Package } from "lucide-react";
import type { Metadata } from "next";
import { getCatalogStatus } from "@/lib/catalog";
import { hasYnsApiKey } from "@/lib/commerce";

export const metadata: Metadata = {
	title: "Launch status",
	description: "Current storefront integration status.",
	robots: { index: false, follow: false },
};

export default function DemoPage() {
	const catalogStatus = getCatalogStatus();
	const linqConnected = Boolean(
		process.env.NEXT_PUBLIC_LINQ_PHONE || process.env.NEXT_PUBLIC_SALES_AGENT_URL,
	);
	const checkoutConnected = hasYnsApiKey || catalogStatus.liveCount > 0;
	const rows = [
		{ label: "Store", value: "LIVE", ready: true, icon: CheckCircle2 },
		{
			label: "Stripe checkout",
			value: checkoutConnected ? "Connected" : "Waiting for live catalog",
			ready: checkoutConnected,
			icon: CreditCard,
		},
		{
			label: "Catalog",
			value: `${catalogStatus.count} ${catalogStatus.mode} products`,
			ready: true,
			icon: Package,
		},
		{
			label: "Linq agent",
			value: linqConnected ? "Connected" : "Not connected",
			ready: linqConnected,
			icon: Bot,
		},
	];

	return (
		<section className="mx-auto min-h-[70vh] max-w-4xl px-4 py-16 sm:px-6 sm:py-24">
			<p className="eyebrow text-lime-300">Operator view</p>
			<h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] sm:text-6xl">Launch status</h1>
			<p className="mt-4 max-w-xl text-muted-foreground">
				Current production commerce readiness, sourced from the deployed catalog and integration
				configuration.
			</p>
			<div className="mt-10 overflow-hidden rounded-3xl border border-border bg-card/70">
				{rows.map((row) => (
					<div
						key={row.label}
						className="flex items-center gap-4 border-b border-border p-5 last:border-b-0 sm:p-6"
					>
						<row.icon className="h-5 w-5 text-lime-300" />
						<div className="min-w-0 flex-1">
							<p className="text-sm text-muted-foreground">{row.label}</p>
							<p className="truncate font-medium">{row.value}</p>
						</div>
						{row.ready ? (
							<CheckCircle2 className="h-5 w-5 text-lime-300" />
						) : (
							<CircleDashed className="h-5 w-5 text-muted-foreground" />
						)}
					</div>
				))}
			</div>
		</section>
	);
}
