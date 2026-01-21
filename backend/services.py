from __future__ import annotations

import os
import json
import uuid
import io
import asyncio
import wave
import contextlib
from datetime import datetime
import time
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from typing import List, Optional, Tuple
import config
import providers
import note_store
import usage_log as usage
import subprocess
import tempfile
import re
import sys
import importlib.util
from language import contains_japanese

# Load environment variables from .env file
load_dotenv()

# Configure providers and models (use centralized, normalized config)
GOOGLE_MODEL = config.GOOGLE_MODEL
OPENAI_TRANSCRIBE_MODEL = config.OPENAI_TRANSCRIBE_MODEL
OPENAI_TITLE_MODEL = config.OPENAI_TITLE_MODEL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _title_with_openai(transcribed_text: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    llm = ChatOpenAI(model=OPENAI_TITLE_MODEL, api_key=OPENAI_API_KEY, temperature=0.5)
    resp = llm.invoke(
        f"Generate a short, descriptive title for this transcription:\n\n{transcribed_text}"
    )
    return str(getattr(resp, "content", resp)).strip().replace('"', '')

# Load scenario data
scenarios_path = os.path.join(os.path.dirname(__file__), 'scenarios.json')
with open(scenarios_path, 'r') as f:
    scenarios_data = json.load(f)
SCENARIO_VERSIONS_DIR = os.path.join(os.path.dirname(__file__), 'scenario_versions')

def get_scenario_by_id(scenario_id):
    """Finds a scenario in the loaded data by its ID."""
    for scenario in scenarios_data:
        if scenario["id"] == scenario_id:
            return scenario
    return None

def list_scenarios() -> list:
    return scenarios_data

def reload_scenarios(new_list: list) -> None:
    # Persist to file and update in-memory data
    global scenarios_data
    try:
        with open(scenarios_path, 'w') as f:
            json.dump(new_list, f, ensure_ascii=False, indent=2)
        scenarios_data = new_list
    except Exception as e:
        raise e

def ensure_versions_dir():
    os.makedirs(SCENARIO_VERSIONS_DIR, exist_ok=True)

def save_scenarios_version(label: str | None = None) -> str:
    """Save the current scenarios into a timestamped JSON file and return filename."""
    ensure_versions_dir()
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_label = (label or "").strip().replace(" ", "_")
    name = f"scenarios-{ts}{('-' + safe_label) if safe_label else ''}.json"
    path = os.path.join(SCENARIO_VERSIONS_DIR, name)
    with open(path, 'w') as f:
        json.dump(scenarios_data, f, ensure_ascii=False, indent=2)
    return name

def list_scenario_versions() -> list[dict]:
    ensure_versions_dir()
    out = []
    for f in sorted(os.listdir(SCENARIO_VERSIONS_DIR)):
        if f.endswith('.json'):
            out.append({"filename": f})
    return out

def activate_scenario_version(filename: str) -> None:
    ensure_versions_dir()
    path = os.path.join(SCENARIO_VERSIONS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(filename)
    with open(path, 'r') as f:
        data = json.load(f)
    reload_scenarios(data)

# --------- Scenario generation from video/transcript ---------

def _ffmpeg_extract_audio(url: str, out_wav_path: str, sample_rate: int = 16000) -> None:
    """Use ffmpeg to extract mono WAV audio from a video URL or file path.

    Strategy:
    - YouTube: resolve media via yt-dlp and pipe into ffmpeg.
    - Other URLs: try ffmpeg direct; if it fails and yt-dlp is available, fall back to yt-dlp pipe (supports many sites).
    """
    if isinstance(url, str) and _is_youtube_url(url):
        _ffmpeg_extract_audio_from_youtube(url, out_wav_path, sample_rate=sample_rate)
        return
    try:
        max_seconds = int(getattr(config, "VIDEO_MAX_SECONDS", 300) or 0)
    except Exception:
        max_seconds = 300
    cmd = ["ffmpeg", "-y", "-i", url]
    if max_seconds > 0:
        cmd += ["-t", str(max_seconds)]
    cmd += ["-vn", "-ac", "1", "-ar", str(sample_rate), out_wav_path]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return
    except subprocess.CalledProcessError as e:
        url_str = str(url or "")
        can_try_ytdlp = url_str.startswith("http://") or url_str.startswith("https://")
        if can_try_ytdlp and importlib.util.find_spec("yt_dlp") is not None:
            _ffmpeg_extract_audio_from_youtube(url_str, out_wav_path, sample_rate=sample_rate)
            return
        snippet = ((e.stderr or b"")[:400]).decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg_failed: {snippet or 'unknown_error'}") from e


def _is_youtube_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    u = url.strip().lower()
    return u.startswith("https://www.youtube.com/") or u.startswith("https://youtube.com/") or u.startswith("https://youtu.be/")


def _ffmpeg_extract_audio_from_youtube(url: str, out_wav_path: str, sample_rate: int = 16000) -> None:
    """Extract audio using yt-dlp piped into ffmpeg.

    Used for YouTube and as a fallback for other sites where ffmpeg cannot ingest the URL directly.
    """
    if importlib.util.find_spec("yt_dlp") is None:
        raise RuntimeError("yt_dlp_not_installed (install with: pip install yt-dlp)")

    # Cap downloads to reduce abuse/cost. yt-dlp expects human-friendly sizes.
    try:
        max_bytes = int(getattr(config, "YTDLP_MAX_FILESIZE_BYTES", 52428800) or 0)
    except Exception:
        max_bytes = 52428800
    max_size_arg = None
    if max_bytes > 0:
        max_mib = max(1, int(round(max_bytes / (1024 * 1024))))
        max_size_arg = f"{max_mib}M"

    ytdlp_cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--no-playlist",
        "--no-progress",
        *(["--max-filesize", max_size_arg] if max_size_arg else []),
        "-f",
        "bestaudio/best",
        "-o",
        "-",
        url,
    ]
    try:
        max_seconds = int(getattr(config, "VIDEO_MAX_SECONDS", 300) or 0)
    except Exception:
        max_seconds = 300
    ffmpeg_cmd = ["ffmpeg", "-y", "-i", "pipe:0"]
    if max_seconds > 0:
        ffmpeg_cmd += ["-t", str(max_seconds)]
    ffmpeg_cmd += ["-vn", "-ac", "1", "-ar", str(sample_rate), out_wav_path]

    proc = subprocess.Popen(
        ytdlp_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    try:
        subprocess.run(
            ffmpeg_cmd,
            stdin=proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        _, ytdlp_err = proc.communicate(timeout=60)
        if proc.returncode not in (0, None):
            snippet = (ytdlp_err or b"")[:400].decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"yt_dlp_failed: {snippet or 'unknown_error'}")


def _transcribe_audio_bytes(audio_bytes: bytes, lang_hint: str | None = None) -> str:
    """Transcribe bytes via Gemini, with OpenAI fallback, honoring language hints when possible."""
    try:
        instruction = "Transcribe this audio recording in the language you hear. Do not translate."
        if lang_hint:
            hint = lang_hint.strip()
            lower = hint.lower()
            if "japanese" in lower or lower == "ja":
                instruction = (
                    "Transcribe this audio recording. "
                    "If the speaker uses Japanese, write it in Japanese script (hiragana/katakana/kanji) without romanizing. "
                    "If another language is spoken, transcribe using that language's typical writing system. "
                    "Do not translate."
                )
            else:
                instruction = (
                    "Transcribe this audio recording. "
                    f"The expected language is {hint}, but always keep the language that is actually spoken and its writing system. "
                    "Do not translate."
                )
        result = providers.transcribe_audio(
            audio_bytes,
            file_ext="wav",
            mime_type="audio/wav",
            instructions=instruction,
            language_hint=lang_hint,
            context=providers.CONTEXT_NOTES,
        )
        try:
            if result.provider == "gemini":
                key_index = int(result.meta.get("key_index", 0) or 0)
                usage.log_usage(
                    event="video_transcribe",
                    provider="gemini",
                    model=result.model,
                    key_label=usage.key_label_from_index(key_index, providers.GOOGLE_KEYS),
                    status="success",
                )
            elif result.provider == "openai":
                usage.log_usage(
                    event="video_transcribe",
                    provider="openai",
                    model=result.model,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            else:
                usage.log_usage(
                    event="video_transcribe",
                    provider=result.provider,
                    model=result.model,
                    key_label="unknown",
                    status="success",
                )
        except Exception:
            pass
        return result.text
    except Exception:
        return ""


def generate_scenarios_from_transcript(
    transcript: str,
    target_language: str = "Japanese",
    max_scenes: int = 5,
    usage_event: str = "scenario_compile",
) -> list:
    """Use an LLM to turn a transcript into a short branching scenario list."""
    prompt = (
        "You are a language learning scenario designer. Given this dialogue transcript, "
        "produce a compact branching scenario for beginners in JSON array format.\n\n"
        f"Target language: {target_language}.\n"
        f"Max scenes: {max_scenes}. Keep it simple and kid-friendly.\n\n"
        "Output JSON only (no markdown), where each item is:\n"
        "{\n  \"id\": number,\n  \"language\": string,\n  \"description\": string,\n  \"character_dialogue_jp\": string,\n  \"character_dialogue_en\": string,\n  \"options\": [ {\n    \"text\": string, \n    \"next_scenario\": number,\n    \"keywords\": [string...],\n    \"examples\": [ { \"native\": string, \"target\": string, \"pronunciation\": string } ]\n  } ... ]\n}\n\n"
        "Guidelines:\n- IDs must be sequential starting at 1.\n- Use Japanese in character_dialogue_jp when target_language is Japanese; English in character_dialogue_en.\n- Provide 2–3 options in early scenes; terminal scenes can have empty options.\n- Include 1 example per option in the target language.\n- Keywords should include short target-language triggers like はい, いいえ, お願いします.\n\nTranscript:\n" + transcript
    )
    provider_used = None
    model_used = None
    key_index = None
    try:
        resp, key_index = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": prompt}])])
        provider_used = "gemini"
        model_used = config.GOOGLE_MODEL
        text = str(getattr(resp, "content", resp))
    except Exception:
        provider_used = "openai"
        model_used = config.OPENAI_NARRATIVE_MODEL
        text = providers.openai_chat([HumanMessage(content=prompt)])
    try:
        usage.log_usage(
            event=str(usage_event or "scenario_compile"),
            provider=str(provider_used or "unknown"),
            model=str(model_used or "unknown"),
            key_label=(providers.key_label_from_index(key_index or 0) if provider_used == "gemini" else usage.OPENAI_LABEL),
            status="success",
        )
    except Exception:
        pass
    # Attempt to extract JSON array
    try:
        import json as _json
        # Find first [ ... ] block
        m = re.search(r"\[.*\]", text, flags=re.S)
        arr = m.group(0) if m else text
        data = _json.loads(arr)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []



def generate_scenarios_from_video(url: str, target_language: str = "Japanese", max_scenes: int = 5) -> list:
    """Pipeline: ffmpeg audio extract -> transcribe -> LLM structure -> scenarios list."""
    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "audio.wav")
        _ffmpeg_extract_audio(url, wav_path)
        with open(wav_path, "rb") as f:
            audio_bytes = f.read()
    transcript = _transcribe_audio_bytes(audio_bytes, lang_hint=target_language)
    return generate_scenarios_from_transcript(
        transcript,
        target_language=target_language,
        max_scenes=max_scenes,
        usage_event="video_compile",
    )

def _clamp_float(value: object, default: float = 0.0, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        v = float(value)
    except Exception:
        v = float(default)
    if v < lo:
        return float(lo)
    if v > hi:
        return float(hi)
    return float(v)


def process_interaction(
    audio_file,
    current_scenario_id_str,
    lang: Optional[str] = None,
    judge: Optional[float] = None,
):
    """
    Processes the user's audio interaction to determine the next scenario.
    """
    temp_filename = f"temp_{uuid.uuid4()}.webm"
    temp_path = os.path.join(VOICE_NOTES_DIR, temp_filename)

    try:
        current_scenario_id = int(current_scenario_id_str)
        
        # 1. Save temporary audio file to get a stable file path
        audio_bytes = audio_file.read()
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        # 2. Transcribe Audio to Text with provider rotation & fallback
        lang_hint_value = (lang or "").strip().lower()
        if "japanese" in lang_hint_value or lang_hint_value == "ja":
            instruction = (
                "Transcribe this audio recording. "
                "If the speech is Japanese, write it in Japanese script (hiragana/katakana/kanji) without romanizing. "
                "If it is another language, transcribe using that language's normal writing system. "
                "Do not translate."
            )
        elif lang_hint_value:
            instruction = (
                "Transcribe this audio recording. "
                f"The expected language is {lang}, but always use the language that is actually spoken and its native script. "
                "Do not translate."
            )
        else:
            instruction = "Transcribe this audio recording in the language you hear. Do not translate."

        transcribe_started = time.perf_counter()
        result = providers.transcribe_audio(
            audio_bytes,
            file_ext="webm",
            mime_type="audio/webm",
            instructions=instruction,
            language_hint=lang_hint_value or None,
            context=providers.CONTEXT_INTERACTION,
        )
        transcribed_text = result.text
        duration_ms = int((time.perf_counter() - transcribe_started) * 1000)
        try:
            print(f"[interaction/{result.provider}] Heard: {(transcribed_text or '')[:200]} (transcription {duration_ms}ms)")
        except Exception:
            pass
        if result.provider == "gemini":
            key_index = int(result.meta.get("key_index", 0) or 0)
            usage.log_usage(
                event="interaction_transcribe",
                provider="gemini",
                model=result.model,
                key_label=usage.key_label_from_index(key_index, providers.GOOGLE_KEYS),
                status="success",
            )
        elif result.provider == "openai":
            usage.log_usage(
                event="interaction_transcribe",
                provider="openai",
                model=result.model,
                key_label=usage.OPENAI_LABEL,
                status="success",
            )
        else:
            usage.log_usage(
                event="interaction_transcribe",
                provider=result.provider,
                model=result.model,
                key_label="unknown",
                status="success",
            )

        heard_raw = transcribed_text or ""
        transcribed_text = (transcribed_text or "").lower()
        match_confidence = 0.0
        match_type = "none"
        best_match_score = 0.0
        best_match_threshold = None

        # 3. Recognize Intent (Simplified MVP Logic)
        current_scenario = get_scenario_by_id(current_scenario_id)
        if not current_scenario:
            return {"error": "Scenario not found", "heard": heard_raw, "confidence": 0.0, "match_type": "missing_scenario"}

        # If no lang provided, infer from scenario or presence of JP dialogue
        if not lang:
            lang = current_scenario.get("language") or ("Japanese" if current_scenario.get("character_dialogue_jp") else "English")

        def _coerce_int(value, default):
            try:
                return max(0, int(value))
            except Exception:
                return default

        reward_points = _coerce_int(
            current_scenario.get("reward_points")
            or current_scenario.get("points")
            or current_scenario.get("success_points"),
            config.DEFAULT_SUCCESS_POINTS,
        )
        penalties_cfg = current_scenario.get("penalties") or {}
        incorrect_cfg = penalties_cfg.get("incorrect_answer") or {}
        failure_lives = _coerce_int(
            incorrect_cfg.get("lives")
            or incorrect_cfg.get("life")
            or incorrect_cfg.get("health")
            or incorrect_cfg.get("count"),
            config.DEFAULT_FAILURE_LIFE_COST,
        )
        language_cfg = penalties_cfg.get("language_mismatch") or {}
        language_failure_lives = _coerce_int(
            language_cfg.get("lives")
            or language_cfg.get("life")
            or language_cfg.get("health")
            or language_cfg.get("count"),
            failure_lives or config.DEFAULT_FAILURE_LIFE_COST,
        )

        # Judge focus slider: 0.0 = learning-first (default, backwards compatible)
        #                    1.0 = story-first (more permissive; fewer language gates)
        judge_story_weight = _clamp_float(judge, default=0.0)

        success = False

        next_scenario_id = None

        # Heuristic quick pass for clear English yes/no
        if transcribed_text:
            if any(k in transcribed_text for k in ["yes", "yeah", "yep", "i am", "sure", "ok", "okay"]):
                for option in current_scenario.get("options", []):
                    if "yes" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                            match_confidence = 0.9
                            match_type = "yes_no_keyword"
                        break
            if not next_scenario_id and any(k in transcribed_text for k in ["no", "not", "nope", "nah"]):
                for option in current_scenario.get("options", []):
                    if "no" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                            match_confidence = 0.9
                            match_type = "yes_no_keyword"
                        break

        # Japanese quick pass: はい/うん → yes, いいえ/いや → no
        if not next_scenario_id and heard_raw:
            raw = (heard_raw or "").strip()
            if any(tok in raw for tok in ["はい", "ええ", "うん"]):
                for option in current_scenario.get("options", []):
                    if "yes" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                            match_confidence = 0.9
                            match_type = "yes_no_keyword"
                        break
            if not next_scenario_id and any(tok in raw for tok in ["いいえ", "いや", "いえ", "ノー"]):
                for option in current_scenario.get("options", []):
                    if "no" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                            match_confidence = 0.9
                            match_type = "yes_no_keyword"
                        break

        # Japanese polite acceptance (e.g., お願いします/ください) → often implies affirmative
        if not next_scenario_id and heard_raw:
            raw = (heard_raw or "").strip()
            if any(tok in raw for tok in ["お願いします", "おねがいします", "下さい", "ください", "欲しい", "ほしい", "お願いします。"]):
                for option in current_scenario.get("options", []):
                    if "yes" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                            match_confidence = 0.85
                            match_type = "polite_affirmative"
                        break

        # Scenario-specific keyword/example matching
        if not next_scenario_id and current_scenario.get("options"):
            try:
                best_score = 0.0
                best_idx = -1
                import re
                raw = heard_raw or ""
                threshold = 0.6 - (0.12 * judge_story_weight)  # story-first is a bit more permissive
                for idx, opt in enumerate(current_scenario["options"]):
                    candidates: List[str] = []
                    # free-form keywords list
                    for kw in (opt.get("keywords") or []):
                        if isinstance(kw, str) and kw.strip():
                            candidates.append(kw.strip())
                    # examples may be strings or {native,target}
                    for ex in (opt.get("examples") or []):
                        if isinstance(ex, str) and ex.strip():
                            candidates.append(ex.strip())
                        elif isinstance(ex, dict):
                            for k in ("target", "native", "pronunciation"):
                                v = (ex.get(k) or "").strip()
                                if v:
                                    candidates.append(v)
                    # Evaluate candidates
                    for cand in candidates:
                        # direct substring match boosts score
                        score = 0.0
                        if cand and cand in raw:
                            score = max(score, 0.95)
                        # similarity in romanized/latin domain using lowercased transcription
                        score = max(score, _similarity(transcribed_text or "", cand))
                        if score > best_score:
                            best_score = score
                            best_idx = idx
                best_match_score = float(best_score)
                best_match_threshold = float(threshold)
                if best_idx >= 0 and best_score >= threshold:
                    next_scenario = current_scenario["options"][best_idx]
                    next_scenario_id = next_scenario.get("next_scenario")
                    if next_scenario_id is not None:
                        success = True
                        match_confidence = float(best_score)
                        match_type = "examples_similarity"
            except Exception:
                pass

        # If target language is Japanese and user spoke non‑Japanese, prompt them to say it in Japanese
        if judge_story_weight < 0.66 and (lang or "").lower() in ("japanese", "ja") and heard_raw and not contains_japanese(heard_raw):
            out = {
                "heard": heard_raw,
                "npcDoesNotUnderstand": True,
                "message": "Please say it in Japanese.",
                "scoreDelta": 0,
                "livesDelta": -language_failure_lives,
                "confidence": 0.0,
                "match_type": "wrong_language",
            }
            if next_scenario_id:
                out["repeatNextScenario"] = next_scenario_id
            return out

        # Semantic choice via LLM among available options
        if not next_scenario_id and current_scenario.get("options"):
            try:
                opts = current_scenario["options"]
                lines = []
                for idx, opt in enumerate(opts, start=1):
                    line = f"{idx}. {opt.get('text') or ''}"
                    # include examples if present to bias selection
                    exs = opt.get('examples') or []
                    if exs:
                        # Flatten to text pieces
                        ex_texts: List[str] = []
                        for e in exs:
                            if isinstance(e, str) and e.strip():
                                ex_texts.append(e.strip())
                            elif isinstance(e, dict):
                                t = (e.get('target') or e.get('native') or '').strip()
                                if t:
                                    ex_texts.append(t)
                        if ex_texts:
                            line += " (e.g., " + "; ".join(ex_texts[:3]) + ")"
                    lines.append(line)
                options_block = "\n".join(lines)
                focus_line = (
                    "Judging focus: STORY-FIRST (prioritize narrative progression even if the learner uses the wrong language)."
                    if judge_story_weight >= 0.66
                    else "Judging focus: LEARNING-FIRST (prefer target-language intent; reject mismatched-language replies when unclear)."
                )
                prompt = (
                    "You are choosing the best matching option for a user's spoken reply.\n"
                    "The user reply may be in any language (e.g., Japanese).\n"
                    f"{focus_line}\n"
                    "Given the scenario context and these options, reply with ONLY the number of the single best option (1-based).\n"
                    "If none fit, reply 0.\n\n"
                    f"Context (may be empty): {current_scenario.get('description') or ''}\n"
                    f"Character line JP: {current_scenario.get('character_dialogue_jp') or ''}\n"
                    f"Character line EN: {current_scenario.get('character_dialogue_en') or ''}\n\n"
                    f"Options:\n{options_block}\n\n"
                    f"User said: {heard_raw}\n\n"
                    "Answer:"
                )
                resp, key_index = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": prompt}])])
                out = str(getattr(resp, "content", resp)).strip()
                # Extract first integer on the line
                import re
                m = re.search(r"\b(\d+)\b", out)
                choice = int(m.group(1)) if m else 0
                if 1 <= choice <= len(opts):
                    next_scenario_id = opts[choice - 1].get("next_scenario")
                    if next_scenario_id is not None:
                        success = True
                        match_confidence = 0.62
                        match_type = "llm_choice"
            except Exception:
                try:
                    # Fallback to OpenAI if configured
                    from langchain_core.messages import HumanMessage as HM
                    out = providers.openai_chat([HM(content=prompt)])
                    import re
                    m = re.search(r"\b(\d+)\b", str(out))
                    choice = int(m.group(1)) if m else 0
                    if 1 <= choice <= len(opts):
                        next_scenario_id = opts[choice - 1].get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                            match_confidence = 0.62
                            match_type = "llm_choice"
                except Exception:
                    pass

        if not next_scenario_id:
            # If target is Japanese and options include a clear affirmative example, guide the learner
            if (lang or "").lower() in ("japanese", "ja") and current_scenario.get("options"):
                try:
                    yes_opt = None
                    for o in current_scenario["options"]:
                        if "yes" in (o.get("text") or "").lower():
                            yes_opt = o
                            break
                    if yes_opt:
                        exs = yes_opt.get("examples") or []
                        expected = None
                        if exs:
                            if isinstance(exs[0], dict):
                                expected = (exs[0].get("target") or "").strip() or None
                            elif isinstance(exs[0], str):
                                expected = exs[0]
                            if expected:
                                pron = providers.romanize(expected, "Japanese") or ""
                                return {
                                    "heard": heard_raw,
                                    "npcDoesNotUnderstand": True,
                                    "message": "Please answer in Japanese.",
                                    "repeatExpected": expected,
                                    "pronunciation": pron,
                                    "repeatNextScenario": yes_opt.get("next_scenario"),
                                    "scoreDelta": 0,
                                    "livesDelta": -language_failure_lives,
                                    "confidence": 0.0,
                                    "match_type": "wrong_language",
                                }
                except Exception:
                    pass
            # Return heard text so UI can display it; signal that it didn't match
            return {
                "error": "Could not determine intent from speech.",
                "heard": heard_raw,
                "scoreDelta": 0,
                "livesDelta": -failure_lives,
                "confidence": float(best_match_score or 0.0),
                "match_type": match_type if match_type != "none" else "no_match",
                "best_match_score": float(best_match_score or 0.0),
                "best_match_threshold": float(best_match_threshold) if best_match_threshold is not None else None,
            }

        # 4. Determine Next Scenario
        success = True
        next_scenario = get_scenario_by_id(next_scenario_id)
        if not next_scenario:
            return {
                "error": "Next scenario not found",
                "heard": heard_raw,
                "scoreDelta": 0,
                "livesDelta": 0,
                "confidence": float(match_confidence or 0.0),
                "match_type": match_type,
            }
        
        return {
            "nextScenario": next_scenario,
            "heard": heard_raw,
            "scoreDelta": reward_points if success else 0,
            "livesDelta": 0,
            "confidence": float(match_confidence or 0.0),
            "match_type": match_type,
            "best_match_score": float(best_match_score or 0.0),
            "best_match_threshold": float(best_match_threshold) if best_match_threshold is not None else None,
        }

    except Exception as e:
        return {"error": str(e), "scoreDelta": 0, "livesDelta": 0}
    finally:
        # 5. Clean up the temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'transcriptions'))

async def transcribe_and_save(wav_path):
    """Transcribes and titles an audio file, saving the results."""
    base_filename = os.path.basename(wav_path)
    ext = os.path.splitext(base_filename)[1].lower().lstrip('.') or 'wav'
    print(f"Starting transcription process for {base_filename}...")
    try:
        # Read audio bytes
        with open(wav_path, "rb") as af:
            audio_bytes = af.read()

        # Transcribe with provider rotation & fallback
        print(f"Transcribing {base_filename} from local file bytes...")
        mime = {
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "mp3": "audio/mp3",
            "m4a": "audio/mp4",
        }.get(ext, "audio/wav")
        result = await asyncio.to_thread(
            providers.transcribe_audio,
            audio_bytes,
            file_ext=ext,
            mime_type=mime,
            instructions="Transcribe this audio recording.",
            context=providers.CONTEXT_NOTES,
        )
        transcribed_text = result.text
        print(f"Successfully transcribed {base_filename} via {result.provider}.")
        if result.provider == "gemini":
            key_index = int(result.meta.get("key_index", 0) or 0)
            usage.log_usage(
                event="transcribe",
                provider="gemini",
                model=result.model,
                key_label=usage.key_label_from_index(key_index, providers.GOOGLE_KEYS),
                status="success",
            )
        elif result.provider == "openai":
            usage.log_usage(
                event="transcribe",
                provider="openai",
                model=result.model,
                key_label=usage.OPENAI_LABEL,
                status="success",
            )
        else:
            usage.log_usage(
                event="transcribe",
                provider=result.provider,
                model=result.model,
                key_label="unknown",
                status="success",
            )

        # Generate title
        print(f"Generating title for {base_filename}...")
        try:
            title_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Return exactly one short title (5–8 words) for the transcription below. "
                            "Use the same language as the transcription. Do not include quotes, bullets, markdown, or any extra text. "
                            "Output only the title on a single line.\n\n" + transcribed_text
                        ),
                    },
                ]
            )
            # Try Gemini briefly, else fallback to OpenAI title
            gemini_ok = False
            last_key_index = None
            for attempt in range(2):
                try:
                    title_response, key_index = await asyncio.to_thread(
                        providers.invoke_google, [title_message]
                    )
                    last_key_index = key_index
                    title_text = providers.normalize_title_output(title_response.content)
                    gemini_ok = True
                    break
                except Exception as ge:
                    print(f"Gemini title attempt {attempt+1} failed for {base_filename}: {ge}")
                    if providers.is_rate_limit_error(ge):
                        break
                    continue
            if gemini_ok:
                usage.log_usage(
                    event="title",
                    provider="gemini",
                    model=config.GOOGLE_MODEL,
                    key_label=providers.key_label_from_index(last_key_index or 0),
                    status="success",
                )
            else:
                raise RuntimeError("Gemini unavailable for title")
        except Exception as e:
            try:
                print(f"Falling back to OpenAI title for {base_filename}: {e}")
                title_text = providers.title_with_openai(transcribed_text)
                usage.log_usage(
                    event="title",
                    provider="openai",
                    model=config.OPENAI_TITLE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            except Exception:
                title_text = "Title generation failed."
        print(f"Successfully generated title for {base_filename}.")

        payload = note_store.build_note_payload(base_filename, title_text, transcribed_text)
        note_store.save_note_json(os.path.splitext(base_filename)[0], payload)
        print(f"Successfully saved transcription and title for {base_filename}.")

    except Exception as e:
        print(f"Error during transcription/titling for {wav_path}: {e}")
        if os.path.exists(wav_path):
            payload = note_store.build_note_payload(base_filename, "Title generation failed.", "Transcription failed.")
            note_store.save_note_json(os.path.splitext(base_filename)[0], payload)

def _audio_length_seconds(path: str) -> float | None:
    try:
        with contextlib.closing(wave.open(path, 'rb')) as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return round(frames / float(rate), 2) if rate else None
    except Exception:
        return None

STOPWORDS = set(
    "the a an and or but for with without on in at to from of by this that those these is are was were be been being i you he she it we they them me my your our their as not just into over under again more most some any few many much very can could should would".split()
)

def _infer_topics(text: str | None, title: str | None) -> list[str]:
    source = (title or "").strip() or (text or "").strip()
    if not source:
        return []
    # naive keyword extraction: keep alphas, lower, remove stopwords, top 3
    import re

    words = re.findall(r"[A-Za-z]{3,}", source.lower())
    words = [w for w in words if w not in STOPWORDS]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    topics = sorted(freq, key=lambda k: (-freq[k], k))[:3]
    return topics

def get_notes():
    """Lists all notes with their details, including date, topics, and length."""
    notes = []
    if not os.path.exists(VOICE_NOTES_DIR):
        return notes

    # Ensure transcripts dir exists (in case)
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    wav_files = [f for f in os.listdir(VOICE_NOTES_DIR) if f.lower().endswith(AUDIO_EXTS)]
    wav_files.sort(key=lambda f: os.path.getmtime(os.path.join(VOICE_NOTES_DIR, f)), reverse=True)
    for filename in wav_files:
        base_filename = filename[:-4]
        audio_path = os.path.join(VOICE_NOTES_DIR, filename)
        data, transcription, title = note_store.load_note_json(base_filename)
        if data is None:
            # JSON not yet created (transcription pending). Return lightweight
            # metadata without creating placeholder JSON to avoid overwriting
            # the final payload when it arrives.
            mtime = os.path.getmtime(audio_path)
            date_str = __import__('datetime').datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            length_sec = note_store.audio_length_seconds(audio_path)
            notes.append({
                "filename": filename,
                "transcription": transcription,  # likely None
                "title": title,  # likely None (frontend will fallback to filename)
                "date": date_str,
                "length_seconds": length_sec,
                "topics": [],
                "tags": [],
            })
            continue
        else:
            data = note_store.ensure_metadata_in_json(base_filename, data)

        notes.append({
            "filename": filename,
            "transcription": transcription,
            "title": title,
            "date": data.get("date"),
            "length_seconds": data.get("length_seconds"),
            "topics": data.get("topics", []),
            "tags": data.get("tags", []),
        })
    return notes


# --------- Say-the-line imitation checking ---------

def _normalize_text_for_match(s: str) -> str:
    import re, string
    s = (s or "").lower().strip()
    table = str.maketrans({c: " " for c in string.punctuation})
    s = s.translate(table)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    na, nb = _normalize_text_for_match(a), _normalize_text_for_match(b)
    if not na or not nb:
        return 0.0
    return float(SequenceMatcher(a=na, b=nb).ratio())

def imitate_say(audio_bytes: bytes, mime: str, expected_text: str, target_lang: str | None = None) -> dict:
    """Transcribe the audio and compare to expected_text. Returns {success, score, heard, makesSense}."""
    # Transcribe via Gemini first, fallback OpenAI
    result = providers.transcribe_audio(
        audio_bytes,
        file_ext=("webm" if (mime and "webm" in mime) else "wav"),
        mime_type=mime or "audio/webm",
        instructions="Transcribe this audio recording.",
        language_hint=target_lang,
        context=providers.CONTEXT_IMITATE,
    )
    heard = result.text
    if result.provider == "gemini":
        key_index = int(result.meta.get("key_index", 0) or 0)
        usage.log_usage(
            event="imitate_transcribe",
            provider="gemini",
            model=result.model,
            key_label=providers.key_label_from_index(key_index, providers.GOOGLE_KEYS),
            status="success",
        )
    elif result.provider == "openai":
        usage.log_usage(
            event="imitate_transcribe",
            provider="openai",
            model=result.model,
            key_label=usage.OPENAI_LABEL,
            status="success",
        )
    else:
        usage.log_usage(
            event="imitate_transcribe",
            provider=result.provider,
            model=result.model,
            key_label="unknown",
            status="success",
        )
    score = _similarity(heard or "", expected_text or "")
    success = score >= 0.72  # initial threshold; tune later
    makes_sense = False
    try:
        makes_sense = providers.makes_sense(heard or "", language=(target_lang or ""))
    except Exception:
        makes_sense = False
    try:
        print(f"[imitate] Expect='{(expected_text or '')[:60]}' Heard='{(heard or '')[:60]}' score={score:.3f} makes_sense={makes_sense}")
    except Exception:
        pass
    return {
        "success": success,
        "score": round(score, 3),
        "confidence": round(score, 3),
        "threshold": 0.72,
        "heard": heard,
        "makesSense": makes_sense,
    }


# --------- Scenario Option Suggestions ---------

def _scenario_context_text(s: dict) -> str:
    parts = []
    # Character dialogue shown to the learner
    jp = (s or {}).get("character_dialogue_jp") or ""
    en = (s or {}).get("character_dialogue_en") or ""
    desc = (s or {}).get("description") or ""
    if jp:
        parts.append(f"Character (JP): {jp}")
    if en:
        parts.append(f"Character (EN): {en}")
    if desc:
        parts.append(f"Prompt: {desc}")
    return "\n".join(parts)


def generate_option_suggestions(
    scenario_id: int,
    n_per_option: int = 3,
    target_language: str | None = None,
    native_language: str | None = None,
    stage: str = "examples",
) -> dict:
    """Generate example utterances for each option in the given scenario.

    Returns JSON:
    {
      "question": "What do you say to the kind man?",
      "options": [
         {"option_text": "Yes", "examples": ["…", "…"], "next_scenario": 2},
         {"option_text": "No",  "examples": ["…", "…"], "next_scenario": 3}
      ]
    }
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        return {"question": "", "options": []}

    opts = scenario.get("options") or []
    # Build a constrained prompt so LLM returns suggestions that align with options
    context_txt = _scenario_context_text(scenario)
    n = max(1, int(n_per_option or 3))
    question = "What do you say to the kind man?"
    # Prefer a friendlier auto-question if present in scenario
    if scenario.get("question"):
        question = str(scenario["question"]).strip()
    elif scenario.get("description"):
        # Derive a simple question from description
        question = f"What do you say?"

    option_lines = "\n".join([f"- {o.get('text','')}" for o in opts])
    # System: teaching mode and language focus
    sys = (
        "You help a child learn speaking through example phrases."
        " Return short, simple, positive phrases a child might say."
    )
    # Language directions
    if native_language and target_language:
        sys += f" Provide pairs: translation in {native_language} and phrase in {target_language}."
    elif target_language:
        sys += f" Always respond in {target_language}."
    else:
        sys += " Use the same language and register as the scene suggests."

    if (stage or "examples").lower() == "hints":
        sys += " Provide hints or stems instead of full sentences when possible."
    user = (
        f"Scene:\n{context_txt}\n\n"
        f"Learner is prompted: '{question}'.\n"
        f"Available option meanings (do NOT change or invent options):\n{option_lines}\n\n"
        f"Task: For each option (in order), generate {n} example phrases the learner could say that match the option's meaning."
        " Keep each phrase under 12 words. Avoid quotes, bullets, or numbering."
        + (
            " Respond ONLY as compact JSON like {\"options\": [[{\"native\": \"...\", \"target\": \"...\"}, ...], ...]} "
            if native_language or target_language
            else " Respond ONLY as compact JSON: {\"options\":[[phrases for option1],[phrases for option2], ...]}."
        )
    )

    suggestions_any: list | None = None
    suggestions: list[list[dict]] = []
    try:
        # Try Gemini first
        from langchain_core.messages import HumanMessage
        resp, key_index = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": sys + "\n\n" + user}])])
        raw = str(getattr(resp, "content", resp))
        try:
            import json as _json
            data = _json.loads(raw)
            suggestions_any = data.get("options") or []
        except Exception:
            # Try to coerce simple line-based output if model failed JSON
            lines = [l.strip("- *\t ") for l in raw.splitlines() if l.strip()]
            if lines:
                per = max(1, len(lines) // max(1, len(opts)))
                suggestions_any = [lines[i*per:(i+1)*per] for i in range(len(opts))]
        try:
            usage.log_usage(
                event="options",
                provider="gemini",
                model=config.GOOGLE_MODEL,
                key_label=providers.key_label_from_index(key_index or 0),
                status="success",
            )
        except Exception:
            pass
    except Exception:
        # Fallback to OpenAI
        from langchain_core.messages import HumanMessage
        raw = providers.openai_chat([HumanMessage(content=sys + "\n\n" + user)])
        try:
            import json as _json
            data = _json.loads(raw)
            suggestions_any = data.get("options") or []
        except Exception:
            lines = [l.strip("- *\t ") for l in raw.splitlines() if l.strip()]
            if lines:
                per = max(1, len(lines) // max(1, len(opts)))
                suggestions_any = [lines[i*per:(i+1)*per] for i in range(len(opts))]
        try:
            usage.log_usage(
                event="options",
                provider="openai",
                model=config.OPENAI_NARRATIVE_MODEL,
                key_label=usage.OPENAI_LABEL,
                status="success",
            )
        except Exception:
            pass

    # Normalize and pair with options
    # Coerce suggestions into [[{native, target}, ...], ...] form
    def _coerce_pair_list(value) -> list[list[dict]]:
        out: list[list[dict]] = []
        if not isinstance(value, list):
            return out
        for group in value:
            if isinstance(group, list):
                items = []
                for item in group:
                    if isinstance(item, dict) and ("native" in item or "target" in item):
                        native = str(item.get("native") or "").strip()
                        target = str(item.get("target") or "").strip()
                    else:
                        # If plain string, we treat it as target; native left empty
                        native = ""
                        target = str(item).strip()
                    if native or target:
                        items.append({"native": native, "target": target})
                out.append(items)
            else:
                # group is a string; wrap
                out.append([{ "native": "", "target": str(group).strip() }])
        return out

    suggestions = _coerce_pair_list(suggestions_any or [])

    out = {"question": question, "options": []}
    for i, o in enumerate(opts):
        group = suggestions[i] if i < len(suggestions) and isinstance(suggestions[i], list) else []
        # dedupe by target string
        seen = set()
        items = []
        for idx, pair in enumerate(group):
            native_txt = (pair.get("native") or "").strip().strip('"').strip("'")
            target_txt = (pair.get("target") or "").strip().strip('"').strip("'")
            key = target_txt.lower()
            # If one side is missing but languages are provided, try to translate
            if (not target_txt) and native_language and target_language and native_txt:
                try:
                    target_txt = providers.translate_text(native_txt, to_language=target_language, from_language=native_language)
                except Exception:
                    target_txt = native_txt  # fallback: mirror text
                key = target_txt.lower()
            if (not native_txt) and native_language and target_language and target_txt:
                try:
                    native_txt = providers.translate_text(target_txt, to_language=native_language, from_language=target_language)
                except Exception:
                    native_txt = target_txt
            if not target_txt or key in seen:
                continue
            seen.add(key)
            audio_rel = None
            try:
                os.makedirs(config.EXAMPLES_AUDIO_DIR, exist_ok=True)
                fname = f"scenario-{scenario_id}-opt{i}-ex{len(items)}.mp3"
                fpath = os.path.join(config.EXAMPLES_AUDIO_DIR, fname)
                if not os.path.exists(fpath):
                    audio_bytes = providers.tts_with_openai(target_txt, voice="alloy", fmt="mp3")
                    with open(fpath, "wb") as wf:
                        wf.write(audio_bytes)
                audio_rel = f"/examples/{fname}"
            except Exception:
                audio_rel = None
            items.append({"native": native_txt, "target": target_txt, "audio": audio_rel})
            if len(items) >= n:
                break

        out["options"].append({
            "option_text": o.get("text", ""),
            "examples": items,
            "next_scenario": o.get("next_scenario"),
        })
    return out
