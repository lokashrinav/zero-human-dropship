import re;


enum Intent: str {
    GREETING = "greeting",
    DISCOVERY = "discovery",
    PRODUCT_SEARCH = "product_search",
    PRODUCT_QUESTION = "product_question",
    CHECKOUT_REQUEST = "checkout_request",
    ACKNOWLEDGEMENT = "acknowledgement",
    UNKNOWN = "unknown",
    OPT_OUT = "opt_out",
    RESUME = "resume"
}


obj Product {
    has name: str,
        images: list[str],
        stripe_id: str,
        product_url: str,
        payment_link: str,
        cost_cents: int,
        price_cents: int,
        description: str;
}


obj ModelDecision {
    has intent: str,
        recommended_product_ids: list[str],
        reply_text: str,
        should_send_checkout: bool,
        reason: str;
}


sem ModelDecision.intent = "One of greeting, discovery, product_search, product_question, checkout_request, acknowledgement, unknown, opt_out, resume.";
sem ModelDecision.recommended_product_ids = "Zero to three stripe_id values copied exactly from the provided catalog candidates. Never invent an identifier.";
sem ModelDecision.reply_text = "A concise suggestion with no URL, payment link, price, inventory claim, policy, or unsupported fact.";
sem ModelDecision.should_send_checkout = "Whether the customer explicitly asks to buy or check out a grounded product. This is advisory only.";
sem ModelDecision.reason = "A short classification reason without hidden chain of thought.";


obj SalesPlan {
    has intent: str,
        product_ids: list[str],
        reply_text: str,
        should_send_checkout: bool,
        reason: str,
        used_model: bool = False;
}


glob STOP_WORDS: set[str] = {
         "a",
         "about",
         "actually",
         "also",
         "an",
         "and",
         "anything",
         "are",
         "as",
         "at",
         "be",
         "below",
         "budget",
         "buy",
         "can",
         "cheaper",
         "cool",
         "could",
         "do",
         "does",
         "dollar",
         "dollars",
         "find",
         "for",
         "from",
         "get",
         "give",
         "have",
         "help",
         "i",
         "ignore",
         "in",
         "instructions",
         "is",
         "it",
         "item",
         "invent",
         "key",
         "keys",
         "less",
         "looking",
         "max",
         "me",
         "need",
         "of",
         "on",
         "or",
         "please",
         "price",
         "recommend",
         "reveal",
         "sell",
         "show",
         "something",
         "than",
         "that",
         "the",
         "to",
         "under",
         "up",
         "want",
         "what",
         "whats",
         "with",
         "you",
         "your"
     };


def normalize_text(text: str) -> str {
    lowered = text.casefold();
    return re.sub(r"[^a-z0-9$.' -]+", " ", lowered) as str;
}


def money_text_to_cents(text: str) -> int {
    pieces = text.split(".");
    dollars = int(pieces[0]);
    cents = 0;
    if len(pieces) > 1 {
        fraction = pieces[1];
        if len(fraction) == 1 {
            cents = int(fraction) * 10;
        } elif len(fraction) >= 2 {
            cents = int(fraction[:2]);
        }
    }
    return dollars * 100 + cents;
}


def extract_budget_cents(message: str) -> tuple[int | None, bool] {
    normalized = normalize_text(message);
    budget_language = (
        "$" in normalized
        or "under" in normalized
        or "less than" in normalized
        or "below" in normalized
        or "up to" in normalized
        or "budget" in normalized
        or "max" in normalized
    );
    if not budget_language {
        return (None, False);
    }
    matches = re.findall(r"\$?\s*(\d+(?:\.\d{1,2})?)", normalized) as list[str];
    if not matches {
        return (None, False);
    }
    # The final stated amount wins, so an injection such as "invent a $1 item;
    # actually show something under $10" cannot override the user's request.
    amount = money_text_to_cents(matches[-1]);
    strict = "under" in normalized
    or "less than" in normalized
    or "below" in normalized;
    return (amount, strict);
}


def query_tokens(message: str) -> list[str] {
    tokens = re.findall(r"[a-z0-9]+", normalize_text(message)) as list[str];
    selected: list[str] = [];
    for token in tokens {
        if token not in STOP_WORDS and not token.isdigit() and len(token) > 1 {
            selected.append(token);
        }
    }
    return selected;
}


def is_stop_request(message: str) -> bool {
    normalized = " ".join(normalize_text(message).replace("-", " ").split());
    if normalized in {
        "stop",
        "unsubscribe",
        "optout",
        "opt out",
        "cancel",
        "end",
        "quit"
    } {
        return True;
    }
    return (
        "stop messaging" in normalized
        or "stop texting" in normalized
        or "do not message" in normalized
        or "don't message" in normalized
        or "do not text" in normalized
        or "don't text" in normalized
    );
}


def is_resume_request(message: str) -> bool {
    normalized = " ".join(normalize_text(message).split());
    return normalized in {"start", "resume", "unstop", "opt in", "optin"};
}


def infer_intent(message: str, last_product_ids: list[str]) -> str {
    normalized = normalize_text(message);
    collapsed = " ".join(normalized.split());
    if is_stop_request(message) {
        return Intent.OPT_OUT;
    }
    if is_resume_request(message) {
        return Intent.RESUME;
    }
    if any(
        phrase in normalized
        for phrase in [
            "buy it",
            "checkout",
            "check out",
            "payment link",
            "pay for",
            "order it",
            "i want it",
            "i'll take it",
            "ill take it",
            "i ll take it"
        ]
    ) {
        return Intent.CHECKOUT_REQUEST;
    }
    if collapsed in {"hello", "hi", "hey", "good morning", "good evening"} {
        return Intent.GREETING;
    }
    if any(
        phrase in normalized
        for phrase in ["thanks", "thank you", "got it", "i paid", "paid"]
    ) {
        return Intent.ACKNOWLEDGEMENT;
    }
    if extract_budget_cents(message)[0] is not None or len(query_tokens(message)) > 0 {
        if last_product_ids
        and any(
            phrase in normalized
            for phrase in ["how much", "describe", "what is", "available", "in stock"]
        ) {
            return Intent.PRODUCT_QUESTION;
        }
        return Intent.PRODUCT_SEARCH;
    }
    return Intent.UNKNOWN;
}


def product_by_id(products: list[Product], product_id: str) -> Product | None {
    for product in products {
        if product.stripe_id == product_id {
            return product;
        }
    }
    return None;
}


def named_product_in_message(products: list[Product], message: str) -> Product | None {
    normalized_message = " ".join(normalize_text(message).split());
    matches: list[Product] = [];
    for product in products {
        normalized_name = " ".join(normalize_text(product.name).split());
        if normalized_name and normalized_name in normalized_message {
            matches.append(product);
        }
    }
    return matches[0] if len(matches) == 1 else None;
}


def lexical_score(product: Product, tokens: list[str]) -> int {
    name = normalize_text(product.name);
    description = normalize_text(product.description);
    score = 0;
    for token in tokens {
        singular = token[:-1] if token.endswith("s") and len(token) > 3 else token;
        if token in name or singular in name {
            score += 100;
        } elif token in description or singular in description {
            score += 30;
        }
    }
    return score;
}


def product_precedes(
    left: Product,
    right: Product,
    tokens: list[str],
    budget_cents: int | None,
    cheapest: bool
) -> bool {
    left_score = lexical_score(left, tokens);
    right_score = lexical_score(right, tokens);
    if left_score != right_score {
        return left_score > right_score;
    }
    if cheapest and left.price_cents != right.price_cents {
        return left.price_cents < right.price_cents;
    }
    if budget_cents is not None and left.price_cents != right.price_cents {
        return left.price_cents > right.price_cents;
    }
    if left.name.casefold() != right.name.casefold() {
        return left.name.casefold() < right.name.casefold();
    }
    return left.stripe_id < right.stripe_id;
}


def rank_products(
    message: str, products: list[Product], limit: int = 3
) -> list[Product] {
    (budget_cents, strict_budget) = extract_budget_cents(message);
    tokens = query_tokens(message);
    eligible: list[Product] = [];
    for product in products {
        if budget_cents is not None {
            if strict_budget and product.price_cents >= budget_cents {
                continue;
            }
            if not strict_budget and product.price_cents > budget_cents {
                continue;
            }
        }
        eligible.append(product);
    }

    lexical_matches: list[Product] = [];
    if tokens {
        for product in eligible {
            if lexical_score(product, tokens) > 0 {
                lexical_matches.append(product);
            }
        }
    }
    candidates: list[Product] = [];
    if lexical_matches {
        candidates = lexical_matches;
    } elif not tokens and budget_cents is not None {
        candidates = eligible;
    }
    if not tokens and budget_cents is None {
        candidates = [];
    }

    ordered: list[Product] = [];
    cheapest = "cheapest" in normalize_text(message);
    for product in candidates {
        inserted = False;
        index = 0;
        while index < len(ordered) {
            if product_precedes(
                product, ordered[index], tokens, budget_cents, cheapest
            ) {
                ordered.insert(index, product);
                inserted = True;
                break;
            }
            index += 1;
        }
        if not inserted {
            ordered.append(product);
        }
    }
    return ordered[:limit];
}


def price_text(price_cents: int) -> str {
    return f"${price_cents // 100}.{price_cents % 100:02d}";
}


def short_description(description: str, limit: int = 96) -> str {
    cleaned = " ".join(description.split());
    if not cleaned {
        return "";
    }
    first_sentence = cleaned.split(".")[0].strip();
    summary = f"{first_sentence}." if first_sentence else "";
    if len(summary) <= limit {
        return summary;
    }
    shortened = summary[:limit - 1].rstrip();
    return shortened + "…";
}


def render_recommendations(products: list[Product]) -> str {
    if not products {
        return "I couldn't find that in our current catalog. Try a broader category or budget, and I'll check again.";
    }
    if len(products) == 1 {
        product = products[0];
        lines: list[str] = [
            f"Best pick: {product.name} — {price_text(product.price_cents)}"
        ];
        summary = short_description(product.description);
        if summary {
            lines.append("");
            lines.append(f"{summary} Want this one?");
        }
        return "\n".join(lines);
    }
    lines: list[str] = [];
    index = 1;
    for product in products[:3] {
        lines.append(f"{index}. {product.name} — {price_text(product.price_cents)}");
        summary = short_description(product.description);
        if summary {
            lines.append(f"   {summary}");
        }
        index += 1;
    }
    lines.append("");
    lines.append(f"Best pick: {products[0].name}.");
    return "\n".join(lines);
}


def validate_model_selection(
    proposal: ModelDecision, eligible: list[Product]
) -> list[Product] | None {
    if len(proposal.recommended_product_ids) > 3 {
        return None;
    }
    selected: list[Product] = [];
    seen: set[str] = set();
    for product_id in proposal.recommended_product_ids {
        if product_id in seen {
            return None;
        }
        product = product_by_id(eligible, product_id);
        if product is None {
            return None;
        }
        seen.add(product_id);
        selected.append(product);
    }
    return selected;
}


def build_sales_plan(
    message: str,
    products: list[Product],
    last_product_ids: list[str] | None = None,
    model_proposal: ModelDecision | None = None
) -> SalesPlan {
    previous_product_ids: list[str] = last_product_ids or [];
    normalized = normalize_text(message);
    intent = infer_intent(message, previous_product_ids);
    if intent == Intent.OPT_OUT {
        return SalesPlan(
            intent=intent,
            product_ids=[],
            reply_text="You're opted out. I won't send sales messages. Text START if you want to resume.",
            should_send_checkout=False,
            reason="customer_opt_out"
        );
    }
    if intent == Intent.RESUME {
        return SalesPlan(
            intent=intent,
            product_ids=[],
            reply_text="You're opted back in. What are you looking for today?",
            should_send_checkout=False,
            reason="customer_resumed"
        );
    }
    if any(
        phrase in normalized
        for phrase in [
            "shipping",
            "refund",
            "return policy",
            "warranty",
            "delivery time"
        ]
    ) {
        return SalesPlan(
            intent=Intent.UNKNOWN,
            product_ids=[],
            reply_text="I don't have verified shipping, returns, warranty, or delivery terms in the catalog, so I won't guess. Please check the store policy page before purchasing.",
            should_send_checkout=False,
            reason="unverified_policy_question"
        );
    }
    named_product = named_product_in_message(products, message);
    if named_product is not None
    and any(
        phrase in normalized
        for phrase in ["how much", "describe", "what is", "available", "in stock"]
    ) {
        intent = Intent.PRODUCT_QUESTION;
    }
    if intent == Intent.GREETING or intent == Intent.UNKNOWN {
        return SalesPlan(
            intent=intent,
            product_ids=[],
            reply_text="Hi! Tell me what you're looking for or your budget, and I'll recommend something from our live catalog.",
            should_send_checkout=False,
            reason="needs_discovery"
        );
    }
    if intent == Intent.ACKNOWLEDGEMENT {
        return SalesPlan(
            intent=intent,
            product_ids=[],
            reply_text="Thanks! If you need another recommendation, just tell me a category or budget.",
            should_send_checkout=False,
            reason="acknowledgement_not_conversion"
        );
    }
    if intent == Intent.PRODUCT_QUESTION {
        questioned: Product | None = named_product
            if named_product is not None
            else (
                product_by_id(products, previous_product_ids[0])
                    if len(previous_product_ids) == 1
                    else None
            );
        if questioned is None and len(previous_product_ids) != 1 {
            return SalesPlan(
                intent=intent,
                product_ids=[],
                reply_text="Which catalog product do you mean? Reply with its exact name and I'll answer from the listing.",
                should_send_checkout=False,
                reason="ambiguous_product_question"
            );
        }
        if questioned is None {
            return SalesPlan(
                intent=intent,
                product_ids=[],
                reply_text="I can't verify that item in the current catalog. Tell me what you're looking for and I'll check again.",
                should_send_checkout=False,
                reason="prior_product_not_in_catalog"
            );
        }
        return SalesPlan(
            intent=intent,
            product_ids=[questioned.stripe_id],
            reply_text=f"{questioned.name} is currently listed in our catalog at {price_text(
                questioned.price_cents
            )}. {questioned.description}",
            should_send_checkout=False,
            reason="trusted_catalog_answer"
        );
    }
    if intent == Intent.CHECKOUT_REQUEST {
        checkout_product: Product | None = named_product
            if named_product is not None
            else (
                product_by_id(products, previous_product_ids[0])
                    if len(previous_product_ids) == 1
                    else None
            );
        if checkout_product is None and len(previous_product_ids) != 1 {
            return SalesPlan(
                intent=intent,
                product_ids=[],
                reply_text="Which product would you like to buy? Reply with its name and I'll send the verified checkout link.",
                should_send_checkout=False,
                reason="ambiguous_checkout"
            );
        }
        if checkout_product is None or not checkout_product.payment_link {
            return SalesPlan(
                intent=intent,
                product_ids=[],
                reply_text="That checkout isn't available right now. Tell me what else you'd like and I'll check the live catalog.",
                should_send_checkout=False,
                reason="checkout_unavailable"
            );
        }
        return SalesPlan(
            intent=intent,
            product_ids=[checkout_product.stripe_id],
            reply_text=f"Here's the verified checkout for {checkout_product.name} at {price_text(
                checkout_product.price_cents
            )}.",
            should_send_checkout=True,
            reason="exact_prior_product"
        );
    }

    ranked = rank_products(message, products);
    used_model = False;
    if model_proposal is not None {
        model_selected = validate_model_selection(model_proposal, ranked);
        if model_selected is not None and model_selected {
            ranked = model_selected;
            used_model = True;
        }
    }
    product_ids = [product.stripe_id for product in ranked];
    return SalesPlan(
        intent=Intent.PRODUCT_SEARCH,
        product_ids=product_ids,
        reply_text=render_recommendations(ranked),
        should_send_checkout=False,
        reason="grounded_catalog_match" if ranked else "no_catalog_match",
        used_model=used_model
    );
}
