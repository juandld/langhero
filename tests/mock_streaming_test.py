def test_mock_streaming_endpoint(app_client):
    with app_client.websocket_connect("/stream/mock") as ws:
        ws.send_json({"scenario_id": "integration-test", "language": "en"})
        ready = ws.receive_json()
        assert ready["event"] == "ready"
        assert ready["scenario_id"] == "integration-test"
        assert ready["lives_total"] == 3
        assert ready["lives_remaining"] == 3
        assert ready["score"] == 0

        ws.send_bytes(b"hello")
        partial = ws.receive_json()
        assert partial["event"] == "partial"
        assert partial["seq"] == 1
        assert partial["bytes"] == 5
        assert "transcript" in partial

        ws.send_text("stop")
        final = ws.receive_json()
        assert final["event"] == "final"
        assert final["total_chunks"] == 1
        assert final["total_bytes"] == 5
        assert final["reason"] == "client_stop"
