import asyncio

import streaming


def test_streaming_interaction_flow(app_client, monkeypatch):
    async def _fake_transcribe(_audio_bytes: bytes, _language=None) -> str:
        await asyncio.sleep(0)
        return "hello world"

    def _fake_process(_audio_file, _scenario_id, _lang):
        return {"heard": "final heard", "nextScenario": 5}

    monkeypatch.setattr(streaming, "transcribe_audio", _fake_transcribe, raising=False)
    monkeypatch.setattr(streaming, "process_interaction", _fake_process, raising=False)

    with app_client.websocket_connect("/stream/interaction") as ws:
        ws.send_json({"scenario_id": 1, "language": "japanese"})
        ready = ws.receive_json()
        assert ready["event"] == "ready"
        assert ready["lives_total"] == 3
        assert ready["lives_remaining"] == 3
        assert ready["score"] == 0

        ws.send_bytes(b"chunk-1")
        partial = ws.receive_json()
        assert partial["event"] == "partial"
        assert partial["transcript"] == "hello world"

        penalty = ws.receive_json()
        assert penalty["event"] == "penalty"
        assert penalty["detected_language"] == "english"
        assert penalty["lives_remaining"] == 2
        assert penalty["score"] == 0
        assert isinstance(penalty["message"], str) and penalty["message"]

        ws.send_text("stop")
        final = ws.receive_json()
        assert final["event"] == "final"
        assert final["result"]["nextScenario"] == 5
        assert final["score"] >= 0
        assert final["lives_remaining"] == 2
