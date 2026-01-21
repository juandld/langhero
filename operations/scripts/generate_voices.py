#!/usr/bin/env python3
"""Generate example voice lines for scenario option examples via OpenAI TTS.

Delegates the core caching logic to `backend/voice_cache.py` so both the backend
runtime and this batch script share the same manifest + clip ID format.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _resolve_repo_root()
BACKEND_DIR = REPO_ROOT / "backend"
for p in (BACKEND_DIR, REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import config  # noqa: E402
import voice_cache  # noqa: E402

# Re-export for pytest imports (tests/voice_generation_test.py)
generate_for_scenarios = voice_cache.generate_for_scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate scenario example voices via OpenAI TTS.")
    parser.add_argument(
        "--scenario-file",
        default=str(REPO_ROOT / "backend" / "scenarios.json"),
        help="Path to the scenario JSON file (default: backend/scenarios.json).",
    )
    parser.add_argument(
        "--output-dir",
        default=str(config.EXAMPLES_AUDIO_DIR),
        help="Directory where audio files + manifest are stored (default: backend config path).",
    )
    parser.add_argument("--voice", default="alloy", help="OpenAI voice name (default: alloy).")
    parser.add_argument("--format", default="mp3", help="Audio format/extension (default: mp3).")
    parser.add_argument(
        "--manifest",
        default=None,
        help="Path to manifest JSON (default: <output-dir>/manifest.json).",
    )
    parser.add_argument(
        "--link-index",
        default=None,
        help="Path to scenario clip index JSON (default: <output-dir>/scenario_clips.json).",
    )
    parser.add_argument(
        "--max-variants",
        type=int,
        default=4,
        help="Maximum number of cached variants per unique phrase (default: 4).",
    )
    parser.add_argument(
        "--expand-variants",
        action="store_true",
        help="Allow up to --max-variants per phrase (default: reuse single variant per phrase).",
    )
    parser.add_argument(
        "--write-copies",
        action="store_true",
        help="Also emit legacy scenario-specific copies (default: reference canonical clips only).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Regenerate scenario-specific files even if they already exist.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List planned work without touching the filesystem or OpenAI APIs.",
    )
    args = parser.parse_args()

    if not args.dry_run and not config.OPENAI_API_KEY:
        parser.error("OPENAI_API_KEY is not set. Export it or add it to backend/.env before running.")

    scenario_path = Path(args.scenario_file)
    if not scenario_path.exists():
        parser.error(f"Scenario file not found: {scenario_path}")

    with scenario_path.open("r", encoding="utf-8") as f:
        scenarios = json.load(f)

    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest or (output_dir / "manifest.json"))
    link_index_path = Path(args.link_index or (output_dir / "scenario_clips.json"))
    stats = generate_for_scenarios(
        scenarios,
        output_dir=output_dir,
        voice=args.voice,
        fmt=args.format,
        manifest_path=manifest_path,
        link_index_path=link_index_path,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        max_variants=max(1, args.max_variants),
        expand_variants=args.expand_variants,
        write_copies=args.write_copies,
    )

    summary = (
        f"variants_created={stats.variants_created}, "
        f"variants_reused={stats.variants_reused}, "
        f"links_recorded={stats.links_recorded}, "
        f"scenario_copies={stats.scenario_copies}, "
        f"synth_calls={stats.synth_calls}"
    )
    print(f"Done. {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
