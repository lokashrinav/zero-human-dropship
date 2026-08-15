import type {
	APICollectionGetByIdResult,
	APIProductGetByIdResult,
	APIProductsBrowseResult,
} from "commerce-kit";
import { ArrowRight } from "lucide-react";
import { cacheLife } from "next/cache";
import Link from "next/link";
import { ProductCard } from "@/components/product-card";
import { commerce } from "@/lib/commerce";

export type Product = APIProductsBrowseResult["data"][number];

type ProductGridProps = {
	title?: string;
	description?: string;
	products?: (
		| Product
		| APICollectionGetByIdResult["productCollections"][number]["product"]
		| NonNullable<APIProductGetByIdResult>
	)[];
	limit?: number;
	showViewAll?: boolean;
	viewAllHref?: string;
};

export async function ProductGrid({
	title = "Featured Products",
	description = "Handpicked favorites from our collection",
	products,
	limit = 6,
	showViewAll = true,
	viewAllHref = "/products",
}: ProductGridProps) {
	"use cache";
	cacheLife("minutes");

	const displayProducts = products ?? (await commerce.productBrowse({ active: true, limit })).data;

	return (
		<section id="products" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-12 sm:px-6 sm:py-20 lg:px-8">
			<div className="mb-7 flex items-end justify-between gap-8 sm:mb-10">
				<div>
					<p className="eyebrow text-lime-300">Curated now</p>
					<h2 className="mt-2 text-3xl font-semibold tracking-[-0.045em] text-foreground sm:text-5xl">
						{title}
					</h2>
					<p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground sm:text-base">{description}</p>
				</div>
				{showViewAll && (
					<Link
						href={viewAllHref}
						className="hidden items-center gap-1 border-b border-white/20 pb-1 text-sm font-medium text-muted-foreground transition-colors hover:border-lime-300 hover:text-foreground sm:inline-flex"
					>
						View all
						<ArrowRight className="h-4 w-4" />
					</Link>
				)}
			</div>

			<div className="grid grid-cols-2 gap-x-3 gap-y-7 sm:gap-x-5 sm:gap-y-10 lg:grid-cols-4">
				{displayProducts.map((product, index) => (
					<ProductCard key={product.id} product={product} priority={index === 0} />
				))}
			</div>

			{showViewAll && (
				<div className="mt-12 text-center sm:hidden">
					<Link
						href={viewAllHref}
						className="inline-flex h-11 items-center gap-1 rounded-full border border-border px-5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
					>
						View all products
						<ArrowRight className="h-4 w-4" />
					</Link>
				</div>
			)}
		</section>
	);
}
