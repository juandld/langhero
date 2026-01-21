from __future__ import annotations

import json
from pathlib import Path

import pytest

from operations.scripts import generate_voices


class StubSynth:
    def __init__(self):
        self.calls: list[tuple[str, str, str]] = []
        self.counter = 0

    def __call__(self, text: str, voice: str, fmt: str) -> bytes:
        self.counter += 1
        self.calls.append((text, voice, fmt))
        return f"{self.counter}:{voice}:{text}".encode("utf-8")


def _sample_scenarios(repetitions: int = 1) -> list[dict]:
    options = []
    for idx in range(repetitions):
        options.append(
            {
                "text": f"Option {idx}",
                "examples": [
                    {
                        "native": "Example",
                        "target": "はい、お願いします。",
                    }
                ],
            }
        )
    return [
        {
            "id": 1,
            "language": "Japanese",
            "options": options,
        }
    ]


def test_basic_generation_creates_manifest(tmp_path):
    scenarios = _sample_scenarios()
    manifest_path = tmp_path / "manifest.json"
    synth = StubSynth()

    index_path = tmp_path / "scenario_clips.json"

    stats = generate_voices.generate_for_scenarios(
        scenarios,
        output_dir=tmp_path,
        voice="alloy",
        fmt="mp3",
        manifest_path=manifest_path,
        link_index_path=index_path,
        synthesizer=synth,
    )

    assert stats.variants_created == 1
    assert stats.links_recorded == 1
    assert synth.calls == [("はい、お願いします。", "alloy", "mp3")]
    # Canonical clip stored under phrases/
    phrases = list((tmp_path / "phrases").glob("*.mp3"))
    assert len(phrases) == 1
    assert phrases[0].read_bytes().startswith(b"1:alloy:")
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest["phrases"]) == 1
    link_index = json.loads(index_path.read_text())
    entry = link_index["scenario-1-opt0-ex0.mp3"]
    assert entry["clip_id"].startswith("clip_")
    assert entry["file"].startswith("phrases/")


def test_reuse_skips_duplicate_synthesis(tmp_path):
    scenarios = _sample_scenarios()
    manifest_path = tmp_path / "manifest.json"
    synth = StubSynth()
    index_path = tmp_path / "scenario_clips.json"

    generate_voices.generate_for_scenarios(
        scenarios,
        output_dir=tmp_path,
        voice="alloy",
        fmt="mp3",
        manifest_path=manifest_path,
        link_index_path=index_path,
        synthesizer=synth,
    )
    assert len(synth.calls) == 1

    second_run = [
        {
            "id": 2,
            "language": "Japanese",
            "options": [
                {
                    "text": "Option again",
                    "examples": [{"native": "Example", "target": "はい、お願いします。"}],
                }
            ],
        }
    ]

    stats = generate_voices.generate_for_scenarios(
        second_run,
        output_dir=tmp_path,
        voice="alloy",
        fmt="mp3",
        manifest_path=manifest_path,
        link_index_path=index_path,
        synthesizer=synth,
    )

    assert len(synth.calls) == 1, "synthesizer should not be invoked again for identical phrase"
    assert stats.variants_reused == 1
    link_index = json.loads(index_path.read_text())
    assert "scenario-2-opt0-ex0.mp3" in link_index
    assert link_index["scenario-2-opt0-ex0.mp3"]["clip_id"] == link_index["scenario-1-opt0-ex0.mp3"]["clip_id"]


def test_variant_cap_and_round_robin(tmp_path):
    scenarios = _sample_scenarios(repetitions=5)
    manifest_path = tmp_path / "manifest.json"
    synth = StubSynth()

    index_path = tmp_path / "scenario_clips.json"
    stats = generate_voices.generate_for_scenarios(
        scenarios,
        output_dir=tmp_path,
        voice="verse",
        fmt="mp3",
        manifest_path=manifest_path,
        max_variants=2,
        expand_variants=True,
        link_index_path=index_path,
        synthesizer=synth,
    )

    assert stats.variants_created == 2
    assert len(synth.calls) == 2

    # Link index should alternate clip IDs across options
    link_index = json.loads(index_path.read_text())
    payloads = []
    for _, meta in sorted(link_index.items()):
        clip_path = tmp_path / meta["file"]
        assert clip_path.exists()
        payloads.append(clip_path.read_bytes())
    unique_payloads = {payload for payload in payloads}
    assert len(unique_payloads) == 2


def test_dry_run_does_not_write_or_call_openai(tmp_path):
    scenarios = _sample_scenarios()
    manifest_path = tmp_path / "manifest.json"
    synth = StubSynth()

    stats = generate_voices.generate_for_scenarios(
        scenarios,
        output_dir=tmp_path,
        voice="alloy",
        fmt="mp3",
        manifest_path=manifest_path,
        link_index_path=tmp_path / "scenario_clips.json",
        dry_run=True,
        synthesizer=synth,
    )

    assert stats.links_recorded == 1
    assert len(list(tmp_path.glob("phrases/*.mp3"))) == 0
    assert not manifest_path.exists()
    assert synth.calls == []
