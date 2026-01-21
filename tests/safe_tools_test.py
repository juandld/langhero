import io


def test_translate_endpoint_never_penalizes(app_client):
    resp = app_client.post(
        "/narrative/translate",
        data={
            "text": "Hello there",
            "native": "English",
            "target": "Japanese",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "livesDelta" not in payload
    assert "scoreDelta" not in payload


def test_imitate_endpoint_safe_zone(app_client):
    audio_bytes = io.BytesIO(b"stub audio")
    files = {"audio_file": ("line.webm", audio_bytes, "audio/webm")}
    resp = app_client.post(
        "/narrative/imitate",
        data={"expected": "はい", "lang": "Japanese"},
        files=files,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "livesDelta" not in payload
    assert "scoreDelta" not in payload
