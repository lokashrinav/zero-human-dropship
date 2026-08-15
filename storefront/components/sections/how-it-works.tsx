import { CreditCard, PackageCheck, ScanSearch } from "lucide-react";

const steps = [
	{
		icon: ScanSearch,
		number: "01",
		title: "Find your upgrade",
		description: "Browse the edit or ask our AI agent to help match a product to your needs and budget.",
	},
	{
		icon: CreditCard,
		number: "02",
		title: "Check out securely",
		description: "Pay through Stripe. Physical orders require a complete shipping address before payment.",
	},
	{
		icon: PackageCheck,
		number: "03",
		title: "Track the handoff",
		description: "Delivery estimates and shipping costs are shown during checkout when available.",
	},
] as const;

export function HowItWorks() {
	return (
		<section id="how-it-works" className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-28 lg:px-8">
			<div className="grid gap-10 lg:grid-cols-[0.75fr_1.25fr] lg:gap-20">
				<div>
					<p className="eyebrow text-lime-300">Simple by design</p>
					<h2 className="mt-4 max-w-md text-3xl font-semibold tracking-[-0.045em] sm:text-4xl">
						From “that looks useful” to on its way.
					</h2>
					<p className="mt-5 max-w-md text-sm leading-6 text-muted-foreground sm:text-base">
						No manufactured urgency. Take your time, check the details, and buy only when it makes sense.
					</p>
				</div>
				<div className="grid gap-3">
					{steps.map((step) => {
						const Icon = step.icon;
						return (
							<article
								key={step.number}
								className="group grid grid-cols-[auto_1fr] gap-4 rounded-3xl border border-border bg-card/60 p-5 transition-colors hover:border-lime-300/30 sm:gap-5 sm:p-6"
							>
								<div className="flex size-11 items-center justify-center rounded-2xl bg-secondary text-lime-300">
									<Icon className="size-5" aria-hidden="true" />
								</div>
								<div>
									<div className="flex items-baseline justify-between gap-4">
										<h3 className="font-semibold tracking-tight">{step.title}</h3>
										<span className="font-mono text-xs text-muted-foreground">{step.number}</span>
									</div>
									<p className="mt-2 text-sm leading-6 text-muted-foreground">{step.description}</p>
								</div>
							</article>
						);
					})}
				</div>
			</div>
		</section>
	);
}
