export const orderProductsByIdRanking = <Product extends { id: string }>(
	products: readonly Product[],
	ranking: readonly string[],
) => {
	const rankById = new Map(ranking.map((id, index) => [id, index] as const));

	return products
		.map((product, originalIndex) => ({
			originalIndex,
			product,
			rank: rankById.get(product.id),
		}))
		.sort((left, right) => {
			if (left.rank === undefined && right.rank === undefined) {
				return left.originalIndex - right.originalIndex;
			}
			if (left.rank === undefined) return 1;
			if (right.rank === undefined) return -1;
			return left.rank - right.rank || left.originalIndex - right.originalIndex;
		})
		.map(({ product }) => product);
};
