def test_story_import_supports_source_url(app_client, monkeypatch):
    import main as main_module

    def fake_fetch(url: str, **_kwargs):
        return {
            "url": url,
            "final_url": url,
            "content_type": "text/html; charset=utf-8",
            "title": "Example Page",
            "text": "A stranger approaches.\nThey ask for help.",
        }

    monkeypatch.setattr(main_module.url_fetch, "fetch_url_text", fake_fetch, raising=True)

    res = app_client.post(
        "/api/stories/import",
        json={
            "source_url": "https://example.com/story",
            "max_scenes": 2,
            "attest_rights": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data.get("scenarios"), list) and len(data["scenarios"]) == 2
    assert data.get("source", {}).get("title") == "Example Page"
