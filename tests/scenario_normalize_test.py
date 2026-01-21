from scenario_normalize import normalize_scenarios


def test_normalize_scenarios_sets_mode_defaults_and_advanced():
    scenarios = [
        {"id": 1, "description": "A"},
        {"id": 2, "description": "B"},
        {"id": 3, "description": "C"},
    ]
    normalize_scenarios(scenarios, ensure_advanced=True)
    assert scenarios[0]["mode"] == "beginner"
    assert any(s.get("mode") == "advanced" for s in scenarios)
    assert all(isinstance(s.get("lives"), int) and s["lives"] > 0 for s in scenarios)
    assert all(isinstance(s.get("reward_points"), int) and s["reward_points"] >= 0 for s in scenarios)
    assert all(isinstance(s.get("penalties"), dict) for s in scenarios)


def test_normalize_scenarios_preserves_existing_modes():
    scenarios = [
        {"id": 1, "mode": "beginner"},
        {"id": 2, "mode": "advanced"},
        {"id": 3, "mode": "beginner"},
    ]
    normalize_scenarios(scenarios, ensure_advanced=True)
    assert [s["mode"] for s in scenarios] == ["beginner", "advanced", "beginner"]

