def test_auto_import_text_only(app_client):
    res = app_client.post(
        "/api/import/auto",
        json={"text": "A stranger approaches.", "max_scenes": 1, "attest_rights": True, "activate": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kind"] == "text"
    assert isinstance(data.get("scenarios"), list) and data["scenarios"]


def test_auto_import_web_url_prefers_url_fetch(app_client, monkeypatch):
    import main as main_module

    def fake_fetch(url: str, **_kwargs):
        return {
            "url": url,
            "final_url": url,
            "content_type": "text/html; charset=utf-8",
            "title": "Example Page",
            "text": "Line one.\nLine two.",
        }

    monkeypatch.setattr(main_module.url_fetch, "fetch_url_text", fake_fetch, raising=True)

    res = app_client.post(
        "/api/import/auto",
        json={"url": "https://example.com/page", "max_scenes": 2, "attest_rights": True, "activate": False},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kind"] == "web"
    assert data.get("source", {}).get("title") == "Example Page"
    assert isinstance(data.get("scenarios"), list) and len(data["scenarios"]) == 2


def test_auto_import_video_url_uses_video_pipeline(app_client, monkeypatch):
    import main as main_module

    calls = {"count": 0}

    def fake_generate(url: str, target_language: str, max_scenes: int):
        calls["count"] += 1
        return [{"id": 1, "description": "A"}, {"id": 2, "description": "B"}]

    monkeypatch.setattr(main_module, "generate_scenarios_from_video", fake_generate, raising=True)

    res = app_client.post(
        "/api/import/auto",
        json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "target_language": "Japanese",
            "max_scenes": 2,
            "attest_rights": True,
            "activate": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kind"] == "video"
    assert calls["count"] == 1
    assert isinstance(data.get("scenarios"), list) and len(data["scenarios"]) == 2
