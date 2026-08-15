import { catalog } from "@/lib/catalog";

export function GET(request: Request) {
	const origin = new URL(request.url).origin;

	return Response.json(
		catalog.map((product) => ({
			id: product.id,
			name: product.name,
			product_url: `${origin}/product/${product.slug}`,
			images: product.images,
			image_kind: product.image_kind,
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
