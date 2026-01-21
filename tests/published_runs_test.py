def test_publish_requires_attestation(app_client):
    res = app_client.post(
        "/api/published_runs",
        json={"title": "t", "scenarios": [{"id": 1}], "confirm_publish": True, "attest_rights": False},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "attest_rights_required"


def test_publish_requires_confirm_publish(app_client):
    res = app_client.post(
        "/api/published_runs",
        json={"title": "t", "scenarios": [{"id": 1}], "confirm_publish": False, "attest_rights": True},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "confirm_publish_required"


def test_publish_roundtrip_and_delete(app_client):
    scenarios = [
        {"id": 1, "mode": "beginner", "lives": 3, "reward_points": 10, "penalties": {}, "options": []},
        {"id": 2, "mode": "advanced", "lives": 2, "reward_points": 15, "penalties": {}, "options": []},
    ]
    res = app_client.post(
        "/api/published_runs",
        json={
            "title": "Shared test run",
            "target_language": "Japanese",
            "scenarios": scenarios,
            "attest_rights": True,
            "confirm_publish": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    public_id = data["public_id"]
    delete_key = data["delete_key"]
    assert public_id
    assert delete_key
    assert data["title"] == "Shared test run"
    assert isinstance(data["scenarios"], list) and len(data["scenarios"]) == 2

    res2 = app_client.get(f"/api/published_runs/{public_id}")
    assert res2.status_code == 200
    fetched = res2.json()
    assert fetched["public_id"] == public_id
    assert fetched["title"] == "Shared test run"
    assert "delete_key" not in fetched
    assert isinstance(fetched["scenarios"], list) and len(fetched["scenarios"]) == 2

    res3 = app_client.request("DELETE", f"/api/published_runs/{public_id}", json={"delete_key": "wrong"})
    assert res3.status_code == 403

    res4 = app_client.request("DELETE", f"/api/published_runs/{public_id}", json={"delete_key": delete_key})
    assert res4.status_code == 200
    assert res4.json()["status"] == "ok"

    res5 = app_client.get(f"/api/published_runs/{public_id}")
    assert res5.status_code == 404
