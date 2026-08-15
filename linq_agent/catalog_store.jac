import hashlib;
import json;
import re;
import from pathlib { Path }
import from sales_logic { Product }
import from urllib.parse { urlparse }


obj CatalogSnapshot {
    has products: list[Product],
        version: str,
        source_path: str,
        checkout_ready_products: int;
}


def _required_text(item: dict[str, object], key: str) -> str {
    value = item.get(key);
    if not isinstance(value, str) or not value.strip() {
        raise ValueError(f"Catalog field '{key}' must be a non-empty string");
    }
    return value.strip();
}


def _money_to_cents(value: object, field_name: str, allow_zero: bool) -> int {
    if isinstance(value, bool) or not isinstance(value, (int, float)) {
        raise ValueError(f"Catalog field '{field_name}' must be a JSON number");
    }
    text = str(value);
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", text) {
        raise ValueError(
            f"Catalog field '{field_name}' must have at most two decimals"
        );
    }
    pieces = text.split(".");
    cents = int(pieces[0]) * 100;
    if len(pieces) == 2 {
        fraction = pieces[1];
        cents += int(fraction) * 10 if len(fraction) == 1 else int(fraction);
    }
    if cents < 0 or (not allow_zero and cents == 0) {
        raise ValueError(f"Catalog field '{field_name}' is outside the allowed range");
    }
    return cents;
}


def _validated_images(item: dict[str, object]) -> list[str] {
    raw_images = item.get("images");
    if not isinstance(raw_images, list) {
        raise ValueError("Catalog field 'images' must be an array");
    }
    images: list[str] = [];
    for raw_image in raw_images {
        if not isinstance(raw_image, str) or not raw_image.startswith("https://") {
            raise ValueError("Every catalog image must be an absolute HTTPS URL");
        }
        images.append(raw_image);
    }
    return images;
}


def _validated_payment_link(item: dict[str, object]) -> str {
    raw_link = item.get("payment_link");
    if not isinstance(raw_link, str) {
        raise ValueError("Catalog field 'payment_link' must be a string");
    }
    link = raw_link.strip();
    if not link {
        return "";
    }
    parsed = urlparse(link);
    if parsed.scheme != "https"
    or parsed.hostname != "buy.stripe.com"
    or not parsed.path.strip("/") {
        raise ValueError("payment_link must be an absolute https://buy.stripe.com URL");
    }
    if "[" in link or "]" in link or "(" in link or ")" in link {
        raise ValueError("payment_link must be a raw URL, not Markdown");
    }
    return link;
}


def validate_catalog_text(
    raw_text: str,
    source_path: str = "memory",
    allow_non_transactional: bool = False,
    require_active: bool = False
) -> CatalogSnapshot {
    parsed = json.loads(raw_text);
    if not isinstance(parsed, list) {
        raise ValueError("Catalog root must be a JSON array");
    }
    products: list[Product] = [];
    seen_ids: set[str] = set();
    checkout_ready = 0;
    for (index, raw_entry) in enumerate(parsed) {
        if not isinstance(raw_entry, dict) {
            raise ValueError(f"Catalog entry {index} must be an object");
        }
        item = raw_entry as dict[str, object];
        raw_active = item.get("active");
        if require_active and not isinstance(raw_active, bool) {
            raise ValueError(
                f"Catalog entry {index} must have a boolean active status"
            );
        }
        active = raw_active if isinstance(raw_active, bool) else True;
        name = _required_text(item, "name");
        stripe_id = _required_text(item, "stripe_id");
        if not stripe_id.startswith("prod_") {
            raise ValueError(f"Catalog entry {index} has an invalid Stripe product id");
        }
        if stripe_id in seen_ids {
            raise ValueError(f"Duplicate Stripe product id: {stripe_id}");
        }
        description = _required_text(item, "description");
        images = _validated_images(item);
        payment_link = _validated_payment_link(item);
        if not payment_link and not allow_non_transactional {
            raise ValueError(
                f"Catalog entry {index} must have a verified Stripe payment_link"
            );
        }
        raw_cost = item.get("cost");
        cost_cents = 0 if raw_cost is None else _money_to_cents(raw_cost, "cost", True);
        price_cents = _money_to_cents(item.get("price"), "price", False);
        if cost_cents > price_cents {
            raise ValueError(f"Catalog entry {index} has cost greater than price");
        }
        seen_ids.add(stripe_id);
        if active {
            products.append(
                Product(
                    name=name,
                    images=images,
                    stripe_id=stripe_id,
                    payment_link=payment_link,
                    cost_cents=cost_cents,
                    price_cents=price_cents,
                    description=description
                )
            );
            if payment_link {
                checkout_ready += 1;
            }
        }
    }
    if not products {
        raise ValueError("Catalog must contain at least one active product");
    }
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest() as str;
    return CatalogSnapshot(
        products=products,
        version=f"sha256:{digest}",
        source_path=source_path,
        checkout_ready_products=checkout_ready
    );
}


def load_catalog_file(path: str, production_mode: bool = False) -> CatalogSnapshot {
    catalog_path = Path(path);
    if not catalog_path.is_file() {
        raise FileNotFoundError(f"Catalog not found: {path}");
    }
    return validate_catalog_text(
        catalog_path.read_text(encoding="utf-8"),
        str(catalog_path),
        allow_non_transactional=(
            not production_mode and catalog_path.name == "catalog.example.json"
        ),
        require_active=production_mode
    );
}
