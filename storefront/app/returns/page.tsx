import type { Metadata } from "next";

export const metadata: Metadata = {
	title: "Returns & refunds",
	description: "KOVA return and refund disclosure.",
};

export default function ReturnsPage() {
	const supportEmail = process.env.SUPPORT_EMAIL?.trim();

	return (
		<article className="prose prose-invert mx-auto max-w-3xl px-4 py-16 sm:px-6 sm:py-24">
			<p className="eyebrow text-lime-300">Store policy</p>
			<h1>Returns & refunds</h1>
			<p>
				Do not send an item back without return instructions. Contact KOVA
				{supportEmail ? (
					<>
						{" "}
						at <a href={`mailto:${supportEmail}`}>{supportEmail}</a>
					</>
				) : (
					" once the support contact shown on this site is available"
				)}{" "}
				and include your order reference, the item, and the reason for the request.
			</p>
			<p>
				Eligibility depends on the item condition, fulfillment status, and applicable consumer law. If a
				refund is approved, it is returned to the original payment method. Any product-specific terms are
				shown before purchase.
			</p>
		</article>
	);
}
