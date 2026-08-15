import { catalog } from "@/lib/catalog";

export function GET() {
	return Response.json(
		catalog.map((product) => ({
			id: product.id,
			name: product.name,
			images: product.images,
			stripe_id: product.stripe_id,
			payment_link: product.payment_link,
			price: product.price,
			description: product.description,
			active: product.active,
		})),
		{
			headers: {
				"Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
			},
		},
	);
}
