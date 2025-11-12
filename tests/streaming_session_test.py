import asyncio

import pytest

from backend import streaming


class DummyWebSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, payload):
        self.messages.append(payload)


@pytest.fixture
def session_env(monkeypatch):
    scenarios = {}

    def fake_get_scenario_by_id(scenario_id):
        return scenarios.get(int(scenario_id)) if scenario_id is not None else None

    monkeypatch.setattr(streaming, "get_scenario_by_id", fake_get_scenario_by_id)

    async def fake_transcribe_audio(data, language=None):
        await asyncio.sleep(0)
        return "mock transcript"

    monkeypatch.setattr(streaming, "transcribe_audio", fake_transcribe_audio)

    return scenarios


def test_create_session_uses_scenario_defaults(session_env):
    session_env.update(
        {
            1: {
                "id": 1,
                "lives": 5,
                "reward_points": 25,
                "penalties": {
                    "language_mismatch": {"points": 15},
                },
            }
        }
    )

    session = streaming.create_session({"scenario_id": 1, "language": "japanese"})

    assert session.lives_total == 5
    assert session.lives_remaining == 5
    assert session.points_per_success == 25
    assert session.points_per_penalty == 15
    assert session.target_language == "japanese"


def test_finalize_applies_score_delta(session_env, monkeypatch):
    session_env.update(
        {
            1: {"id": 1, "reward_points": 10},
            2: {"id": 2},
        }
    )

    session = streaming.create_session({"scenario_id": 1})
    session.audio_buffer.extend(b"fake-bytes")

    def fake_process_interaction(_audio, _scenario_id, _lang):
        return {
            "nextScenario": {"id": 2},
            "heard": "こんにちは",
            "scoreDelta": 30,
            "livesDelta": 0,
        }

    monkeypatch.setattr(streaming, "process_interaction", fake_process_interaction)

    ws = DummyWebSocket()
    asyncio.run(session.finalize(ws))

    assert session.score == 30
    assert session.lives_remaining == session.lives_total
    final_event = ws.messages[-1]
    assert final_event["event"] == "final"
    assert final_event["score"] == 30
    assert final_event["lives_remaining"] == session.lives_total


def test_finalize_applies_life_penalty(session_env, monkeypatch):
    session_env.update(
        {
            1: {
                "id": 1,
                "reward_points": 5,
                "penalties": {"incorrect_answer": {"lives": 2}},
            }
        }
    )

    session = streaming.create_session({"scenario_id": 1})
    session.audio_buffer.extend(b"fake-bytes")

    def fake_process_interaction(_audio, _scenario_id, _lang):
        return {
            "error": "No match",
            "heard": "",
            "scoreDelta": 0,
            "livesDelta": -2,
        }

    monkeypatch.setattr(streaming, "process_interaction", fake_process_interaction)

    ws = DummyWebSocket()
    asyncio.run(session.finalize(ws))

    assert session.score == 0
    assert session.lives_remaining == session.lives_total - 2
    penalty_event = ws.messages[-2]
    assert penalty_event["event"] == "penalty"
    assert penalty_event["type"] == "incorrect_answer"
    assert penalty_event["lives_delta"] == -2


def test_auto_finalize_on_match(session_env, monkeypatch):
    session_env.update(
        {
            1: {
                "id": 1,
                "reward_points": 10,
                "penalties": {"incorrect_answer": {"lives": 1}},
            },
            2: {"id": 2},
        }
    )

    session = streaming.create_session({"scenario_id": 1})

    call_count = {"count": 0}

    def fake_process_interaction(_audio, _scenario_id, _lang):
        call_count["count"] += 1
        return {
            "nextScenario": {"id": 2},
            "heard": "はい、お願いします。",
            "scoreDelta": 15,
            "livesDelta": 0,
        }

    monkeypatch.setattr(streaming, "process_interaction", fake_process_interaction)

    ws = DummyWebSocket()

    async def run_flow():
        await session.append_chunk(b"0" * 20000, ws)
        await asyncio.sleep(0.05)

    asyncio.run(run_flow())

    assert session.auto_finalized is True
    assert session.final_event_sent is True
    assert session.score == 15
    assert call_count["count"] == 1
    assert ws.messages[-1]["event"] == "final"
