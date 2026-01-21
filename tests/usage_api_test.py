import usage_log as usage


def test_api_meta(app_client):
    res = app_client.get("/api/meta")
    assert res.status_code == 200
    data = res.json()
    assert "demo_mode" in data
    assert "demo_video_cache_only" in data
    assert "demo_allow_llm_import" in data
    assert "demo_disable_streaming" in data
    assert "utc_now" in data


def test_usage_endpoints_reflect_logged_events(app_client):
    usage.log_usage(event="unit_test_event", provider="openai", model="stub-model", key_label=usage.OPENAI_LABEL)
    usage.log_usage(event="unit_test_event", provider="openai", model="stub-model", key_label=usage.OPENAI_LABEL)

    weekly = app_client.get("/api/usage/weekly").json()
    assert weekly["totals"]["events"] >= 2
    assert weekly["events"].get("unit_test_event", 0) >= 2
    assert weekly["providers"].get("openai", 0) >= 2
    assert weekly["models"].get("stub-model", 0) >= 2
    assert weekly["by_event_provider_model"].get("unit_test_event|openai|stub-model", 0) >= 2

    recent = app_client.get("/api/usage/recent?limit=10&days=2")
    assert recent.status_code == 200
    payload = recent.json()
    assert payload["limit"] == 10
    assert payload["days"] == 2
    assert any((e.get("event") == "unit_test_event") for e in (payload.get("events") or []))

