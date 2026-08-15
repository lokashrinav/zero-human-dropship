import { cacheLife } from "next/cache";
import Link from "next/link";
import { commerce, meGetCached } from "@/lib/commerce";

async function FooterContactLink() {
	"use cache";
	cacheLife("hours");
	const supportEmail = process.env.SUPPORT_EMAIL?.trim();
	if (supportEmail) {
		return (
			<li>
				<a href={`mailto:${supportEmail}`} className="footer-link">
					Contact support
				</a>
			</li>
		);
	}

	const me = await meGetCached().catch(() => null);
	if (!me?.store.settings?.enabledTools?.contactForm) {
		return null;
	}

	return (
		<li>
			<Link href="/contact" className="footer-link">
				Contact
			</Link>
		</li>
	);
}

async function FooterLegalPages() {
	"use cache";
	cacheLife("hours");

	const pages = await commerce.legalPageBrowse();
	if (pages.data.length === 0) {
		return null;
	}

	return pages.data.map((page) => (
		<li key={page.id}>
			<Link href={`/legal${page.href}`} className="footer-link">
				{page.label}
			</Link>
		</li>
	));
}

async function getCopyrightYear() {
	"use cache";
	cacheLife("days");

	return new Date().getFullYear();
}

export async function Footer() {
	const year = await getCopyrightYear();

	return (
		<footer className="border-t border-border bg-neutral-950">
			<div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
				<div className="grid gap-10 py-12 sm:grid-cols-[1.5fr_1fr_1fr] sm:py-16">
					<div className="max-w-md">
						<Link href="/" className="inline-flex items-center gap-2.5" aria-label="KOVA home">
							<span className="grid size-7 place-items-center rounded-lg bg-lime-300 text-[0.65rem] font-black tracking-[-0.08em] text-neutral-950">
								K/
							</span>
							<span className="text-lg font-semibold tracking-[-0.04em]">KOVA</span>
						</Link>
						<p className="mt-4 text-sm leading-6 text-muted-foreground">
							A focused edit of useful everyday objects. Product, shipping, and return details are confirmed
							before purchase.
						</p>
					</div>

					<div>
						<h3 className="eyebrow text-white/85">Explore</h3>
						<ul className="mt-4 space-y-3">
							<li>
								<Link href="/products" className="footer-link">
									All products
								</Link>
							</li>
							<li>
								<Link href="/#how-it-works" className="footer-link">
									How it works
								</Link>
							</li>
							<li>
								<Link href="/faq" className="footer-link">
									FAQ
								</Link>
							</li>
						</ul>
					</div>

					<div>
						<h3 className="eyebrow text-white/85">Support & policies</h3>
						<ul className="mt-4 space-y-3">
							<FooterContactLink />
							<FooterLegalPages />
							<li>
								<Link href="/shipping" className="footer-link">
									Shipping
								</Link>
							</li>
							<li>
								<Link href="/returns" className="footer-link">
									Returns & refunds
								</Link>
							</li>
						</ul>
						<p className="mt-5 text-xs leading-5 text-white/40">
							Shipping costs and estimates appear at checkout when available. Return eligibility varies by
							item; contact us before sending anything back.
						</p>
					</div>
				</div>

				<div className="flex flex-col gap-2 border-t border-border py-6 text-xs text-white/35 sm:flex-row sm:items-center sm:justify-between">
					<p>&copy; {year} KOVA. All rights reserved.</p>
					<p>Payments processed securely by Stripe.</p>
				</div>
			</div>
		</footer>
	);
}
