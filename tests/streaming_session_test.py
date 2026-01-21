import asyncio

import pytest

from backend import streaming
from tests.fixtures import scenarios as scenario_fixtures


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
            1: scenario_fixtures.beginner_scenario(
                id=1,
                lives=5,
                reward_points=25,
                penalties={
                    "language_mismatch": {"points": 15, "lives": 2},
                    "incorrect_answer": {"lives": 3},
                },
            )
        }
    )

    session = streaming.create_session({"scenario_id": 1, "language": "japanese"})

    assert session.lives_total == 5
    assert session.lives_remaining == 5
    assert session.points_per_success == 25
    assert session.points_per_penalty == 15
    assert session.target_language == "japanese"
    assert session.language_penalty_lives == 2
    assert session.incorrect_penalty_lives == 3
    assert session.mode == "beginner"


def test_create_session_advanced_mode(session_env):
    session_env.update({2: scenario_fixtures.advanced_scenario(id=2, lives=2, reward_points=20)})

    session = streaming.create_session({"scenario_id": 2})

    assert session.mode == "advanced"
    assert session.lives_total == 2
    assert session.points_per_success == 20


def test_finalize_applies_score_delta(session_env, monkeypatch):
    session_env.update(
        {
            1: scenario_fixtures.beginner_scenario(id=1, reward_points=10),
            2: scenario_fixtures.advanced_scenario(id=2, mode="advanced"),
        }
    )

    session = streaming.create_session({"scenario_id": 1})
    session.audio_buffer.extend(b"fake-bytes")

    def fake_process_interaction(_audio, _scenario_id, _lang, judge=None):
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
    assert final_event["mode"] == "beginner"


def test_finalize_applies_life_penalty(session_env, monkeypatch):
    session_env.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                reward_points=5,
                penalties={"incorrect_answer": {"lives": 2}},
            )
        }
    )

    session = streaming.create_session({"scenario_id": 1})
    session.audio_buffer.extend(b"fake-bytes")

    def fake_process_interaction(_audio, _scenario_id, _lang, judge=None):
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
    assert penalty_event["mode"] == "beginner"


def test_auto_finalize_on_match(session_env, monkeypatch):
    session_env.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                reward_points=10,
                penalties={"incorrect_answer": {"lives": 1}},
            ),
            2: scenario_fixtures.advanced_scenario(id=2, mode="advanced"),
        }
    )

    session = streaming.create_session({"scenario_id": 1})

    call_count = {"count": 0}

    def fake_process_interaction(_audio, _scenario_id, _lang, judge=None):
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
    assert ws.messages[-1]["mode"] == "beginner"


def test_language_penalty_respects_config(session_env):
    session_env.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                lives=4,
                penalties={
                    "language_mismatch": {"lives": 2},
                },
            )
        }
    )

    session = streaming.create_session({"scenario_id": 1, "language": "japanese"})
    ws = DummyWebSocket()

    asyncio.run(session.apply_language_penalty("english", ws))

    assert session.lives_remaining == session.lives_total - 2
    event = ws.messages[-1]
    assert event["event"] == "penalty"
    assert event["lives_delta"] == -2
    assert event["mode"] == "beginner"


def test_partial_language_penalty_disabled_when_story_first(session_env, monkeypatch):
    session_env.update({1: scenario_fixtures.beginner_scenario(id=1, lives=3)})

    async def fake_transcribe_audio(_data, _language=None):
        await asyncio.sleep(0)
        return "yes please"

    monkeypatch.setattr(streaming, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(streaming, "process_interaction", lambda *_args, **_kwargs: {"error": "nope"})

    session = streaming.create_session({"scenario_id": 1, "language": "japanese", "judge": 1.0})
    ws = DummyWebSocket()

    async def run_flow():
        await session.append_chunk(b"0" * 20000, ws)
        await asyncio.sleep(0.05)

    asyncio.run(run_flow())

    assert session.lives_remaining == session.lives_total
    assert all(msg.get("event") != "penalty" for msg in ws.messages)
