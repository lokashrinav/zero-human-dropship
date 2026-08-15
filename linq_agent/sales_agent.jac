import agent_runtime;


def initialize_service -> dict[str, object] {
    return agent_runtime.bootstrap();
}


def enqueue_linq_webhook(raw_text: str) -> dict[str, object] {
    return agent_runtime.ingest_webhook(raw_text);
}


def process_linq_event(event_id: str) -> dict[str, object] {
    result = agent_runtime.process_pending_event(event_id);
    agent_runtime.flush_event_sink();
    return result;
}


def recover_pending_events(limit: int = 50) -> dict[str, object] {
    result = agent_runtime.process_all_pending(limit);
    agent_runtime.flush_event_sink();
    return result;
}


def check_linq_authentication -> dict[str, object] {
    return agent_runtime.check_linq_authentication();
}


def service_status -> dict[str, object] {
    agent_runtime.refresh_catalog();
    return agent_runtime.get_status();
}


def dashboard_events(cursor: int = 0, limit: int = 100) -> dict[str, object] {
    return agent_runtime.get_events(cursor, limit);
}


def reload_catalog -> dict[str, object] {
    return agent_runtime.refresh_catalog(force=True);
}


with entry:__main__ {
    print(initialize_service());
}
