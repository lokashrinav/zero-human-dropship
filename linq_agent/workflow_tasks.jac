import from catalog_store { validate_catalog_text }


def audit_catalog_for_workflow(catalog_json: str) -> dict[str, object] {
    snapshot = validate_catalog_text(catalog_json, source_path="render_workflow_input");
    return {
        "valid": True,
        "catalog_products": len(snapshot.products),
        "checkout_ready_products": snapshot.checkout_ready_products,
        "catalog_version": snapshot.version
    };
}
