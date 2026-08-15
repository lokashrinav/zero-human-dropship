"""HTTP endpoints for Pioneer-backed product intelligence."""

import from http { HTTPMethod }
import from product_intelligence {
    ModelInfo,
    Product,
    RankResponse,
    RunEvidence,
    ServiceStatus,
    _generate_copy_live,
    _get_model_info,
    _get_recent_runs,
    _get_service_status,
    _rank_products_live,
}


"""Rank supplied catalog products and generate deterministically checked copy."""
@restspec(method=HTTPMethod.POST, path="/rank-products")
def:pub rank_products(products: list[Product], goal: str) -> RankResponse {
    return _rank_products_live(products, goal);
}


"""Generate checked copy for one supplied catalog product."""
@restspec(method=HTTPMethod.POST, path="/generate-copy")
def:pub generate_copy(product: Product, goal: str) -> RankResponse {
    return _generate_copy_live(product, goal);
}


"""Return catalog reachability and latest proven inference state."""
@restspec(method=HTTPMethod.GET, path="/status")
def:pub status -> ServiceStatus {
    return _get_service_status();
}


"""Return exact selected models and their current catalog availability."""
@restspec(method=HTTPMethod.GET, path="/model-info")
def:pub model_info -> ModelInfo {
    return _get_model_info();
}


"""Return recent non-secret evidence for the judge dashboard."""
@restspec(method=HTTPMethod.GET, path="/recent-runs")
def:pub recent_runs(limit: int = 20) -> list[RunEvidence] {
    return _get_recent_runs(limit);
}
