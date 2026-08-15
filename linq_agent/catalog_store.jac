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


def _validated_store_base(public_store_url: str) -> str {
    base = public_store_url.strip().rstrip("/");
    parsed = urlparse(base);
    if not base
    or parsed.scheme != "https"
    or not parsed.hostname
    or parsed.username is not None
    or parsed.password is not None
    or parsed.path not in {"", "/"}
    or parsed.query
    or parsed.fragment {
        raise ValueError("PUBLIC_STORE_URL must be an absolute HTTPS origin");
    }
    return base;
}


def _product_slug(name: str) -> str {
    normalized = re.sub(r"^development product\s*[—-]\s*", "", name.casefold()) as str;
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") as str;
    if not slug {
        raise ValueError("Catalog product name cannot produce a storefront slug");
    }
    return slug;
}


def _validated_product_url(
    item: dict[str, object], name: str, public_store_url: str
) -> str {
    store_base = _validated_store_base(public_store_url)
        if public_store_url.strip()
        else "";
    raw_url = item.get("product_url");
    if raw_url is None {
        if not store_base {
            raise ValueError(
                "Catalog requires product_url or a configured PUBLIC_STORE_URL"
            );
        }
        return f"{store_base}/product/{_product_slug(name)}";
    }
    if not isinstance(raw_url, str) or not raw_url.strip() {
        raise ValueError("Catalog field 'product_url' must be a non-empty string");
    }
    product_url = raw_url.strip();
    parsed = urlparse(product_url);
    if parsed.scheme != "https"
    or not parsed.hostname
    or not parsed.path.startswith("/product/")
    or not parsed.path.removeprefix("/product/").strip("/")
    or parsed.username is not None
    or parsed.password is not None
    or parsed.query
    or parsed.fragment {
        raise ValueError("product_url must be an absolute HTTPS product page URL");
    }
    if store_base and parsed.netloc != urlparse(store_base).netloc {
        raise ValueError("product_url must use the configured storefront origin");
    }
    if "[" in product_url
    or "]" in product_url
    or "(" in product_url
    or ")" in product_url {
        raise ValueError("product_url must be a raw URL, not Markdown");
    }
    return product_url;
}


def validate_catalog_text(
    raw_text: str,
    source_path: str = "memory",
    allow_non_transactional: bool = False,
    require_active: bool = False,
    public_store_url: str = ""
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
        product_url = _validated_product_url(item, name, public_store_url);
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
                    product_url=product_url,
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
    digest_input = (
        raw_text + "\npublic_store_url=" + public_store_url.strip().rstrip("/")
    );
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest() as str;
    return CatalogSnapshot(
        products=products,
        version=f"sha256:{digest}",
        source_path=source_path,
        checkout_ready_products=checkout_ready
    );
}


def load_catalog_file(
    path: str, production_mode: bool = False, public_store_url: str = ""
) -> CatalogSnapshot {
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
        require_active=production_mode,
        public_store_url=public_store_url
    );
}
