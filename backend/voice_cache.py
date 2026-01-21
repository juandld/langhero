from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple
from uuid import uuid4

import config
import providers

Synthesizer = Callable[[str, str, str], bytes]


def iter_examples(scenarios: list[dict]) -> Iterable[Tuple[int, int, int, str, str]]:
    """Yield (scenario_id, option_idx, example_idx, target_text, language_hint)."""
    for scenario in scenarios:
        scenario_id = scenario.get("id")
        if scenario_id is None:
            continue
        scenario_lang = (scenario.get("language") or "").strip()
        for opt_idx, option in enumerate(scenario.get("options") or []):
            option_lang = (option.get("language") or "").strip()
            for ex_idx, example in enumerate(option.get("examples") or []):
                target = (example.get("target") or "").strip()
                if not target:
                    continue
                example_lang = (example.get("language") or "").strip()
                lang = example_lang or option_lang or scenario_lang
                yield int(scenario_id), opt_idx, ex_idx, target, lang


def normalize_phrase(text: str, language: str | None = None) -> str:
    """Normalize text for manifest keys (collapse whitespace, lowercase ASCII)."""
    collapsed = " ".join((text or "").strip().split())
    if collapsed.isascii():
        collapsed = collapsed.lower()
    lang_key = (language or "").strip().lower()
    return f"{lang_key}::{collapsed}"


def phrase_digest(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def default_manifest() -> dict:
    return {"version": 1, "phrases": {}}


def load_manifest(path: Path) -> dict:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "phrases" in data:
                return data
        except Exception:
            pass
    return default_manifest()


def _atomic_json_write(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
    Path(tmp.name).replace(path)


def save_manifest(data: dict, path: Path) -> None:
    _atomic_json_write(data, path)


@dataclass
class GenerationStats:
    variants_created: int = 0
    variants_reused: int = 0
    synth_calls: int = 0
    links_recorded: int = 0
    scenario_copies: int = 0
    dry_run: bool = False


def _ensure_entry(manifest: dict, key: str, phrase: str, language: str | None) -> dict:
    phrases = manifest.setdefault("phrases", {})
    entry = phrases.get(key)
    if not entry:
        entry = {
            "phrase": phrase,
            "language": language or "",
            "variants": [],
            "next_index": 0,
            "phrase_id": f"phr_{uuid4().hex}",
        }
        phrases[key] = entry
    else:
        if phrase and not entry.get("phrase"):
            entry["phrase"] = phrase
        if language and not entry.get("language"):
            entry["language"] = language
        entry.setdefault("next_index", 0)
        entry.setdefault("variants", [])
        entry.setdefault("phrase_id", f"phr_{uuid4().hex}")
    return entry


def _create_variant(
    *,
    entry: dict,
    key: str,
    phrase: str,
    output_dir: Path,
    voice: str,
    fmt: str,
    synthesizer: Synthesizer,
    dry_run: bool,
    stats: Optional[GenerationStats] = None,
) -> dict:
    variants = entry["variants"]
    idx = len(variants)
    digest = phrase_digest(key)
    rel_path = f"phrases/phrase-{digest}-v{idx}.{fmt}"
    abs_path = output_dir / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        audio_bytes = synthesizer(phrase, voice, fmt)
        abs_path.write_bytes(audio_bytes)
        if stats is not None:
            stats.synth_calls += 1
    variant = {
        "variant_id": f"clip_{uuid4().hex}",
        "file": rel_path,
        "voice": voice,
        "format": fmt,
    }
    variants.append(variant)
    if stats is not None:
        stats.variants_created += 1
    return variant


def _select_variant(entry: dict) -> dict:
    variants = entry["variants"]
    idx = entry.get("next_index", 0) % max(1, len(variants))
    entry["next_index"] = (idx + 1) % max(1, len(variants))
    variant = variants[idx]
    if "variant_id" not in variant:
        variant["variant_id"] = f"clip_{uuid4().hex}"
    return variant


def _ensure_variant_file(
    *,
    output_dir: Path,
    variant: dict,
    phrase: str,
    voice: str,
    fmt: str,
    synthesizer: Synthesizer,
    dry_run: bool,
    stats: Optional[GenerationStats] = None,
) -> Path:
    rel = variant["file"]
    abs_path = output_dir / rel
    if abs_path.exists() or dry_run:
        return abs_path
    audio_bytes = synthesizer(phrase, variant.get("voice", voice), variant.get("format", fmt))
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(audio_bytes)
    if stats is not None:
        stats.synth_calls += 1
    return abs_path


def get_or_create_clip(
    phrase: str,
    *,
    language: str | None = None,
    output_dir: Path | None = None,
    manifest_path: Path | None = None,
    voice: str = "alloy",
    fmt: str = "mp3",
    max_variants: int = 4,
    expand_variants: bool = False,
    dry_run: bool = False,
    synthesizer: Synthesizer | None = None,
) -> dict:
    """Return a manifest-backed voice clip for the given phrase.

    The clip is deduplicated across identical phrases (via normalization key).
    Returns metadata: {clip_id, phrase_id, file, voice, format}.
    """
    output_dir = output_dir or Path(config.EXAMPLES_AUDIO_DIR)
    manifest_path = manifest_path or (output_dir / "manifest.json")
    output_dir.mkdir(parents=True, exist_ok=True)

    synth = synthesizer or providers.tts_with_openai
    key = normalize_phrase(phrase, language)
    manifest = load_manifest(manifest_path)
    entry = _ensure_entry(manifest, key, phrase, language)

    create_new = not entry["variants"]
    if not create_new and expand_variants and len(entry["variants"]) < max(1, max_variants):
        create_new = True

    if create_new:
        variant = _create_variant(
            entry=entry,
            key=key,
            phrase=phrase,
            output_dir=output_dir,
            voice=voice,
            fmt=fmt,
            synthesizer=synth,
            dry_run=dry_run,
            stats=None,
        )
    else:
        variant = _select_variant(entry)

    _ensure_variant_file(
        output_dir=output_dir,
        variant=variant,
        phrase=phrase,
        voice=voice,
        fmt=fmt,
        synthesizer=synth,
        dry_run=dry_run,
        stats=None,
    )

    if not dry_run:
        save_manifest(manifest, manifest_path)

    return {
        "clip_id": variant["variant_id"],
        "phrase_id": entry.get("phrase_id"),
        "file": variant["file"],
        "voice": variant.get("voice", voice),
        "format": variant.get("format", fmt),
    }


def generate_for_scenarios(
    scenarios: list[dict],
    *,
    output_dir: Path,
    voice: str,
    fmt: str,
    manifest_path: Path,
    link_index_path: Path | None = None,
    overwrite: bool = False,
    dry_run: bool = False,
    max_variants: int = 4,
    expand_variants: bool = False,
    write_copies: bool = False,
    synthesizer: Synthesizer | None = None,
) -> GenerationStats:
    """Batch-generate cached phrase clips for scenario example phrases."""
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = GenerationStats(dry_run=dry_run)
    manifest = load_manifest(manifest_path)
    links: dict[str, dict] = {}
    processed_keys: set[str] = set()
    synth_func = synthesizer or providers.tts_with_openai

    for scenario_id, opt_idx, ex_idx, text, language in iter_examples(scenarios):
        fname = f"scenario-{scenario_id}-opt{opt_idx}-ex{ex_idx}.{fmt}"
        dest_path = output_dir / fname
        key = normalize_phrase(text, language)
        entry = _ensure_entry(manifest, key, text, language)
        create_new = not entry["variants"]
        if not create_new and expand_variants and len(entry["variants"]) < max(1, max_variants):
            create_new = True

        if create_new:
            variant = _create_variant(
                entry=entry,
                key=key,
                phrase=text,
                output_dir=output_dir,
                voice=voice,
                fmt=fmt,
                synthesizer=synth_func,
                dry_run=dry_run,
                stats=stats,
            )
        else:
            variant = _select_variant(entry)
            stats.variants_reused += 1

        links[fname] = {
            "clip_id": variant["variant_id"],
            "phrase_id": entry.get("phrase_id"),
            "file": variant["file"],
            "voice": variant.get("voice", voice),
            "format": variant.get("format", fmt),
        }
        processed_keys.add(fname)

        variant_path = _ensure_variant_file(
            output_dir=output_dir,
            variant=variant,
            phrase=text,
            voice=voice,
            fmt=fmt,
            synthesizer=synth_func,
            dry_run=dry_run,
            stats=stats,
        )

        if write_copies:
            if not dry_run:
                if dest_path.exists() and not overwrite:
                    pass
                else:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(variant_path, dest_path)
            stats.scenario_copies += 1

    if not dry_run:
        save_manifest(manifest, manifest_path)
        if link_index_path:
            existing = {}
            if link_index_path.exists():
                try:
                    existing = json.loads(link_index_path.read_text())
                except Exception:
                    existing = {}
            existing.update(links)
            _atomic_json_write(existing, link_index_path)

    stats.links_recorded = len(processed_keys)
    return stats

