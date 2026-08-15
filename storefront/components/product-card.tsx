import type {
	APICollectionGetByIdResult,
	APIProductGetByIdResult,
	APIProductsBrowseResult,
} from "commerce-kit";
import { PackageOpen } from "lucide-react";
import Link from "next/link";
import { getCatalogPurchase } from "@/lib/catalog";
import { formatMoney } from "@/lib/money";
import { getStoreConfig } from "@/lib/store-config";
import { isVideoUrl } from "@/lib/utils";
import { YNSMedia } from "@/lib/yns-media";
import { QuickAddButton } from "./quick-add-button";

type BrowseProduct = APIProductsBrowseResult["data"][number];
type CollectionProduct = APICollectionGetByIdResult["productCollections"][number]["product"];
type FullProduct = NonNullable<APIProductGetByIdResult>;

export async function ProductCard({
	product,
	priority = false,
}: {
	product: BrowseProduct | CollectionProduct | FullProduct;
	priority?: boolean;
}) {
	const { currency, locale } = await getStoreConfig();
	const variants = "variants" in product ? product.variants : null;
	const firstVariantPrice = variants?.[0] ? BigInt(variants[0].price) : null;
	const { minPrice, maxPrice } =
		variants && firstVariantPrice !== null
			? variants.reduce(
					(acc, v) => {
						const price = BigInt(v.price);
						return {
							minPrice: price < acc.minPrice ? price : acc.minPrice,
							maxPrice: price > acc.maxPrice ? price : acc.maxPrice,
						};
					},
					{ minPrice: firstVariantPrice, maxPrice: firstVariantPrice },
				)
			: { minPrice: null, maxPrice: null };

	const priceDisplay =
		variants && variants.length > 1 && minPrice && maxPrice && minPrice !== maxPrice
			? `${formatMoney({ amount: minPrice, currency, locale })} - ${formatMoney({ amount: maxPrice, currency, locale })}`
			: minPrice
				? formatMoney({ amount: minPrice, currency, locale })
				: null;

	const allImages = [
		...(product.images ?? []),
		...(variants?.flatMap((v) => v.images ?? []).filter((img) => !(product.images ?? []).includes(img)) ??
			[]),
	];
	const primaryImage = allImages[0];
	const secondaryImage = allImages[1];
	const catalogPurchase = getCatalogPurchase(product);

	const singleVariant =
		!catalogPurchase && variants?.length === 1 && variants[0]?.stock !== 0 ? variants[0] : null;

	return (
		<Link href={`/product/${product.slug}`} className="group min-w-0">
			<div className="relative mb-3 aspect-square overflow-hidden rounded-[1.25rem] border border-border bg-secondary sm:mb-4 sm:rounded-[1.5rem]">
				<div className="pointer-events-none absolute inset-0 z-[1] bg-linear-to-t from-black/20 via-transparent to-white/[0.04] opacity-60" />
				{catalogPurchase?.catalogMode === "live" && (
					<span className="absolute left-2.5 top-2.5 z-10 rounded-full border border-white/15 bg-black/70 px-2.5 py-1 text-[0.58rem] font-semibold uppercase tracking-[0.12em] text-white/80 backdrop-blur-md sm:left-3 sm:top-3">
						Secure Stripe checkout
					</span>
				)}
				{singleVariant && (
					<QuickAddButton
						variantId={singleVariant.id}
						variantSku={"sku" in singleVariant ? singleVariant.sku : null}
						variantPrice={singleVariant.price}
						variantImages={singleVariant.images}
						product={{
							id: product.id,
							name: product.name,
							slug: product.slug,
							images: product.images ?? [],
						}}
					/>
				)}
				{primaryImage &&
					(isVideoUrl(primaryImage) ? (
						<video
							className={`absolute inset-0 w-full h-full object-cover transition-opacity duration-500 ${secondaryImage ? "group-hover:opacity-0" : ""}`}
							src={primaryImage}
							muted
							loop
							autoPlay
							playsInline
						/>
					) : (
						<YNSMedia
							src={primaryImage}
							alt={product.name}
							fill
							sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
							className={`object-cover transition-opacity duration-500 ${secondaryImage ? "group-hover:opacity-0" : ""}`}
							priority={priority}
						/>
					))}
				{secondaryImage &&
					(isVideoUrl(secondaryImage) ? (
						<video
							className="absolute inset-0 w-full h-full object-cover opacity-0 transition-opacity duration-500 group-hover:opacity-100"
							src={secondaryImage}
							muted
							loop
							autoPlay
							playsInline
						/>
					) : (
						<YNSMedia
							src={secondaryImage}
							alt={`${product.name} - alternate view`}
							fill
							sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
							className="object-cover opacity-0 transition-opacity duration-500 group-hover:opacity-100"
						/>
					))}
				{!primaryImage && (
					<div className="absolute inset-0 grid place-items-center bg-[radial-gradient(circle_at_center,rgba(190,242,100,0.16),transparent_46%)] text-center text-white/50">
						<div>
							<PackageOpen className="mx-auto size-14 text-lime-300/65" aria-hidden="true" />
							<p className="mt-3 text-xs">Product image coming soon</p>
						</div>
					</div>
				)}
			</div>
			<div className="flex items-start justify-between gap-2 px-0.5">
				<h3 className="line-clamp-2 min-w-0 text-sm font-medium leading-snug text-foreground sm:text-base">
					{product.name}
				</h3>
				<p className="shrink-0 text-sm font-semibold text-lime-300 sm:text-base">{priceDisplay}</p>
			</div>
			<p className="mt-1.5 hidden text-xs text-muted-foreground sm:block">View details →</p>
		</Link>
	);
}
