import io

import pytest

from backend import services
from tests.fixtures import scenarios as scenario_fixtures


@pytest.fixture
def interaction_env(tmp_path, monkeypatch):
    voice = tmp_path / "voice"
    trans = tmp_path / "trans"
    voice.mkdir()
    trans.mkdir()

    monkeypatch.setattr(services, "VOICE_NOTES_DIR", str(voice))
    monkeypatch.setattr(services, "TRANSCRIPTS_DIR", str(trans))

    # Avoid network/provider calls
    monkeypatch.setattr(services.usage, "log_usage", lambda *args, **kwargs: None)
    monkeypatch.setattr(services.providers, "translate_text", lambda text, **_: "はい、お願いします。")
    monkeypatch.setattr(services.providers, "romanize", lambda text, *_: "hai, onegaishimasu")

    class Stub:
        transcript = "はい、お願いします。"

    stub = Stub()

    monkeypatch.setattr(
        services.providers,
        "transcribe_audio",
        lambda *args, **kwargs: services.providers.TranscriptionResult(
            text=stub.transcript,
            provider="openai",
            model="stub-model",
        ),
        raising=False,
    )
    monkeypatch.setattr(services.providers, "openai_chat", lambda *args, **kwargs: "0")

    scenarios = {}

    def fake_get_scenario_by_id(scenario_id):
        return scenarios.get(int(scenario_id)) if scenario_id is not None else None

    monkeypatch.setattr(services, "get_scenario_by_id", fake_get_scenario_by_id)

    return stub, scenarios


def make_audio():
    return io.BytesIO(b"\x00\x01fake-audio-data")


def test_process_interaction_awards_reward(interaction_env):
    stub, scenarios = interaction_env
    scenarios.clear()
    scenarios.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                reward_points=15,
                penalties={"incorrect_answer": {"lives": 2}},
                options=[
                    {
                        "text": "Yes",
                        "next_scenario": 2,
                        "examples": [{"target": "はい、お願いします。"}],
                    },
                    {
                        "text": "No",
                        "next_scenario": 3,
                        "examples": [{"target": "いいえ、結構です。"}],
                    },
                ],
            ),
            2: scenario_fixtures.advanced_scenario(id=2, options=[]),
            3: scenario_fixtures.advanced_scenario(id=3, options=[]),
        }
    )
    stub.transcript = "はい、お願いします。"

    result = services.process_interaction(make_audio(), "1", "Japanese")
    print("incorrect-result", result)

    assert result["nextScenario"]["id"] == 2
    assert result["scoreDelta"] == 15
    assert result["livesDelta"] == 0


def test_process_interaction_penalizes_incorrect_answer(interaction_env):
    stub, scenarios = interaction_env
    scenarios.clear()
    scenarios.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                reward_points=10,
                penalties={"incorrect_answer": {"lives": 2}},
                options=[
                    {
                        "text": "Yes",
                        "next_scenario": 2,
                        "examples": [{"target": "はい、お願いします。"}],
                    }
                ],
            ),
            2: scenario_fixtures.advanced_scenario(id=2, options=[]),
        }
    )
    stub.transcript = "ちがいます"

    result = services.process_interaction(make_audio(), "1", "Japanese")

    assert result["npcDoesNotUnderstand"] is True
    assert result["scoreDelta"] == 0
    assert result["livesDelta"] == -2


def test_process_interaction_penalizes_wrong_language(interaction_env):
    stub, scenarios = interaction_env
    scenarios.clear()
    scenarios.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                reward_points=10,
                penalties={
                    "incorrect_answer": {"lives": 1},
                    "language_mismatch": {"lives": 3, "points": 12},
                },
                options=[
                    {
                        "text": "Yes",
                        "next_scenario": 2,
                        "examples": [{"target": "はい、お願いします。"}],
                    }
                ],
            ),
            2: scenario_fixtures.advanced_scenario(id=2, options=[]),
        }
    )
    stub.transcript = "yes please"

    result = services.process_interaction(make_audio(), "1", "Japanese")

    assert result["npcDoesNotUnderstand"] is True
    assert "repeatExpected" not in result
    assert result["livesDelta"] == -3
    assert result["scoreDelta"] == 0


def test_process_interaction_story_first_allows_wrong_language(interaction_env):
    stub, scenarios = interaction_env
    scenarios.clear()
    scenarios.update(
        {
            1: scenario_fixtures.beginner_scenario(
                id=1,
                reward_points=10,
                penalties={
                    "incorrect_answer": {"lives": 1},
                    "language_mismatch": {"lives": 3, "points": 12},
                },
                options=[
                    {
                        "text": "Yes",
                        "next_scenario": 2,
                        "examples": [{"target": "はい、お願いします。"}],
                    }
                ],
            ),
            2: scenario_fixtures.advanced_scenario(id=2, options=[]),
        }
    )
    stub.transcript = "yes please"

    result = services.process_interaction(make_audio(), "1", "Japanese", judge=1.0)

    assert result["nextScenario"]["id"] == 2
    assert result["scoreDelta"] == 10
    assert result["livesDelta"] == 0
