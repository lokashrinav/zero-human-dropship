import type { LinqData, LinqEvent } from "../contracts";

const secondsAgo = (seconds: number) =>
	new Date(Date.now() - seconds * 1_000).toISOString();

export const linqFixture = (): LinqData => {
	const events: LinqEvent[] = [
		{
			id: "demo-linq-1",
			timestamp: secondsAgo(42),
			type: "inbound_message",
			stage: "sell",
			headline: "INBOUND MESSAGE",
			detail: "Mock shopper asked for a compact desk-cleaning product.",
			direction: "inbound",
		},
		{
			id: "demo-linq-2",
			timestamp: secondsAgo(34),
			type: "sales_agent",
			stage: "sell",
			headline: "SALES AGENT",
			detail: "Mock conversation intent classified.",
			direction: "internal",
		},
		{
			id: "demo-linq-3",
			timestamp: secondsAgo(26),
			type: "product_selected",
			stage: "sell",
			headline: "PRODUCT SELECTED",
			detail: "Pocket Desk Vacuum selected from mock catalog.",
			direction: "internal",
		},
		{
			id: "demo-linq-4",
			timestamp: secondsAgo(18),
			type: "payment_link_sent",
			stage: "sell",
			headline: "PAYMENT LINK SENT",
			detail: "Mock outbound payment-link event. No transaction occurred.",
			direction: "outbound",
		},
	];

	return {
		online: null,
		phoneNumber: null,
		conversations: 1,
		recommendations: 1,
		paymentLinksSent: 1,
		events,
	};
};
