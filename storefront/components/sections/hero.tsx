import { ArrowDownRight, Check, MessageCircleMore, PackageOpen, ShieldCheck, Sparkles } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { commerce } from "@/lib/commerce";
import { formatMoney } from "@/lib/money";
import { getStoreConfig } from "@/lib/store-config";

function getSalesAgentHref() {
	const configuredUrl = process.env.NEXT_PUBLIC_SALES_AGENT_URL?.trim();
	if (configuredUrl) {
		return configuredUrl;
	}

	const phone = process.env.NEXT_PUBLIC_LINQ_PHONE?.replace(/[^+\d]/g, "");
	return phone ? `sms:${phone}?body=${encodeURIComponent("Help me find the right KOVA product.")}` : null;
}

const trustPoints = ["Secure checkout", "Shipping shown before payment"] as const;

export async function Hero() {
	const agentHref = getSalesAgentHref();
	const [featuredResult, storeConfig] = await Promise.all([
		commerce.productBrowse({ active: true, limit: 1 }),
		getStoreConfig(),
	]);
	const featuredProduct = featuredResult.data[0] ?? null;
	const featuredPrice = featuredProduct?.variants[0]?.price
		? formatMoney({
				amount: featuredProduct.variants[0].price,
				currency: storeConfig.currency,
				locale: storeConfig.locale,
			})
		: null;
	const featuredImage = featuredProduct?.images[0] ?? featuredProduct?.variants[0]?.images[0] ?? null;

	return (
		<section className="hero-field relative isolate overflow-hidden border-b border-border">
			<div className="pointer-events-none absolute inset-0" aria-hidden="true">
				<div className="hero-orb absolute -right-36 -top-20 size-[28rem] rounded-full sm:size-[40rem]" />
				<div className="hero-grid absolute inset-0 opacity-40" />
			</div>

			<div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 py-12 sm:px-6 sm:py-16 lg:min-h-[42rem] lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:py-20">
				<div className="max-w-3xl">
					<div className="mb-5 inline-flex items-center gap-2 rounded-full border border-lime-300/20 bg-lime-300/8 px-3 py-1.5 text-xs font-medium text-lime-200 sm:mb-6">
						<Sparkles className="size-3.5" aria-hidden="true" />
						The useful-things edit
					</div>
					<h1 className="text-balance text-[clamp(3.15rem,8vw,6.6rem)] font-semibold leading-[0.88] tracking-[-0.075em]">
						Small upgrades.
						<span className="mt-2 block text-lime-300">Big difference.</span>
					</h1>
					<p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground sm:mt-6 sm:text-lg">
						A sharply curated drop of clever everyday products—picked for usefulness, not hype.
					</p>

					<div className="mt-6 flex flex-col gap-3 sm:mt-8 sm:flex-row">
						<Link
							href="#products"
							className="group inline-flex h-13 items-center justify-center gap-2 rounded-full bg-lime-300 px-7 text-sm font-semibold text-neutral-950 transition hover:bg-lime-200"
						>
							Shop the latest drop
							<ArrowDownRight className="size-4 transition-transform group-hover:translate-x-0.5 group-hover:translate-y-0.5" />
						</Link>
						{agentHref ? (
							<a
								href={agentHref}
								className="inline-flex h-13 items-center justify-center gap-2 rounded-full border border-white/12 bg-white/5 px-7 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
							>
								<MessageCircleMore className="size-4" />
								Text our AI agent
							</a>
						) : null}
					</div>

					<ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2.5 sm:mt-8" aria-label="Store assurances">
						{trustPoints.map((point) => (
							<li key={point} className="flex items-center gap-1.5 text-xs text-white/50">
								<Check className="size-3.5 text-lime-300" aria-hidden="true" />
								{point}
							</li>
						))}
					</ul>
				</div>

				{featuredProduct && (
					<div className="relative hidden min-h-[30rem] lg:block">
						<Link
							href={`/product/${featuredProduct.slug}`}
							className="group absolute inset-x-8 top-0 aspect-[4/5] rotate-2 overflow-hidden rounded-[2.5rem] border border-white/10 bg-white/[0.045] p-4 shadow-2xl transition duration-500 hover:rotate-0"
						>
							<div className="relative h-full overflow-hidden rounded-[2rem] border border-white/8 bg-neutral-950/70">
								{featuredImage ? (
									<Image
										src={featuredImage}
										alt={featuredProduct.name}
										fill
										sizes="(max-width: 1024px) 0px, 38vw"
										className="object-cover transition duration-700 group-hover:scale-[1.03]"
										priority
									/>
								) : (
									<div className="absolute inset-0 grid place-items-center bg-[radial-gradient(circle_at_center,rgba(190,242,100,0.18),transparent_42%)]">
										<div className="text-center text-white/55">
											<PackageOpen className="mx-auto size-20 text-lime-300/70" aria-hidden="true" />
											<p className="mt-4 text-sm">Product image coming soon</p>
										</div>
									</div>
								)}
								<div className="absolute inset-0 bg-linear-to-t from-black/80 via-transparent to-black/15" />
								<div className="absolute left-6 top-6 flex items-center gap-2 rounded-full border border-white/10 bg-black/45 px-3 py-1.5 text-[0.65rem] uppercase tracking-[0.2em] text-white/75 backdrop-blur-md">
									<span className="size-1.5 rounded-full bg-lime-300 shadow-[0_0_12px_rgba(190,242,100,0.9)]" />
									Featured product
								</div>
								<div className="absolute bottom-7 left-7 right-7 flex items-end justify-between gap-5">
									<div>
										<p className="font-mono text-xs text-lime-300">KOVA / LIVE CATALOG</p>
										<p className="mt-2 text-3xl font-semibold leading-tight tracking-[-0.04em]">
											{featuredProduct.name}
										</p>
									</div>
									{featuredPrice && (
										<p className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-black">
											{featuredPrice}
										</p>
									)}
								</div>
							</div>
						</Link>
						<div className="absolute -bottom-2 -left-2 flex items-center gap-3 rounded-2xl border border-white/10 bg-neutral-900/90 p-4 shadow-xl backdrop-blur-lg">
							<span className="flex size-10 items-center justify-center rounded-xl bg-lime-300 text-neutral-950">
								<ShieldCheck className="size-5" />
							</span>
							<div>
								<p className="text-sm font-semibold">Checkout, protected</p>
								<p className="mt-0.5 text-xs text-white/45">Payments processed by Stripe</p>
							</div>
						</div>
					</div>
				)}
			</div>
		</section>
	);
}
