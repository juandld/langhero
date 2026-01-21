def test_from_video_uses_cache(app_client, monkeypatch):
    calls = {"count": 0}

    def fake_generate(url: str, target_language: str, max_scenes: int):
        calls["count"] += 1
        return [
            {"id": 1, "description": "A"},
            {"id": 2, "description": "B"},
            {"id": 3, "description": "C"},
        ]

    import main as main_module

    monkeypatch.setattr(main_module, "generate_scenarios_from_video", fake_generate, raising=True)

    body = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "target_language": "Japanese",
        "max_scenes": 3,
        "activate": False,
        "attest_rights": True,
    }

    res1 = app_client.post("/api/scenarios/from_video", json=body)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ok"
    assert calls["count"] == 1
    assert data1.get("cached") in {False, True}  # cache may save after normalize
    assert any((s.get("mode") == "advanced") for s in data1.get("scenarios", []))

    res2 = app_client.post("/api/scenarios/from_video", json=body)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "ok"
    assert calls["count"] == 1  # second call should not invoke generator
    assert data2.get("cached") is True
    assert len(data2.get("scenarios") or []) == 3
