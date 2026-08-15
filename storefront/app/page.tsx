import { Suspense } from "react";
import { ProductGridSkeleton } from "@/components/product-grid-skeleton";
import { AiSalesCta } from "@/components/sections/ai-sales-cta";
import { Hero } from "@/components/sections/hero";
import { HowItWorks } from "@/components/sections/how-it-works";
import { ProductGrid } from "@/components/sections/product-grid";

function FeaturedProductsSkeleton() {
	return (
		<section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-24 lg:px-8">
			<div className="mb-10 flex items-end justify-between">
				<div>
					<div className="h-8 w-48 animate-pulse rounded bg-secondary" />
					<div className="mt-2 h-5 w-64 animate-pulse rounded bg-secondary" />
				</div>
			</div>
			<ProductGridSkeleton className="lg:grid-cols-3" />
		</section>
	);
}

export default function Home() {
	return (
		<>
			<Hero />
			<Suspense fallback={<FeaturedProductsSkeleton />}>
				<ProductGrid
					title="Worth the upgrade"
					description="Useful objects, filtered hard. No clutter, no filler."
					limit={6}
				/>
			</Suspense>
			<AiSalesCta />
			<HowItWorks />
		</>
	);
}
