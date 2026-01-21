#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass

import providers


def _guess_mime(ext: str) -> str:
    ext = (ext or "").lower().lstrip(".")
    return {
        "webm": "audio/webm",
        "ogg": "audio/ogg",
        "mp3": "audio/mp3",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
    }.get(ext, "audio/wav")


@dataclass
class RunResult:
    provider: str
    model: str
    ms: int
    text_len: int
    preview: str


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Benchmark transcription providers via backend/providers.py")
    parser.add_argument("--file", required=True, help="Path to an audio file (wav/webm/ogg/m4a/mp3).")
    parser.add_argument("--language", default="", help="Optional language hint (e.g., Japanese).")
    parser.add_argument(
        "--context",
        default="interaction",
        choices=["interaction", "streaming", "translate", "imitate", "notes"],
        help="Provider preference context (uses TRANSCRIBE_* env vars).",
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs to execute.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs (not counted).")
    args = parser.parse_args(argv)

    path = os.path.abspath(args.file)
    if not os.path.exists(path):
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    ext = os.path.splitext(path)[1].lower().lstrip(".") or "wav"
    mime = _guess_mime(ext)
    with open(path, "rb") as f:
        audio_bytes = f.read()

    ctx_map = {
        "interaction": providers.CONTEXT_INTERACTION,
        "streaming": providers.CONTEXT_STREAMING,
        "translate": providers.CONTEXT_TRANSLATE,
        "imitate": providers.CONTEXT_IMITATE,
        "notes": providers.CONTEXT_NOTES,
    }
    context = ctx_map.get(args.context, providers.CONTEXT_INTERACTION)

    print("Provider benchmark")
    print(f"- file: {path}")
    print(f"- bytes: {len(audio_bytes)}")
    print(f"- ext/mime: {ext} / {mime}")
    print(f"- language_hint: {args.language or '—'}")
    print(f"- context: {context}")
    print("")

    results: list[RunResult] = []

    def run_once() -> RunResult:
        start = time.perf_counter()
        res = providers.transcribe_audio(
            audio_bytes,
            file_ext=ext,
            mime_type=mime,
            instructions="Transcribe this audio recording. Do not translate.",
            language_hint=(args.language or None),
            context=context,
        )
        ms = int((time.perf_counter() - start) * 1000)
        text = (res.text or "").strip()
        preview = text.replace("\n", " ")
        if len(preview) > 140:
            preview = preview[:140].rstrip() + "…"
        return RunResult(
            provider=str(res.provider),
            model=str(res.model),
            ms=ms,
            text_len=len(text),
            preview=preview,
        )

    for idx in range(max(0, int(args.warmup or 0))):
        try:
            r = run_once()
            print(f"warmup {idx + 1}: {r.provider}/{r.model} {r.ms}ms len={r.text_len}")
        except Exception as exc:
            print(f"warmup {idx + 1}: error: {exc}", file=sys.stderr)

    for idx in range(max(1, int(args.runs or 1))):
        r = run_once()
        results.append(r)
        print(f"run {idx + 1}: {r.provider}/{r.model} {r.ms}ms len={r.text_len}")
        print(f"  preview: {r.preview or '—'}")

    ms_values = [r.ms for r in results]
    print("")
    print("Summary")
    if ms_values:
        print(
            f"- ms: mean={int(statistics.mean(ms_values))} "
            f"p50={int(statistics.median(ms_values))} min={min(ms_values)} max={max(ms_values)}"
        )
    by_provider: dict[str, int] = {}
    for r in results:
        by_provider[r.provider] = by_provider.get(r.provider, 0) + 1
    if by_provider:
        print(f"- providers: {', '.join([f'{k}({v})' for k, v in sorted(by_provider.items())])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

