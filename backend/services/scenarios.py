"""
Scenario data management.
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional

# Load scenario data
scenarios_path = os.path.join(os.path.dirname(__file__), '..', 'scenarios.json')
with open(scenarios_path, 'r') as f:
    scenarios_data = json.load(f)

SCENARIO_VERSIONS_DIR = os.path.join(os.path.dirname(__file__), '..', 'scenario_versions')


def get_scenario_by_id(scenario_id: int):
    """Finds a scenario in the loaded data by its ID."""
    for scenario in scenarios_data:
        if scenario["id"] == scenario_id:
            return scenario
    return None


def list_scenarios() -> list:
    """Return all scenarios."""
    return scenarios_data


def reload_scenarios(new_list: list) -> None:
    """Persist to file and update in-memory data."""
    global scenarios_data
    try:
        with open(scenarios_path, 'w') as f:
            json.dump(new_list, f, ensure_ascii=False, indent=2)
        scenarios_data = new_list
    except Exception as e:
        raise e


def ensure_versions_dir():
    """Ensure scenario versions directory exists."""
    os.makedirs(SCENARIO_VERSIONS_DIR, exist_ok=True)


def save_scenarios_version(label: Optional[str] = None) -> str:
    """Save the current scenarios into a timestamped JSON file and return filename."""
    ensure_versions_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_label = (label or "").strip().replace(" ", "_")
    name = f"scenarios-{ts}{('-' + safe_label) if safe_label else ''}.json"
    path = os.path.join(SCENARIO_VERSIONS_DIR, name)
    with open(path, 'w') as f:
        json.dump(scenarios_data, f, ensure_ascii=False, indent=2)
    return name


def list_scenario_versions() -> list[dict]:
    """List all saved scenario versions."""
    ensure_versions_dir()
    out = []
    for f in sorted(os.listdir(SCENARIO_VERSIONS_DIR)):
        if f.endswith('.json'):
            out.append({"filename": f})
    return out


def activate_scenario_version(filename: str) -> None:
    """Load and activate a specific scenario version."""
    ensure_versions_dir()
    path = os.path.join(SCENARIO_VERSIONS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(filename)
    with open(path, 'r') as f:
        data = json.load(f)
    reload_scenarios(data)
