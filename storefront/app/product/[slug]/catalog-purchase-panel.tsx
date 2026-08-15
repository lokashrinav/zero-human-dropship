import { ExternalLink, LockKeyhole, PackageCheck } from "lucide-react";
import { formatMoney } from "@/lib/money";
import { getStoreConfig } from "@/lib/store-config";

export async function CatalogPurchasePanel({
	mode,
	paymentLink,
	price,
	summary,
}: {
	mode: "development" | "live";
	paymentLink: string | null;
	price: string;
	summary: string | null;
}) {
	const { currency, locale } = await getStoreConfig();
	const priceDisplay = formatMoney({ amount: price, currency, locale });
	const canPurchase = mode === "live" && Boolean(paymentLink);

	return (
		<div className="rounded-3xl border border-border bg-card/70 p-5 shadow-2xl shadow-black/15 sm:p-6">
			{summary && <p className="mb-6 max-w-xl text-base leading-7 text-muted-foreground">{summary}</p>}
			<div className="flex items-end justify-between gap-4">
				<div>
					<p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
						One-time purchase
					</p>
					<p className="mt-2 text-3xl font-semibold tracking-tight">{priceDisplay}</p>
				</div>
				<span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
					Physical item
				</span>
			</div>

			{canPurchase && paymentLink ? (
				<a
					href={paymentLink}
					className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-full bg-lime-300 px-6 py-3 text-sm font-semibold text-black transition hover:bg-lime-200"
				>
					Buy with secure Stripe checkout
					<ExternalLink className="h-4 w-4" />
				</a>
			) : (
				<button
					type="button"
					disabled
					className="mt-6 min-h-12 w-full cursor-not-allowed rounded-full border border-border bg-secondary px-6 py-3 text-sm font-semibold text-muted-foreground"
				>
					Checkout unavailable
				</button>
			)}

			<div className="mt-5 grid gap-3 text-xs leading-5 text-muted-foreground sm:grid-cols-2">
				<p className="flex gap-2">
					<LockKeyhole className="mt-0.5 h-4 w-4 shrink-0 text-lime-300" />
					Payment details are handled by Stripe, not stored by this storefront.
				</p>
				<p className="flex gap-2">
					<PackageCheck className="mt-0.5 h-4 w-4 shrink-0 text-lime-300" />
					Shipping options and delivery address are confirmed during checkout.
				</p>
			</div>
		</div>
	);
}
