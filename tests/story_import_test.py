import pytest


def test_story_import_requires_attestation(app_client):
    res = app_client.post(
        "/api/stories/import",
        json={"text": "Hello there.", "max_scenes": 3, "attest_rights": False},
    )
    assert res.status_code == 400
    data = res.json()
    assert data["detail"] == "attest_rights_required"


def test_story_import_returns_fallback_scenarios(app_client):
    res = app_client.post(
        "/api/stories/import",
        json={"text": "A stranger approaches.\nThey ask for help.", "max_scenes": 2, "attest_rights": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["activated"] is False
    assert data["target_language"] in {"English", "Spanish", "Japanese"}
    assert isinstance(data["scenarios"], list) and len(data["scenarios"]) == 2
    assert data["scenarios"][0]["id"] == 1
    assert data["scenarios"][0]["language"]


@pytest.mark.parametrize(
    ("setting", "expected"),
    [
        ("Feudal Japan", "Japanese"),
        ("Tokyo alley", "Japanese"),
        ("Madrid", "Spanish"),
        ("Mexico City", "Spanish"),
    ],
)
def test_story_import_infers_language_from_setting(app_client, setting, expected):
    res = app_client.post(
        "/api/stories/import",
        json={"text": "A short seed.", "setting": setting, "max_scenes": 1, "attest_rights": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_language"] == expected
    assert data["scenarios"][0]["language"] == expected


def test_story_import_respects_target_language_override(app_client):
    res = app_client.post(
        "/api/stories/import",
        json={"text": "A short seed.", "target_language": "Spanish", "max_scenes": 1, "attest_rights": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_language"] == "Spanish"
    assert data["scenarios"][0]["language"] == "Spanish"


def test_story_import_includes_advanced_scene(app_client):
    res = app_client.post(
        "/api/stories/import",
        json={"text": "Line one.\nLine two.\nLine three.", "max_scenes": 3, "attest_rights": True},
    )
    assert res.status_code == 200
    data = res.json()
    scenarios = data["scenarios"]
    assert scenarios[0]["mode"] == "beginner"
    assert any(scene.get("mode") == "advanced" for scene in scenarios)
