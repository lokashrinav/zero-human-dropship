"""Jac-first product ranking, copy generation, and deterministic validation."""

import json;
import math;
import os;
import time;
import pioneer_bridge;
import from datetime { datetime, timezone }


glob DECODER_MODEL: str = "openai/gpt-oss-120b",
     FASTINO_MODEL: str = "fastino/gliner2-large-v1",
     FORBIDDEN_CLAIMS: list[str] = [
         "5-star",
         "five-star",
         "best seller",
         "bestseller",
         "customers love",
         "thousands sold",
         "in stock",
         "limited stock",
         "only one left",
         "only 1 left",
         "free shipping",
         "same-day shipping",
         "next-day shipping",
         "ships in",
         "delivery in",
         "% off",
         "discount",
         "clinically proven",
         "guaranteed results",

     ];


obj Product {
    has id: str,
        name: str,
        supplier_cost: float,
        raw_description: str,
        images: list[str] = [];

    def source_text -> str {
        return f"{self.name} {self.raw_description}".lower();
    }

    def to_prompt_dict -> dict[str, object] {
        return {
            "id": self.id,
            "name": self.name,
            "supplier_cost": self.supplier_cost,
            "raw_description": self.raw_description,
            "image_count": len(self.images),

        };
    }
}


obj RankedProduct {
    has id: str,
        score: int,
        suggested_title: str,
        suggested_description: str,
        suggested_price: float,
        reason: str,
        risk_flags: list[str] = [];

    def to_dict -> dict[str, object] {
        return {
            "id": self.id,
            "score": self.score,
            "suggested_title": self.suggested_title,
            "suggested_description": self.suggested_description,
            "suggested_price": self.suggested_price,
            "reason": self.reason,
            "risk_flags": self.risk_flags,

        };
    }
}


obj RankResponse {
    has status: str,
        ranked_products: list[RankedProduct],
        model: str,
        generated_at: str,
        fastino_model: str,
        fastino_status: str,
        error: str | None = None;

    def to_dict -> dict[str, object] {
        return {
            "status": self.status,
            "ranked_products": [p.to_dict() for p in self.ranked_products],
            "model": self.model,
            "generated_at": self.generated_at,
            "fastino_model": self.fastino_model,
            "fastino_status": self.fastino_status,
            "error": self.error,

        };
    }

    def to_json -> str {
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) as str;
    }
}


obj ModelProposal {
    has id: str,
        score: int,
        suggested_title: str,
        suggested_description: str,
        model_suggested_price: float,
        reason: str,
        model_risk_flags: list[str] = [];
}


obj RunEvidence {
    has status: str,
        model: str,
        products_considered: int,
        top_ranking: str,
        latency_ms: int,
        timestamp: str,
        fastino_step: str,
        error: str | None = None;

    def to_dict -> dict[str, object] {
        return {
            "status": self.status,
            "model": self.model,
            "products_considered": self.products_considered,
            "top_ranking": self.top_ranking,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "fastino_step": self.fastino_step,
            "error": self.error,

        };
    }
}


obj ServiceStatus {
    has status: str,
        catalog_reachable: bool,
        inference_live: bool,
        model: str,
        fastino_model: str,
        latest_recommendation: str,
        last_run_at: str,
        error: str | None = None;
}


obj ModelInfo {
    has decoder_model: str,
        decoder_supports_inference: bool,
        decoder_is_open_weight: bool,
        decoder_license: str,
        fastino_model: str,
        fastino_supports_inference: bool,
        catalog_checked_at: str,
        catalog_reachable: bool;
}


def utc_now -> str {
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") as str;
}


def safe_error(error: Exception) -> str {
    key = os.environ.get("PIONEER_API_KEY", "");
    message = str(error);
    if key {
        message = message.replace(key, "[redacted]");
    }
    return message[:300];
}


def validate_inputs(products: list[Product], goal: str) {
    if not products {
        raise ValueError("products must contain at least one item");
    }
    if not goal.strip() {
        raise ValueError("goal must not be empty");
    }
    seen: set[str] = set();
    for product in products {
        if not product.id.strip() or not product.name.strip() {
            raise ValueError("every product needs a non-empty id and name");
        }
        if product.id in seen {
            raise ValueError(f"duplicate product id: {product.id}");
        }
        if product.supplier_cost < 0.0 or not math.isfinite(product.supplier_cost) {
            raise ValueError(f"invalid supplier_cost for {product.id}");
        }
        if not product.raw_description.strip() {
            raise ValueError(f"raw_description is required for {product.id}");
        }
        seen.add(product.id);
    }
}


def build_system_prompt -> str {
    return """You are a conservative ecommerce product analyst. Rank only the supplied products for the supplied goal. Return JSON only with a ranked_products array. Every supplied id must appear exactly once. Each item must contain id, integer score from 0 to 100, suggested_title, suggested_description, suggested_price as a JSON number without a currency symbol, reason, and risk_flags. Never invent or imply supplier cost, inventory, product features, reviews, customer counts, discounts, availability, certifications, warranties, or shipping times. Copy may use only facts stated in name or raw_description. Image URLs are not inspected. Prefer clear, restrained copy and explain ranking using only supplied facts.""";
}


def build_user_prompt(products: list[Product], goal: str) -> str {
    payload: dict[str, object] = {
        "goal": goal,
        "products": [p.to_prompt_dict() for p in products],

    };
    source_json = json.dumps(payload, ensure_ascii=False) as str;
    return f"Rank these source-of-truth products. Do not add facts. SOURCE_JSON:\n{source_json}";
}


def _as_dict(value: object, field: str) -> dict[str, object] {
    if not isinstance(value, dict) {
        raise ValueError(f"{field} must be an object");
    }
    return value as dict[str, object];
}


def _as_list(value: object, field: str) -> list[object] {
    if not isinstance(value, list) {
        raise ValueError(f"{field} must be an array");
    }
    return value as list[object];
}


def _as_str(value: object, field: str) -> str {
    if not isinstance(value, str) or not value.strip() {
        raise ValueError(f"{field} must be a non-empty string");
    }
    return value.strip();
}


def _as_float(value: object, field: str) -> float {
    if isinstance(value, bool) or not isinstance(value, (int, float)) {
        raise ValueError(f"{field} must be numeric");
    }
    parsed = float(value);
    if not math.isfinite(parsed) {
        raise ValueError(f"{field} must be finite");
    }
    return parsed;
}


def _as_price(value: object, field: str) -> float {
    if isinstance(value, str) {
        cleaned = value.strip().replace(",", "");
        if cleaned.startswith("$") {
            cleaned = cleaned[1:].strip();
        }
        parsed = float(cleaned);
        if not math.isfinite(parsed) {
            raise ValueError(f"{field} must be finite");
        }
        return parsed;
    }
    return _as_float(value, field);
}


def _optional_string_list(value: object | None) -> list[str] {
    if value is None {
        return [];
    }
    values = _as_list(value, "risk_flags");
    output: list[str] = [];
    for item in values {
        if isinstance(item, str) and item.strip() {
            output.append(item.strip()[:80]);
        }
    }
    return output;
}


def _find_char(value: str, char: str) -> int {
    try {
        return value.index(char);
    } except ValueError {
        return -1;
    }
}


def parse_decoder_output(raw: str) -> list[ModelProposal] {
    cleaned = raw.strip();
    if cleaned.startswith("```") {
        first_newline = _find_char(cleaned, "\n");
        if first_newline >= 0 {
            cleaned = cleaned[first_newline + 1:];
        }
        if cleaned.endswith("```") {
            cleaned = cleaned[:-3];
        }
    }
    start = _find_char(cleaned, "{");
    finish = cleaned.rfind("}");
    if start < 0 or finish <= start {
        raise ValueError("decoder returned no JSON object");
    }
    payload = json.loads(cleaned[start:finish + 1]) as dict[str, object];
    rows = _as_list(payload.get("ranked_products"), "ranked_products");
    proposals: list[ModelProposal] = [];
    for (index, row) in enumerate(rows) {
        item = _as_dict(row, f"ranked_products[{index}]");
        score_float = _as_float(item.get("score"), "score");
        score = int(round(score_float));
        if score < 0 or score > 100 {
            raise ValueError("score must be between 0 and 100");
        }
        proposals.append(
            ModelProposal(
                id=_as_str(item.get("id"), "id"),
                score=score,
                suggested_title=_as_str(item.get("suggested_title"), "suggested_title")[:120],
                suggested_description=_as_str(
                    item.get("suggested_description"), "suggested_description"
                )[:600],
                model_suggested_price=_as_price(
                    item.get("suggested_price"), "suggested_price"
                ),
                reason=_as_str(item.get("reason"), "reason")[:300],
                model_risk_flags=_optional_string_list(item.get("risk_flags")),
            )
        );
    }
    return proposals;
}


def _price_cap(goal: str) -> float | None {
    marker = _find_char(goal, "$");
    if marker < 0 {
        return None;
    }
    digits = "";
    for char in goal[marker + 1:] {
        if char.isdigit() or (char == "." and "." not in digits) {
            digits += char;
        } else {
            break;
        }
    }
    if not digits {
        return None;
    }
    try {
        cap = float(digits);
        return cap if cap > 0.0 else None;
    } except ValueError {
        return None;
    }
}


def deterministic_price(product: Product, score: int, goal: str) -> tuple[float, bool] {
    candidate = max(product.supplier_cost * 2.5, product.supplier_cost + 3.5);
    if score >= 85 {
        candidate *= 1.05;
    }
    price = float(math.floor(candidate)) + 0.99;
    if price < candidate {
        price += 1.0;
    }
    cap = _price_cap(goal);
    if cap is not None and price >= cap {
        price = max(0.99, cap - 0.01);
    }
    price = round(price, 2);
    return (price, price <= product.supplier_cost);
}


def _normalize(value: str) -> str {
    return " ".join("".join(c if c.isalnum() else " " for c in value.lower()).split());
}


def source_supports_claim(product: Product, claim: str) -> bool {
    normalized_claim = _normalize(claim);
    normalized_source = _normalize(product.source_text());
    if not normalized_claim {
        return True;
    }
    if normalized_claim in normalized_source {
        return True;
    }
    claim_tokens = [
        token
        for token in normalized_claim.split()
        if len(token) >= 3
    ];
    return bool(claim_tokens)
    and all(token in normalized_source.split() for token in claim_tokens);
}


def deterministic_claim_flags(text: str) -> list[str] {
    lowered = text.lower();
    return [
        f"forbidden_claim:{claim}"
        for claim in FORBIDDEN_CLAIMS
        if claim in lowered
    ];
}


def _find_entities(value: object, depth: int = 0) -> list[dict[str, object]] {
    if depth > 4 or not isinstance(value, dict) {
        return [];
    }
    data = value as dict[str, object];
    entities = data.get("entities");
    if isinstance(entities, list) {
        return [
            item as dict[str, object]
            for item in entities
            if isinstance(item, dict)
        ];
    }
    for key in ["result", "output", "data", "prediction"] {
        nested = data.get(key);
        found = _find_entities(nested, depth + 1);
        if found {
            return found;
        }
    }
    return [];
}


def fastino_claim_flags(product: Product, raw: str) -> list[str] {
    if not raw.strip() {
        return [];
    }
    payload = json.loads(raw) as object;
    flags: list[str] = [];
    for entity in _find_entities(payload) {
        text_value = entity.get("text") or entity.get("span") or entity.get("entity");
        label_value = entity.get("label") or entity.get("type") or "claim";
        if isinstance(text_value, str) and text_value.strip() {
            claim = text_value.strip();
            label = label_value if isinstance(label_value, str) else "claim";
            if not source_supports_claim(product, claim) {
                flags.append(f"unsupported_claim:{label}:{claim[:50]}");
            }
        }
    }
    return flags;
}


def _deduplicate_flags(flags: list[str]) -> list[str] {
    output: list[str] = [];
    for flag in flags {
        clean = " ".join(flag.replace("\n", " ").split())[:120];
        if clean and clean not in output {
            output.append(clean);
        }
    }
    return output;
}


def validate_proposals(
    products: list[Product],
    goal: str,
    proposals: list[ModelProposal],
    fastino_payloads: dict[str, str],
    fastino_available: bool,
) -> list[RankedProduct] {
    by_id: dict[str, Product] = {product.id: product for product in products};
    if len(proposals) != len(products) {
        raise ValueError("decoder must return every supplied product exactly once");
    }
    seen: set[str] = set();
    ranked: list[RankedProduct] = [];
    for proposal in proposals {
        if proposal.id in seen or proposal.id not in by_id {
            raise ValueError(
                f"decoder returned duplicate or unknown id: {proposal.id}"
            );
        }
        seen.add(proposal.id);
        product = by_id[proposal.id];
        combined = f"{proposal.suggested_title} {proposal.suggested_description} {proposal.reason}";
        flags = [f"model:{flag}" for flag in proposal.model_risk_flags];
        flags.extend(deterministic_claim_flags(combined));
        if fastino_available {
            flags.extend(
                fastino_claim_flags(product, fastino_payloads.get(product.id, ""))
            );
        } else {
            flags.append("fastino_unavailable");
        }
        (price, margin_conflict) = deterministic_price(product, proposal.score, goal);
        if margin_conflict {
            flags.append("price_goal_margin_conflict");
        }
        flags = _deduplicate_flags(flags);
        critical = any(
            flag.startswith("forbidden_claim:")
            or flag.startswith("unsupported_claim:")
            or flag == "fastino_unavailable" for flag in flags
        );
        title = product.name if critical else proposal.suggested_title;
        description = (
            product.raw_description if critical else proposal.suggested_description
        );
        reason = proposal.reason;
        if critical {
            flags.append("model_copy_replaced_with_source");
            reason = "Pioneer ranked this source product, but deterministic validation replaced unsupported generated copy with source text.";
        }
        ranked.append(
            RankedProduct(
                id=product.id,
                score=proposal.score,
                suggested_title=title,
                suggested_description=description,
                suggested_price=price,
                reason=reason,
                risk_flags=_deduplicate_flags(flags),
            )
        );
    }
    if seen != set(by_id.keys()) {
        raise ValueError("decoder omitted one or more supplied products");
    }
    ranked.sort(key=lambda (item: RankedProduct) { item.score; }, reverse=True);
    return ranked;
}


def _record(evidence: RunEvidence) {
    pioneer_bridge.append_evidence_json(
        json.dumps(evidence.to_dict(), ensure_ascii=False) as str
    );
}


def _rank_products_live(products: list[Product], goal: str) -> RankResponse {
    validate_inputs(products, goal);
    started = time.perf_counter();
    generated_at = utc_now();
    try {
        raw = pioneer_bridge.call_decoder(
            DECODER_MODEL,
            build_system_prompt(),
            build_user_prompt(products, goal),
            4000,
        );
    } except Exception as error {
        message = safe_error(error);
        _record(
            RunEvidence(
                status="pioneer_unavailable",
                model=DECODER_MODEL,
                products_considered=len(products),
                top_ranking="",
                latency_ms=int((time.perf_counter() - started) * 1000.0),
                timestamp=generated_at,
                fastino_step="not_run",
                error=message,
            )
        );
        return RankResponse(
            status="pioneer_unavailable",
            ranked_products=[],
            model=DECODER_MODEL,
            generated_at=generated_at,
            fastino_model=FASTINO_MODEL,
            fastino_status="not_run",
            error=message,
        );
    }
    try {
        proposals = parse_decoder_output(raw);
        product_map: dict[str, Product] = {product.id: product for product in products};
        fastino_payloads: dict[str, str] = {};
        fastino_available = True;
        for proposal in proposals {
            product = product_map.get(proposal.id);
            if product is None {
                continue;
            }
            validation_text = f"Title: {proposal.suggested_title}\nDescription: {proposal.suggested_description}\nReason: {proposal.reason}";
            try {
                fastino_payloads[proposal.id] = pioneer_bridge.call_gliner(
                    FASTINO_MODEL, validation_text
                );
            } except Exception {
                fastino_available = False;
                fastino_payloads[proposal.id] = "";
            }
        }
        ranked = validate_proposals(
            products, goal, proposals, fastino_payloads, fastino_available
        );
    } except Exception as error {
        message = safe_error(error);
        _record(
            RunEvidence(
                status="pioneer_invalid_response",
                model=DECODER_MODEL,
                products_considered=len(products),
                top_ranking="",
                latency_ms=int((time.perf_counter() - started) * 1000.0),
                timestamp=generated_at,
                fastino_step="failed_or_incomplete",
                error=message,
            )
        );
        return RankResponse(
            status="pioneer_invalid_response",
            ranked_products=[],
            model=DECODER_MODEL,
            generated_at=generated_at,
            fastino_model=FASTINO_MODEL,
            fastino_status="failed_or_incomplete",
            error=message,
        );
    }
    fastino_status = "validated" if fastino_available else "unavailable";
    top = f"{ranked[0].id} ({ranked[0].score})" if ranked else "";
    _record(
        RunEvidence(
            status="ok",
            model=DECODER_MODEL,
            products_considered=len(products),
            top_ranking=top,
            latency_ms=int((time.perf_counter() - started) * 1000.0),
            timestamp=generated_at,
            fastino_step=fastino_status,
        )
    );
    return RankResponse(
        status="ok",
        ranked_products=ranked,
        model=DECODER_MODEL,
        generated_at=generated_at,
        fastino_model=FASTINO_MODEL,
        fastino_status=fastino_status,
    );
}


def _generate_copy_live(product: Product, goal: str) -> RankResponse {
    return _rank_products_live([product], goal);
}


def _run_from_dict(data: dict[str, object]) -> RunEvidence {
    return RunEvidence(
        status=str(data.get("status", "unknown")),
        model=str(data.get("model", "")),
        products_considered=int(data.get("products_considered", 0)),
        top_ranking=str(data.get("top_ranking", "")),
        latency_ms=int(data.get("latency_ms", 0)),
        timestamp=str(data.get("timestamp", "")),
        fastino_step=str(data.get("fastino_step", "not_run")),
        error=str(data.get("error")) if data.get("error") is not None else None,
    );
}


def _get_recent_runs(limit: int = 20) -> list[RunEvidence] {
    bounded = max(1, min(limit, 100));
    rows = json.loads(pioneer_bridge.read_recent_evidence_json(bounded)) as list[
        object
    ];
    return [
        _run_from_dict(row as dict[str, object])
        for row in rows
        if isinstance(row, dict)
    ];
}


def _catalog_model_ids -> set[str] {
    payload = json.loads(pioneer_bridge.fetch_model_catalog()) as dict[str, object];
    rows = _as_list(payload.get("models"), "models");
    ids: set[str] = set();
    for row in rows {
        if isinstance(row, dict) {
            item = row as dict[str, object];
            model_id = item.get("id") or item.get("model_id") or item.get("name");
            supports_inference = item.get("supports_inference");
            if (
                isinstance(model_id, str)
                and isinstance(supports_inference, bool)
                and supports_inference
            ) {
                ids.add(model_id);
            }
        }
    }
    return ids;
}


def _get_model_info -> ModelInfo {
    checked_at = utc_now();
    try {
        ids = _catalog_model_ids();
        reachable = True;
    } except Exception {
        ids = set();
        reachable = False;
    }
    return ModelInfo(
        decoder_model=DECODER_MODEL,
        decoder_supports_inference=DECODER_MODEL in ids,
        decoder_is_open_weight=True,
        decoder_license="Apache-2.0",
        fastino_model=FASTINO_MODEL,
        fastino_supports_inference=FASTINO_MODEL in ids,
        catalog_checked_at=checked_at,
        catalog_reachable=reachable,
    );
}


def _get_service_status -> ServiceStatus {
    model_info = _get_model_info();
    runs = _get_recent_runs(1);
    latest = runs[0] if runs else None;
    if not model_info.catalog_reachable {
        state = "pioneer_unavailable";
    } elif latest is None {
        state = "ready_unproven";
    } else {
        state = "live" if latest.status == "ok" else latest.status;
    }
    return ServiceStatus(
        status=state,
        catalog_reachable=model_info.catalog_reachable,
        inference_live=latest is not None and latest.status == "ok",
        model=DECODER_MODEL,
        fastino_model=FASTINO_MODEL,
        latest_recommendation=latest.top_ranking if latest is not None else "",
        last_run_at=latest.timestamp if latest is not None else "",
        error=latest.error if latest is not None else None,
    );
}
