import hashlib;
import json;
import os;
import threading;
import time;
import uuid;
import band_gate;
import from catalog_store { CatalogSnapshot, load_catalog_file, validate_catalog_text }
import from datetime { datetime, timezone }
import from httpx { Client, Response }
import from llm_sales { safe_model_decision }
import from pathlib { Path }
import from sales_logic {
    Intent,
    Product,
    SalesPlan,
    build_sales_plan,
    price_text,
    product_by_id,
    rank_products
}
import from urllib.parse { quote, urlparse }


glob LINQ_API_BASE: str = "https://api.linqapp.com/api/partner/v3",
     MAX_CATALOG_BYTES: int = 2_097_152,
     REMOTE_CATALOG_REFRESH_SECONDS: float = 30.0,
     STATE_LOCK = threading.RLock(),
     ACTIVE_CATALOG: CatalogSnapshot | None = None,
     ACTIVE_CATALOG_MTIME_NS: int = -1,
     ACTIVE_CATALOG_SOURCE: str = "",
     CATALOG_ERROR: str = "not_loaded",
     LAST_FAILED_CATALOG_SOURCE: str = "",
     LAST_FAILED_CATALOG_MTIME_NS: int = -1,
     LAST_REMOTE_CATALOG_CHECK: float = -1.0,
     LINK_EXPERIENCE_AVAILABLE: bool = False,
     PUBLIC_LINQ_PHONE: str = "",
     LINQ_PHONE_REPUTATION: str = "UNKNOWN",
     SERVICE_STARTED_AT: str = "",
     PROCESSING_EVENTS: set[str] = set(),
     PROCESSING_CONVERSATIONS: set[str] = set();


obj BandFlowResult {
    has plan: SalesPlan,
        status: str;
}


def _utc_now -> str {
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z");
}


def _data_dir -> Path {
    configured = os.getenv("DATA_DIR");
    return Path(configured) if configured else Path("data");
}


def _production_mode -> bool {
    configured = os.getenv("PRODUCTION_MODE") or "";
    return configured.strip().casefold() == "true";
}


def _public_store_url -> str {
    configured = os.getenv("PUBLIC_STORE_URL") or "";
    store_url = configured.strip().rstrip("/");
    if not store_url {
        if _production_mode() {
            raise ValueError("PUBLIC_STORE_URL is required in production mode");
        }
        return "";
    }
    parsed = urlparse(store_url);
    if parsed.scheme != "https"
    or not parsed.hostname
    or parsed.username is not None
    or parsed.password is not None
    or parsed.query
    or parsed.fragment {
        raise ValueError("PUBLIC_STORE_URL must be an absolute HTTPS origin");
    }
    return store_url;
}


def _catalog_path -> Path {
    configured = os.getenv("CATALOG_PATH");
    if configured {
        return Path(configured);
    }
    production = Path("catalog.json");
    if production.is_file() or _production_mode() {
        return production;
    }
    return Path("catalog.example.json");
}


def _catalog_url -> str | None {
    configured = os.getenv("CATALOG_URL") or "";
    catalog_url = configured.strip();
    if not catalog_url {
        return None;
    }
    parsed = urlparse(catalog_url);
    hostname = parsed.hostname or "";
    local_http = parsed.scheme == "http"
    and hostname in {"127.0.0.1", "localhost", "::1"}
    and not _production_mode();
    if not hostname or (parsed.scheme != "https" and not local_http) {
        raise ValueError("CATALOG_URL must be an absolute HTTPS URL");
    }
    if parsed.username is not None or parsed.password is not None or parsed.fragment {
        raise ValueError("CATALOG_URL contains unsupported URL components");
    }
    return catalog_url;
}


def _events_path -> Path {
    return _data_dir() / "events.jsonl";
}


def _conversation_path -> Path {
    return _data_dir() / "conversations.json";
}


def _pending_dir -> Path {
    return _data_dir() / "pending";
}


def _processed_dir -> Path {
    return _data_dir() / "processed";
}


def _event_outbox_dir -> Path {
    return _data_dir() / "event_outbox";
}


def _ensure_storage {
    _data_dir().mkdir(parents=True, exist_ok=True);
    _pending_dir().mkdir(parents=True, exist_ok=True);
    _processed_dir().mkdir(parents=True, exist_ok=True);
    _event_outbox_dir().mkdir(parents=True, exist_ok=True);
}


def _stable_hash(value: str) -> str {
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24] as str;
}


def _event_file_name(event_id: str) -> str {
    return f"{_stable_hash(event_id)}.json";
}


def _atomic_write_text(path: Path, text: str) {
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp";
    temporary.write_text(text, encoding="utf-8");
    os.replace(str(temporary), str(path));
}


def _read_json_object(path: Path) -> dict[str, object] {
    if not path.is_file() {
        return {};
    }
    parsed = json.loads(path.read_text(encoding="utf-8"));
    if not isinstance(parsed, dict) {
        raise ValueError(f"Expected a JSON object in {path.name}");
    }
    return parsed as dict[str, object];
}


def _append_event(
    event_type: str,
    conversation_id: str = "",
    inbound_message_id: str = "",
    data: dict[str, object] | None = None
) -> dict[str, object] {
    _ensure_storage();
    catalog_version = ACTIVE_CATALOG.version
        if ACTIVE_CATALOG is not None
        else "unavailable";
    event: dict[str, object] = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "type": event_type,
        "occurred_at": _utc_now(),
        "source": "linq_sales_agent",
        "conversation_id": conversation_id,
        "inbound_message_id": inbound_message_id,
        "catalog_version": catalog_version,
        "data": data or {}
    };
    encoded_event = json.dumps(event, ensure_ascii=False, separators=(",", ":"));
    with STATE_LOCK {
        with _events_path().open("a", encoding="utf-8") as event_file {
            event_file.write(encoded_event + "\n");
            event_file.flush();
            os.fsync(event_file.fileno());
        }
        if os.getenv("EVENT_SINK_URL") {
            _atomic_write_text(
                _event_outbox_dir() / f"{event['event_id']}.json", encoded_event
            );
        }
    }
    return event;
}


def flush_event_sink(limit: int = 100) -> dict[str, object] {
    sink_url = os.getenv("EVENT_SINK_URL");
    if not sink_url {
        return {"configured": False, "sent": 0, "pending": 0};
    }
    sent = 0;
    failed = False;
    paths = sorted(_event_outbox_dir().glob("*.json"));
    client: Client = Client(timeout=3.0);
    try {
        for path in paths[:limit] {
            try {
                event = _read_json_object(path);
                response: Response = client.post(
                    sink_url, headers={"Content-Type": "application/json"}, json=event
                );
                if response.status_code < 200 or response.status_code >= 300 {
                    failed = True;
                    break;
                }
                path.unlink(missing_ok=True);
                sent += 1;
            } except Exception {
                failed = True;
                break;
            }
        }
    } finally {
        client.close();
    }
    return {
        "configured": True,
        "sent": sent,
        "pending": len(list(_event_outbox_dir().glob("*.json"))),
        "failed": failed
    };
}


def _load_remote_catalog(catalog_url: str) -> CatalogSnapshot {
    client: Client = Client(timeout=5.0, follow_redirects=True);
    try {
        response: Response = client.get(
            catalog_url, headers={"Accept": "application/json"}
        );
        if response.status_code < 200 or response.status_code >= 300 {
            raise RuntimeError(f"catalog_http_{response.status_code}");
        }
        raw_text = response.text;
    } finally {
        client.close();
    }
    if len(raw_text.encode("utf-8")) > MAX_CATALOG_BYTES {
        raise ValueError("Remote catalog exceeds the size limit");
    }
    return validate_catalog_text(
        raw_text,
        source_path="catalog_url",
        allow_non_transactional=False,
        require_active=_production_mode(),
        public_store_url=_public_store_url()
    );
}


def _refresh_remote_catalog(
    catalog_url: str, force: bool = False
) -> dict[str, object] {
    now = time.monotonic();
    if not force
    and ACTIVE_CATALOG is not None
    and ACTIVE_CATALOG_SOURCE == "catalog_url"
    and LAST_REMOTE_CATALOG_CHECK >= 0
    and now - LAST_REMOTE_CATALOG_CHECK < REMOTE_CATALOG_REFRESH_SECONDS {
        return {
            "reloaded": False,
            "catalog_products": len(ACTIVE_CATALOG.products),
            "catalog_version": ACTIVE_CATALOG.version,
            "source": "catalog_url"
        };
    }
    LAST_REMOTE_CATALOG_CHECK = now;
    try {
        candidate = _load_remote_catalog(catalog_url);
        unchanged = ACTIVE_CATALOG is not None
        and ACTIVE_CATALOG_SOURCE == "catalog_url"
        and ACTIVE_CATALOG.version == candidate.version;
        with STATE_LOCK {
            ACTIVE_CATALOG = candidate;
            ACTIVE_CATALOG_MTIME_NS = -1;
            ACTIVE_CATALOG_SOURCE = "catalog_url";
            CATALOG_ERROR = "";
            LAST_FAILED_CATALOG_SOURCE = "";
            LAST_FAILED_CATALOG_MTIME_NS = -1;
            if not unchanged {
                _append_event(
                    "catalog_reloaded",
                    data={
                        "catalog_products": len(candidate.products),
                        "checkout_ready_products": candidate.checkout_ready_products,
                        "catalog_version": candidate.version,
                        "source_file": "catalog_url"
                    }
                );
            }
        }
        return {
            "reloaded": not unchanged,
            "catalog_products": len(candidate.products),
            "catalog_version": candidate.version,
            "source": "catalog_url"
        };
    } except Exception as error {
        CATALOG_ERROR = str(error);
        _append_event(
            "catalog_reload_failed",
            data={"error": "catalog_validation_failed", "source_file": "catalog_url"}
        );
        return {
            "reloaded": False,
            "catalog_products": len(ACTIVE_CATALOG.products)
                if ACTIVE_CATALOG is not None
                else 0,
            "error": "catalog_validation_failed",
            "source": "catalog_url"
        };
    }
}


def refresh_catalog(force: bool = False) -> dict[str, object] {
    _ensure_storage();
    configured_url = os.getenv("CATALOG_URL");
    if configured_url {
        try {
            catalog_url = _catalog_url();
            if catalog_url is None {
                raise ValueError("CATALOG_URL is empty");
            }
            return _refresh_remote_catalog(catalog_url, force);
        } except Exception as error {
            CATALOG_ERROR = str(error);
            if force or LAST_FAILED_CATALOG_SOURCE != "catalog_url_config" {
                LAST_FAILED_CATALOG_SOURCE = "catalog_url_config";
                _append_event(
                    "catalog_reload_failed",
                    data={"error": "catalog_url_invalid", "source_file": "catalog_url"}
                );
            }
            return {
                "reloaded": False,
                "catalog_products": len(ACTIVE_CATALOG.products)
                    if ACTIVE_CATALOG is not None
                    else 0,
                "error": "catalog_url_invalid",
                "source": "catalog_url"
            };
        }
    }
    path = _catalog_path();
    try {
        current_mtime = path.stat().st_mtime_ns;
        if not force
        and ACTIVE_CATALOG is not None
        and current_mtime == ACTIVE_CATALOG_MTIME_NS
        and str(path) == ACTIVE_CATALOG_SOURCE {
            return {
                "reloaded": False,
                "catalog_products": len(ACTIVE_CATALOG.products),
                "catalog_version": ACTIVE_CATALOG.version
            };
        }
        if not force
        and str(path) == LAST_FAILED_CATALOG_SOURCE
        and current_mtime == LAST_FAILED_CATALOG_MTIME_NS {
            return {
                "reloaded": False,
                "catalog_products": len(ACTIVE_CATALOG.products)
                    if ACTIVE_CATALOG is not None
                    else 0,
                "error": "catalog_validation_failed"
            };
        }
        candidate = load_catalog_file(
            str(path),
            production_mode=_production_mode(),
            public_store_url=_public_store_url()
        );
        with STATE_LOCK {
            ACTIVE_CATALOG = candidate;
            ACTIVE_CATALOG_MTIME_NS = current_mtime;
            ACTIVE_CATALOG_SOURCE = str(path);
            CATALOG_ERROR = "";
            LAST_FAILED_CATALOG_SOURCE = "";
            LAST_FAILED_CATALOG_MTIME_NS = -1;
            _append_event(
                "catalog_reloaded",
                data={
                    "catalog_products": len(candidate.products),
                    "checkout_ready_products": candidate.checkout_ready_products,
                    "catalog_version": candidate.version,
                    "source_file": path.name
                }
            );
        }
        return {
            "reloaded": True,
            "catalog_products": len(candidate.products),
            "catalog_version": candidate.version
        };
    } except Exception as error {
        CATALOG_ERROR = str(error);
        LAST_FAILED_CATALOG_SOURCE = str(path);
        try {
            LAST_FAILED_CATALOG_MTIME_NS = path.stat().st_mtime_ns;
        } except Exception {
            LAST_FAILED_CATALOG_MTIME_NS = -1;
        }
        _append_event(
            "catalog_reload_failed",
            data={"error": "catalog_validation_failed", "source_file": path.name}
        );
        return {
            "reloaded": False,
            "catalog_products": len(ACTIVE_CATALOG.products)
                if ACTIVE_CATALOG is not None
                else 0,
            "error": "catalog_validation_failed"
        };
    }
}


def _linq_request(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    timeout_seconds: float = 6.0
) -> dict[str, object] {
    token = os.getenv("LINQ_API_KEY");
    if not token {
        raise RuntimeError("missing_linq_credential");
    }
    client: Client = Client(timeout=timeout_seconds);
    try {
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        };
        if method == "GET" {
            response: Response = client.get(f"{LINQ_API_BASE}{path}", headers=headers);
        } else {
            response = client.post(
                f"{LINQ_API_BASE}{path}", headers=headers, json=payload or {}
            );
        }
        if response.status_code < 200 or response.status_code >= 300 {
            raise RuntimeError(f"linq_http_{response.status_code}");
        }
        parsed = response.json();
    } finally {
        client.close();
    }
    if not isinstance(parsed, dict) {
        raise ValueError("Linq response was not a JSON object");
    }
    result = parsed as dict[str, object];
    trace_id = response.headers.get("X-Trace-ID");
    if trace_id {
        result["_trace_id"] = trace_id;
    }
    return result;
}


def _contains_open_action(value: object) -> bool {
    if isinstance(value, str) {
        return value == "open";
    }
    if isinstance(value, dict) {
        item = value as dict[str, object];
        if item.get("name") == "open" or item.get("action") == "open" {
            return True;
        }
        for child in item.values() {
            if _contains_open_action(child) {
                return True;
            }
        }
    } elif isinstance(value, list) {
        for child in value {
            if _contains_open_action(child) {
                return True;
            }
        }
    }
    return False;
}


def _contains_link_open(value: object) -> bool {
    if isinstance(value, dict) {
        item = value as dict[str, object];
        link_name = item.get("experience") or item.get("name");
        if link_name == "link" and item.get("action") == "open" {
            return True;
        }
        if link_name == "link" and _contains_open_action(item.get("actions")) {
            return True;
        }
        for child in item.values() {
            if _contains_link_open(child) {
                return True;
            }
        }
    } elif isinstance(value, list) {
        for child in value {
            if _contains_link_open(child) {
                return True;
            }
        }
    }
    return False;
}


def discover_linq_experiences -> bool {
    if not os.getenv("LINQ_API_KEY") {
        LINK_EXPERIENCE_AVAILABLE = False;
        return False;
    }
    try {
        response = _linq_request("GET", "/experiences");
        LINK_EXPERIENCE_AVAILABLE = _contains_link_open(response);
    } except Exception {
        LINK_EXPERIENCE_AVAILABLE = False;
    }
    return LINK_EXPERIENCE_AVAILABLE;
}


def _phone_resources(response: dict[str, object]) -> list[dict[str, object]] {
    raw_phone_numbers = response.get("phone_numbers");
    if not isinstance(raw_phone_numbers, list) {
        return [];
    }
    resources: list[dict[str, object]] = [];
    for raw_phone in raw_phone_numbers {
        if not isinstance(raw_phone, dict) {
            continue;
        }
        phone = raw_phone as dict[str, object];
        raw_id = phone.get("id");
        raw_number = phone.get("phone_number");
        if not isinstance(raw_id, str)
        or not raw_id.strip()
        or not isinstance(raw_number, str)
        or not raw_number.startswith("+")
        or not raw_number[1:].isdigit() {
            continue;
        }
        reputation = phone.get("reputation");
        reputation_status = "UNKNOWN";
        if isinstance(reputation, dict) {
            raw_status = (reputation as dict[str, object]).get("status");
            if isinstance(raw_status, str)
            and raw_status in {"HEALTHY", "AT_RISK", "CRITICAL"} {
                reputation_status = raw_status;
            }
        }
        resources.append(
            {"id": raw_id, "phone_number": raw_number, "reputation": reputation_status}
        );
    }
    return resources;
}


def discover_linq_account -> dict[str, object] {
    if not os.getenv("LINQ_API_KEY") {
        LINK_EXPERIENCE_AVAILABLE = False;
        PUBLIC_LINQ_PHONE = "";
        LINQ_PHONE_REPUTATION = "UNKNOWN";
        return {
            "authenticated": False,
            "api_version": "v3",
            "reason": "missing_linq_credential",
            "phone_numbers": [],
            "inbound_messaging_supported": False,
            "link_experience_available": False
        };
    }
    try {
        phone_response = _linq_request("GET", "/phone_numbers");
        phone_numbers = _phone_resources(phone_response);
    } except Exception as error {
        LINK_EXPERIENCE_AVAILABLE = False;
        PUBLIC_LINQ_PHONE = "";
        LINQ_PHONE_REPUTATION = "UNKNOWN";
        return {
            "authenticated": False,
            "api_version": "v3",
            "reason": str(error)[:80],
            "phone_numbers": [],
            "inbound_messaging_supported": False,
            "link_experience_available": False
        };
    }
    if len(phone_numbers) == 1 {
        PUBLIC_LINQ_PHONE = str(phone_numbers[0].get("phone_number") or "");
        LINQ_PHONE_REPUTATION = str(phone_numbers[0].get("reputation") or "UNKNOWN");
    } else {
        PUBLIC_LINQ_PHONE = "";
        LINQ_PHONE_REPUTATION = "UNKNOWN";
    }
    experiences_discovered = False;
    try {
        experience_response = _linq_request("GET", "/experiences");
        LINK_EXPERIENCE_AVAILABLE = _contains_link_open(experience_response);
        experiences_discovered = True;
    } except Exception {
        LINK_EXPERIENCE_AVAILABLE = False;
    }
    return {
        "authenticated": True,
        "api_version": "v3",
        "reason": "partner_api_access_confirmed",
        "phone_numbers": phone_numbers,
        "public_phone": PUBLIC_LINQ_PHONE,
        "inbound_messaging_supported": bool(phone_numbers),
        "experiences_discovered": experiences_discovered,
        "link_experience_available": LINK_EXPERIENCE_AVAILABLE
    };
}


def check_linq_authentication -> dict[str, object] {
    return discover_linq_account();
}


def bootstrap -> dict[str, object] {
    _ensure_storage();
    if not SERVICE_STARTED_AT {
        SERVICE_STARTED_AT = _utc_now();
    }
    catalog_result = refresh_catalog(force=True);
    account = discover_linq_account();
    return {
        "catalog": catalog_result,
        "linq_account": account,
        "link_experience_available": LINK_EXPERIENCE_AVAILABLE,
        "pending_events": len(pending_event_ids())
    };
}


def _extract_text_parts(parts_value: object) -> str {
    if not isinstance(parts_value, list) {
        return "";
    }
    text_parts: list[str] = [];
    for raw_part in parts_value {
        if isinstance(raw_part, dict) {
            part = raw_part as dict[str, object];
            value = part.get("value");
            if part.get("type") == "text"
            and isinstance(value, str)
            and value.strip() {
                text_parts.append(value.strip());
            }
        }
    }
    return "\n".join(text_parts);
}


def ingest_webhook(raw_text: str) -> dict[str, object] {
    _ensure_storage();
    parsed = json.loads(raw_text);
    if not isinstance(parsed, dict) {
        raise ValueError("Webhook payload must be a JSON object");
    }
    envelope = parsed as dict[str, object];
    if envelope.get("api_version") != "v3" {
        raise ValueError("Unsupported Linq API version");
    }
    if envelope.get("event_type") != "message.received" {
        return {"accepted": True, "queued": False, "reason": "event_not_actionable"};
    }
    if envelope.get("webhook_version") != "2026-02-03" {
        raise ValueError("Unsupported Linq webhook version");
    }
    event_id_value = envelope.get("event_id");
    data_value = envelope.get("data");
    if not isinstance(event_id_value, str) or not event_id_value {
        raise ValueError("Webhook event_id is required");
    }
    if not isinstance(data_value, dict) {
        raise ValueError("Webhook data must be an object");
    }
    message_data = data_value as dict[str, object];
    if message_data.get("direction") != "inbound"
    or message_data.get("reconciled_at") is not None {
        return {
            "accepted": True,
            "queued": False,
            "reason": "message_not_live_inbound"
        };
    }
    sender_value = message_data.get("sender_handle");
    if isinstance(sender_value, dict)
    and bool((sender_value as dict[str, object]).get("is_me")) {
        return {"accepted": True, "queued": False, "reason": "own_message_ignored"};
    }
    chat_value = message_data.get("chat");
    if not isinstance(chat_value, dict) {
        raise ValueError("Webhook chat must be an object");
    }
    chat = chat_value as dict[str, object];
    chat_id_value = chat.get("id");
    message_id_value = message_data.get("id");
    if not isinstance(chat_id_value, str) or not isinstance(message_id_value, str) {
        raise ValueError("Webhook chat and message ids are required");
    }
    if chat.get("is_group") {
        return {"accepted": True, "queued": False, "reason": "group_chat_suppressed"};
    }
    message_text = _extract_text_parts(message_data.get("parts"));
    if not message_text {
        return {"accepted": True, "queued": False, "reason": "no_text_content"};
    }
    health_status = "UNKNOWN";
    health_value = chat.get("health_status");
    if isinstance(health_value, dict) {
        health_item = health_value as dict[str, object];
        raw_status = health_item.get("status");
        if isinstance(raw_status, str) {
            health_status = raw_status;
        }
    }
    service_value = message_data.get("service");
    service = service_value if isinstance(service_value, str) else "unknown";
    conversation_id = _stable_hash(chat_id_value);
    pending_path = _pending_dir() / _event_file_name(event_id_value);
    processed_path = _processed_dir() / _event_file_name(event_id_value);
    with STATE_LOCK {
        if pending_path.exists() or processed_path.exists() {
            _append_event(
                "duplicate_delivery_ignored",
                conversation_id=conversation_id,
                inbound_message_id=message_id_value,
                data={"provider_event_id": event_id_value}
            );
            return {"accepted": True, "queued": False, "duplicate": True};
        }
        job: dict[str, object] = {
            "provider_event_id": event_id_value,
            "chat_id": chat_id_value,
            "conversation_id": conversation_id,
            "message_id": message_id_value,
            "message_text": message_text,
            "health_status": health_status,
            "service": service,
            "created_at": envelope.get("created_at") or _utc_now(),
            "received_at": _utc_now()
        };
        _atomic_write_text(pending_path, json.dumps(job, ensure_ascii=False));
        _append_event(
            "inbound_message",
            conversation_id=conversation_id,
            inbound_message_id=message_id_value,
            data={
                "provider_event_id": event_id_value,
                "message_length": len(message_text),
                "service": service,
                "health_status": health_status
            }
        );
    }
    return {"accepted": True, "queued": True, "event_id": event_id_value};
}


def pending_event_ids -> list[str] {
    _ensure_storage();
    event_records: list[tuple[str, str]] = [];
    for path in _pending_dir().glob("*.json") {
        try {
            job = _read_json_object(path);
            raw_id = job.get("provider_event_id");
            if isinstance(raw_id, str) {
                received_at = job.get("received_at");
                sort_key = received_at if isinstance(received_at, str) else "";
                event_records.append((sort_key, raw_id));
            }
        } except Exception {
            continue;
        }
    }
    event_records.sort();
    return [event_id for (_, event_id) in event_records];
}


def _has_earlier_conversation_event(event_id: str, conversation_id: str) -> bool {
    for pending_id in pending_event_ids() {
        if pending_id == event_id {
            return False;
        }
        try {
            earlier = _read_json_object(_pending_dir() / _event_file_name(pending_id));
            if earlier.get("conversation_id") == conversation_id {
                return True;
            }
        } except Exception {
            continue;
        }
    }
    return False;
}


def _string_list(value: object) -> list[str] {
    if not isinstance(value, list) {
        return [];
    }
    return [
        item
        for item in value
        if isinstance(item, str)
    ] as list[str];
}


def _conversation_states -> dict[str, object] {
    try {
        return _read_json_object(_conversation_path());
    } except Exception {
        return {};
    }
}


def _conversation_state(
    states: dict[str, object], conversation_id: str
) -> dict[str, object] {
    raw_state = states.get(conversation_id);
    if isinstance(raw_state, dict) {
        return raw_state as dict[str, object];
    }
    return {
        "state": "new",
        "last_product_ids": [],
        "opted_out": False,
        "has_replied": False
    };
}


def _save_conversation_states(states: dict[str, object]) {
    _atomic_write_text(
        _conversation_path(), json.dumps(states, ensure_ascii=False, sort_keys=True)
    );
}


def _send_message(
    chat_id: str, message_content: dict[str, object]
) -> dict[str, object] {
    encoded_chat_id = quote(chat_id, safe="");
    return _linq_request(
        "POST",
        f"/chats/{encoded_chat_id}/messages",
        payload={"message": message_content}
    );
}


def _send_text_reply(
    chat_id: str, text: str, idempotency_key: str
) -> dict[str, object] {
    return _send_message(
        chat_id,
        {
            "parts": [{"type": "text", "value": text}],
            "idempotency_key": idempotency_key[:255]
        }
    );
}


def _send_product_action(
    chat_id: str,
    product: Product,
    idempotency_key: str,
    use_experience: bool,
    direct_checkout: bool
) -> dict[str, object] {
    target_url = product.payment_link if direct_checkout else product.product_url;
    action_verb = "Buy" if direct_checkout else "View";
    action_title = f"{action_verb} {product.name} — {price_text(product.price_cents)}";
    if use_experience {
        return _send_message(
            chat_id,
            {
                "experience": {
                    "name": "link",
                    "action": "open",
                    "params": {"url": target_url, "title": action_title[:64]}
                },
                "idempotency_key": idempotency_key[:255]
            }
        );
    }
    return _send_message(
        chat_id,
        {
            "parts": [{"type": "link", "value": target_url}],
            "idempotency_key": idempotency_key[:255]
        }
    );
}


def _mark_processed(event_id: str) {
    pending_path = _pending_dir() / _event_file_name(event_id);
    processed_path = _processed_dir() / _event_file_name(event_id);
    if pending_path.is_file() {
        os.replace(str(pending_path), str(processed_path));
    }
}


def _next_conversation_state(plan: SalesPlan, checkout_sent: bool) -> str {
    if plan.intent == Intent.OPT_OUT {
        return "opted_out";
    }
    if plan.intent == Intent.RESUME or plan.intent == Intent.GREETING {
        return "discovery";
    }
    if checkout_sent {
        return "checkout_sent";
    }
    if plan.product_ids {
        return "recommended";
    }
    if plan.intent == Intent.PRODUCT_SEARCH {
        return "no_match";
    }
    return "discovery";
}


def _next_product_ids(plan: SalesPlan, previous_ids: list[str]) -> list[str] {
    if plan.intent == Intent.PRODUCT_SEARCH {
        return plan.product_ids;
    }
    return plan.product_ids if plan.product_ids else previous_ids;
}


def _single_product_plan(
    message: str, products: list[Product], previous_ids: list[str], plan: SalesPlan
) -> SalesPlan {
    if not plan.product_ids {
        return plan;
    }
    primary = product_by_id(products, plan.product_ids[0]);
    if primary is None {
        return plan;
    }
    return build_sales_plan(
        message, [primary], last_product_ids=previous_ids, model_proposal=None
    );
}


def _band_fail_closed_plan(plan: SalesPlan) -> SalesPlan {
    return SalesPlan(
        intent=plan.intent,
        product_ids=[],
        reply_text="I can't safely verify a recommendation right now, so I won't send a product or checkout link. Please try again shortly.",
        should_send_checkout=False,
        reason="band_gate_fail_closed",
        used_model=False
    );
}


def _band_candidate_products(
    plan: SalesPlan, products: list[Product]
) -> list[dict[str, object]] {
    candidates: list[dict[str, object]] = [];
    for product_id in plan.product_ids {
        product = product_by_id(products, product_id);
        if product is not None {
            candidates.append(
                {
                    "product_id": product.stripe_id,
                    "name": product.name,
                    "price_cents": product.price_cents,
                    "currency": "USD"
                }
            );
        }
    }
    return candidates;
}


def _record_product_selected(
    plan: SalesPlan,
    conversation_id: str,
    inbound_message_id: str,
    attempt: int,
    method: str
) {
    if not plan.product_ids {
        return;
    }
    _append_event(
        "product_selected",
        conversation_id=conversation_id,
        inbound_message_id=inbound_message_id,
        data={
            "product_ids": plan.product_ids,
            "primary_product_id": plan.product_ids[0],
            "selection_method": method,
            "attempt": attempt
        }
    );
}


def _request_band_review(
    provider_event_id: str,
    plan: SalesPlan,
    products: list[Product],
    conversation_id: str,
    inbound_message_id: str,
    attempt: int
) -> band_gate.BandReview {
    review_id = f"{provider_event_id}:band:{attempt}";
    _append_event(
        "band_review_requested",
        conversation_id=conversation_id,
        inbound_message_id=inbound_message_id,
        data={
            "review_id": review_id,
            "product_ids": plan.product_ids,
            "attempt": attempt
        }
    );
    review = band_gate.review_candidate(
        band_gate.BandCandidate(
            review_id=review_id,
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            intent=plan.intent,
            catalog_version=ACTIVE_CATALOG.version
                if ACTIVE_CATALOG is not None
                else "unavailable",
            products=_band_candidate_products(plan, products),
            should_send_checkout=plan.should_send_checkout
        )
    );
    event_type = "band_review_approved"
        if review.decision == "APPROVE"
        else (
            "band_review_blocked"
                if review.decision == "BLOCK"
                else "band_review_failed_closed"
        );
    _append_event(
        event_type,
        conversation_id=conversation_id,
        inbound_message_id=inbound_message_id,
        data={
            "review_id": review.review_id,
            "product_ids": plan.product_ids,
            "attempt": attempt,
            "reason": review.reason
        }
    );
    return review;
}


def _apply_band_gate(
    provider_event_id: str,
    message: str,
    plan: SalesPlan,
    products: list[Product],
    previous_ids: list[str],
    conversation_id: str,
    inbound_message_id: str
) -> BandFlowResult {
    gated_action = bool(plan.product_ids);
    if not gated_action {
        return BandFlowResult(plan=plan, status="not_applicable");
    }
    if not band_gate.is_enabled() {
        _record_product_selected(
            plan, conversation_id, inbound_message_id, attempt=1, method="initial"
        );
        return BandFlowResult(plan=plan, status="disabled");
    }

    initial = _single_product_plan(message, products, previous_ids, plan);
    _record_product_selected(
        initial, conversation_id, inbound_message_id, attempt=1, method="initial"
    );
    initial_review = _request_band_review(
        provider_event_id,
        initial,
        products,
        conversation_id,
        inbound_message_id,
        attempt=1
    );
    if initial_review.decision == "APPROVE" {
        return BandFlowResult(plan=initial, status="approved");
    }
    if initial_review.decision != "BLOCK" {
        return BandFlowResult(
            plan=_band_fail_closed_plan(initial), status="fail_closed"
        );
    }

    remaining = [
        product
        for product in products
        if product.stripe_id not in initial.product_ids
    ];
    fallback = build_sales_plan(
        message, remaining, last_product_ids=previous_ids, model_proposal=None
    );
    if not fallback.product_ids {
        _append_event(
            "band_review_failed_closed",
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            data={
                "review_id": f"{provider_event_id}:band:2",
                "product_ids": [],
                "attempt": 2,
                "reason": "no_safe_fallback"
            }
        );
        return BandFlowResult(
            plan=_band_fail_closed_plan(initial), status="fail_closed"
        );
    }
    fallback = _single_product_plan(message, remaining, previous_ids, fallback);
    _record_product_selected(
        fallback, conversation_id, inbound_message_id, attempt=2, method="band_fallback"
    );
    fallback_review = _request_band_review(
        provider_event_id,
        fallback,
        remaining,
        conversation_id,
        inbound_message_id,
        attempt=2
    );
    if fallback_review.decision == "APPROVE" {
        return BandFlowResult(plan=fallback, status="approved_fallback");
    }
    if fallback_review.decision == "BLOCK" {
        _append_event(
            "band_review_failed_closed",
            conversation_id=conversation_id,
            inbound_message_id=inbound_message_id,
            data={
                "review_id": fallback_review.review_id,
                "product_ids": fallback.product_ids,
                "attempt": 2,
                "reason": "fallback_not_approved"
            }
        );
    }
    return BandFlowResult(plan=_band_fail_closed_plan(fallback), status="fail_closed");
}


def _process_pending_event_impl(event_id: str) -> dict[str, object] {
    refresh_catalog();
    pending_path = _pending_dir() / _event_file_name(event_id);
    if not pending_path.is_file() {
        return {"processed": False, "reason": "pending_event_not_found"};
    }
    job = _read_json_object(pending_path);
    raw_chat_id = job.get("chat_id");
    raw_conversation_id = job.get("conversation_id");
    raw_message_id = job.get("message_id");
    raw_message = job.get("message_text");
    raw_health = job.get("health_status");
    raw_service = job.get("service");
    if not isinstance(raw_chat_id, str)
    or not isinstance(raw_conversation_id, str)
    or not isinstance(raw_message_id, str)
    or not isinstance(raw_message, str) {
        _append_event(
            "reply_send_failed",
            data={"code": "malformed_pending_event", "provider_event_id": event_id}
        );
        _mark_processed(event_id);
        return {"processed": False, "reason": "malformed_pending_event"};
    }
    health_status = raw_health if isinstance(raw_health, str) else "UNKNOWN";
    service = raw_service if isinstance(raw_service, str) else "unknown";
    with STATE_LOCK {
        states = _conversation_states();
        state = _conversation_state(states, raw_conversation_id);
        previous_ids = _string_list(state.get("last_product_ids"));
        opted_out = bool(state.get("opted_out"));
    }

    preliminary = build_sales_plan(raw_message, [], previous_ids);
    if preliminary.intent == Intent.OPT_OUT {
        with STATE_LOCK {
            states = _conversation_states();
            states[raw_conversation_id] = {
                "state": "opted_out",
                "last_product_ids": previous_ids,
                "opted_out": True,
                "has_replied": bool(state.get("has_replied")),
                "updated_at": _utc_now()
            };
            _save_conversation_states(states);
        }
        _append_event(
            "intent_detected",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={
                "intent": Intent.OPT_OUT,
                "method": "deterministic",
                "reason": "customer_opt_out"
            }
        );
        _append_event(
            "reply_suppressed",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={"reason": "customer_opt_out"}
        );
        _mark_processed(event_id);
        return {"processed": True, "replied": False, "reason": "customer_opt_out"};
    }
    if opted_out and preliminary.intent != Intent.RESUME {
        _append_event(
            "reply_suppressed",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={"reason": "locally_opted_out"}
        );
        _mark_processed(event_id);
        return {"processed": True, "replied": False, "reason": "locally_opted_out"};
    }
    if health_status not in {"HEALTHY", "AT_RISK"} {
        _append_event(
            "reply_suppressed",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={"reason": "linq_chat_health", "health_status": health_status}
        );
        _mark_processed(event_id);
        return {"processed": True, "replied": False, "reason": "linq_chat_health"};
    }
    if LINQ_PHONE_REPUTATION == "CRITICAL" {
        _append_event(
            "reply_suppressed",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={"reason": "linq_phone_reputation", "reputation": "CRITICAL"}
        );
        _mark_processed(event_id);
        return {"processed": True, "replied": False, "reason": "linq_phone_reputation"};
    }
    if not os.getenv("LINQ_API_KEY") {
        _append_event(
            "reply_send_failed",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={"code": "missing_linq_credential", "retryable": True}
        );
        return {
            "processed": False,
            "replied": False,
            "reason": "missing_linq_credential"
        };
    }

    products = ACTIVE_CATALOG.products if ACTIVE_CATALOG is not None else [];
    eligible = rank_products(raw_message, products);
    model_proposal = safe_model_decision(
        raw_message, str(state.get("state") or "new"), eligible
    )
        if eligible
        else None;
    plan = build_sales_plan(
        raw_message,
        products,
        last_product_ids=previous_ids,
        model_proposal=model_proposal
    );
    _append_event(
        "intent_detected",
        conversation_id=raw_conversation_id,
        inbound_message_id=raw_message_id,
        data={
            "intent": plan.intent,
            "method": "llm_validated" if plan.used_model else "deterministic",
            "reason": plan.reason
        }
    );
    for (rank, product) in enumerate(eligible) {
        _append_event(
            "product_considered",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={
                "product_id": product.stripe_id,
                "name": product.name,
                "price": product.price_cents / 100.0,
                "eligible": True,
                "rank": rank + 1
            }
        );
    }
    if state.get("has_replied") {
        _append_event(
            "customer_response",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={
                "prior_state": str(state.get("state") or "unknown"),
                "intent": plan.intent
            }
        );
    }

    band_flow = _apply_band_gate(
        event_id,
        raw_message,
        plan,
        products,
        previous_ids,
        raw_conversation_id,
        raw_message_id
    );
    plan = band_flow.plan;
    primary = product_by_id(products, plan.product_ids[0])
        if plan.product_ids
        else None;
    should_send_product_page = bool(
        plan.intent == Intent.PRODUCT_SEARCH
        and primary is not None
        and primary.product_url
        and not plan.should_send_checkout
    );
    use_experience = bool(
        LINK_EXPERIENCE_AVAILABLE
        and service == "iMessage"
        and primary is not None
        and (plan.should_send_checkout or should_send_product_page)
    );
    try {
        text_response = _send_text_reply(
            raw_chat_id, plan.reply_text, f"{event_id}:recommendation"
        );
        if plan.product_ids {
            _append_event(
                "product_recommended",
                conversation_id=raw_conversation_id,
                inbound_message_id=raw_message_id,
                data={
                    "product_ids": plan.product_ids,
                    "primary_product_id": plan.product_ids[0],
                    "product_url": primary.product_url if primary is not None else "",
                    "send_status": "accepted",
                    "trace_id": text_response.get("_trace_id") or ""
                }
            );
        }
        checkout_sent = False;
        product_page_sent = False;
        if (plan.should_send_checkout or should_send_product_page)
        and primary is not None
        and health_status != "AT_RISK" {
            action_response = _send_product_action(
                raw_chat_id,
                primary,
                f"{event_id}:checkout"
                    if plan.should_send_checkout
                    else f"{event_id}:product-page",
                use_experience=use_experience,
                direct_checkout=plan.should_send_checkout
            );
            if plan.should_send_checkout {
                checkout_sent = True;
                _append_event(
                    "checkout_link_sent",
                    conversation_id=raw_conversation_id,
                    inbound_message_id=raw_message_id,
                    data={
                        "product_id": primary.stripe_id,
                        "payment_link": primary.payment_link,
                        "channel": "linq_experience"
                            if use_experience
                            else "imessage_link",
                        "send_status": "accepted",
                        "trace_id": action_response.get("_trace_id") or ""
                    }
                );
            } else {
                product_page_sent = True;
                _append_event(
                    "product_page_sent",
                    conversation_id=raw_conversation_id,
                    inbound_message_id=raw_message_id,
                    data={
                        "product_id": primary.stripe_id,
                        "product_url": primary.product_url,
                        "channel": "linq_experience"
                            if use_experience
                            else "imessage_link",
                        "send_status": "accepted",
                        "trace_id": action_response.get("_trace_id") or ""
                    }
                );
            }
        }
    } except Exception as error {
        code = str(error);
        retryable = not code.startswith("linq_http_4") or code == "linq_http_429";
        _append_event(
            "reply_send_failed",
            conversation_id=raw_conversation_id,
            inbound_message_id=raw_message_id,
            data={"code": code[:80], "retryable": retryable}
        );
        if not retryable {
            _mark_processed(event_id);
        }
        return {"processed": not retryable, "replied": False, "reason": code[:80]};
    }

    with STATE_LOCK {
        states = _conversation_states();
        new_state: dict[str, object] = {
            "state": _next_conversation_state(plan, checkout_sent),
            "last_product_ids": _next_product_ids(plan, previous_ids),
            "opted_out": plan.intent == Intent.OPT_OUT,
            "has_replied": True,
            "updated_at": _utc_now()
        };
        if plan.intent == Intent.RESUME {
            new_state["opted_out"] = False;
        }
        states[raw_conversation_id] = new_state;
        _save_conversation_states(states);
        _mark_processed(event_id);
    }
    return {
        "processed": True,
        "replied": True,
        "intent": plan.intent,
        "product_ids": plan.product_ids,
        "checkout_sent": checkout_sent,
        "product_page_sent": product_page_sent,
        "imessage_card": use_experience and (checkout_sent or product_page_sent),
        "band_gate_status": band_flow.status
    };
}


def process_pending_event(event_id: str) -> dict[str, object] {
    pending_path = _pending_dir() / _event_file_name(event_id);
    pending_job = _read_json_object(pending_path);
    raw_conversation_id = pending_job.get("conversation_id");
    conversation_id = raw_conversation_id
        if isinstance(raw_conversation_id, str)
        else "";
    if conversation_id and _has_earlier_conversation_event(event_id, conversation_id) {
        return {"processed": False, "reason": "earlier_conversation_event"};
    }
    with STATE_LOCK {
        if event_id in PROCESSING_EVENTS {
            return {"processed": False, "reason": "already_processing"};
        }
        if conversation_id and conversation_id in PROCESSING_CONVERSATIONS {
            return {"processed": False, "reason": "conversation_busy"};
        }
        PROCESSING_EVENTS.add(event_id);
        if conversation_id {
            PROCESSING_CONVERSATIONS.add(conversation_id);
        }
    }
    try {
        return _process_pending_event_impl(event_id);
    } finally {
        with STATE_LOCK {
            PROCESSING_EVENTS.discard(event_id);
            if conversation_id {
                PROCESSING_CONVERSATIONS.discard(conversation_id);
            }
        }
    }
}


def process_all_pending(limit: int = 50) -> dict[str, object] {
    processed = 0;
    deferred = 0;
    for event_id in pending_event_ids()[:limit] {
        result = process_pending_event(event_id);
        if result.get("processed") {
            processed += 1;
        } else {
            deferred += 1;
        }
    }
    return {"processed": processed, "deferred": deferred};
}


def _load_events -> list[dict[str, object]] {
    if not _events_path().is_file() {
        return [];
    }
    events: list[dict[str, object]] = [];
    for line in _events_path().read_text(encoding="utf-8").splitlines() {
        if not line.strip() {
            continue;
        }
        try {
            parsed = json.loads(line);
            if isinstance(parsed, dict) {
                events.append(parsed as dict[str, object]);
            }
        } except Exception {
            continue;
        }
    }
    return events;
}


def get_status -> dict[str, object] {
    events = _load_events();
    handled_messages: set[str] = set();
    conversations: set[str] = set();
    recommended_messages: set[str] = set();
    checkout_messages: set[str] = set();
    for event in events {
        raw_type = event.get("type");
        raw_message_id = event.get("inbound_message_id");
        raw_conversation_id = event.get("conversation_id");
        if isinstance(raw_conversation_id, str) and raw_conversation_id {
            conversations.add(raw_conversation_id);
        }
        if isinstance(raw_message_id, str) and raw_message_id {
            if raw_type == "inbound_message" {
                handled_messages.add(raw_message_id);
            } elif raw_type == "product_recommended" {
                recommended_messages.add(raw_message_id);
            } elif raw_type == "checkout_link_sent" {
                checkout_messages.add(raw_message_id);
            }
        }
    }
    catalog_count = len(ACTIVE_CATALOG.products) if ACTIVE_CATALOG is not None else 0;
    checkout_ready = ACTIVE_CATALOG.checkout_ready_products
        if ACTIVE_CATALOG is not None
        else 0;
    online = bool(
        ACTIVE_CATALOG is not None
        and ACTIVE_CATALOG.checkout_ready_products > 0
        and os.getenv("LINQ_API_KEY")
        and os.getenv("LINQ_WEBHOOK_SECRET")
        and bool(PUBLIC_LINQ_PHONE)
        and LINQ_PHONE_REPUTATION != "CRITICAL"
        and (not band_gate.is_enabled() or band_gate.is_configured())
    );
    updated_at = _utc_now();
    return {
        "status": "online" if online else "degraded",
        "online": online,
        "phoneNumber": {
            "display": PUBLIC_LINQ_PHONE,
            "public": bool(PUBLIC_LINQ_PHONE),
            "reputation": LINQ_PHONE_REPUTATION
        },
        "conversations": len(conversations),
        "recommendations": len(recommended_messages),
        "paymentLinksSent": len(checkout_messages),
        "updatedAt": updated_at,
        "catalog_products": catalog_count,
        "checkout_ready_products": checkout_ready,
        "messages_handled": len(handled_messages),
        "recommendations_sent": len(recommended_messages),
        "checkout_links_sent": len(checkout_messages),
        "pending_events": len(pending_event_ids()),
        "catalog_version": ACTIVE_CATALOG.version
            if ACTIVE_CATALOG is not None
            else "unavailable",
        "catalog_error": "" if not CATALOG_ERROR else "catalog_unavailable_or_invalid",
        "linq_configured": bool(os.getenv("LINQ_API_KEY")),
        "webhook_verification_configured": bool(os.getenv("LINQ_WEBHOOK_SECRET")),
        "llm_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
        "link_experience_available": LINK_EXPERIENCE_AVAILABLE,
        "band_gate_enabled": band_gate.is_enabled(),
        "band_gate_configured": band_gate.is_configured(),
        "started_at": SERVICE_STARTED_AT
    };
}


def get_events(cursor: int = 0, limit: int = 100) -> dict[str, object] {
    events = _load_events();
    safe_cursor = max(cursor, 0);
    safe_limit = min(max(limit, 1), 250);
    selected = events[safe_cursor:safe_cursor + safe_limit];
    return {
        "events": selected,
        "next_cursor": safe_cursor + len(selected),
        "has_more": safe_cursor + len(selected) < len(events)
    };
}
