import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Shipping",
	description: "KOVA shipping disclosure.",
};

export default function ShippingPage() {
	return (
		<article className="prose prose-invert mx-auto max-w-3xl px-4 py-16 sm:px-6 sm:py-24">
			<p className="eyebrow text-lime-300">Store policy</p>
			<h1>Shipping</h1>
			<p>
				Available destinations, shipping charges, and any delivery estimate are shown during checkout before
				payment. We do not promise a delivery date that has not been confirmed by the checkout flow.
			</p>
			<p>
				Physical orders require a delivery address. Please check that address carefully before placing an
				order. Live fulfillment and tracking details will be sent through the contact information collected at
				checkout.
			</p>
		</article>
	);
}
