import { ArrowUpRight, MessageCircleMore } from "lucide-react";

function getSalesAgentHref() {
	const configuredUrl = process.env.NEXT_PUBLIC_SALES_AGENT_URL?.trim();
	if (configuredUrl) {
		return configuredUrl;
	}

	const phone = process.env.NEXT_PUBLIC_LINQ_PHONE?.replace(/[^+\d]/g, "");
	return phone ? `sms:${phone}?body=${encodeURIComponent("Help me find the right KOVA product.")}` : null;
}

export function AiSalesCta() {
	const agentHref = getSalesAgentHref();

	return (
		<section className="px-4 py-4 sm:px-6 lg:px-8" aria-labelledby="ai-sales-title">
			<div className="ai-cta mx-auto max-w-7xl overflow-hidden rounded-[2rem] border border-white/10 px-5 py-7 sm:px-8 sm:py-9 lg:flex lg:items-center lg:justify-between lg:px-10">
				<div className="flex items-start gap-4">
					<span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-lime-300 text-neutral-950 shadow-[0_0_30px_rgba(190,242,100,0.18)]">
						<MessageCircleMore className="size-5" aria-hidden="true" />
					</span>
					<div>
						<p className="eyebrow text-lime-300">Your personal product scout</p>
						<h2 id="ai-sales-title" className="mt-2 text-2xl font-semibold tracking-[-0.04em] sm:text-3xl">
							Text our AI shopping agent for a personalized deal
						</h2>
						<p className="mt-2 max-w-2xl text-sm leading-6 text-white/60 sm:text-base">
							Tell it what you need and your budget. It will help narrow the catalog—without the hard sell.
						</p>
					</div>
				</div>
				{agentHref ? (
					<a
						href={agentHref}
						className="mt-6 inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-lime-300 px-6 text-sm font-semibold text-neutral-950 transition hover:bg-lime-200 lg:mt-0 lg:w-auto"
					>
						Text our AI agent
						<ArrowUpRight className="size-4" aria-hidden="true" />
					</a>
				) : (
					<span className="mt-6 inline-flex h-12 w-full cursor-not-allowed items-center justify-center rounded-full border border-white/10 bg-white/5 px-6 text-sm font-medium text-white/45 lg:mt-0 lg:w-auto">
						Agent connection coming online
					</span>
				)}
			</div>
		</section>
	);
}
