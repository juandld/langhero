from __future__ import annotations

import os
import json
import uuid
import io
import asyncio
import wave
import contextlib
from datetime import datetime
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders.parsers.audio import OpenAIWhisperParser
from base64 import b64encode
from typing import List, Optional, Tuple
import config
import providers
import note_store
import usage_log as usage
import subprocess
import tempfile
import re

DEFAULT_SUCCESS_POINTS = 10
DEFAULT_FAILURE_LIFE_COST = 1

# Load environment variables from .env file
load_dotenv()

# Configure providers and models (use centralized, normalized config)
GOOGLE_MODEL = config.GOOGLE_MODEL
OPENAI_TRANSCRIBE_MODEL = config.OPENAI_TRANSCRIBE_MODEL
OPENAI_TITLE_MODEL = config.OPENAI_TITLE_MODEL

def _collect_google_api_keys() -> List[str]:
    keys = []
    for name in [
        "GOOGLE_API_KEY",
        "GOOGLE_API_KEY_1",
        "GOOGLE_API_KEY_2",
        "GOOGLE_API_KEY_3",
    ]:
        val = os.getenv(name)
        if val and val not in keys:
            keys.append(val)
    return keys

GOOGLE_KEYS = _collect_google_api_keys()
GOOGLE_LLMS: List[ChatGoogleGenerativeAI] = [
    ChatGoogleGenerativeAI(model=GOOGLE_MODEL, api_key=k) for k in GOOGLE_KEYS
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def _is_rate_limit_error(e: Exception) -> bool:
    s = str(e).lower()
    return (
        "429" in s
        or "rate limit" in s
        or "quota" in s
        or "exceeded your current quota" in s
    )

def _should_google_fallback(e: Exception) -> bool:
    s = str(e).lower()
    return _is_rate_limit_error(e) or (
        "no google gemini api keys configured" in s
        or "unauthorized" in s
        or "permission" in s
        or "invalid api key" in s
        or "not found" in s
        or "publisher model" in s
    )

async def _ainvoke_google(messages: List[HumanMessage]) -> Tuple[object, int]:
    last_err: Optional[Exception] = None
    for idx, llm in enumerate(GOOGLE_LLMS):
        try:
            return await llm.ainvoke(messages), idx
        except Exception as e:
            last_err = e
            if _is_rate_limit_error(e):
                continue
            else:
                # Non-rate-limit error, try next key anyway
                continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")

def _invoke_google(messages: List[HumanMessage]) -> Tuple[object, int]:
    last_err: Optional[Exception] = None
    for idx, llm in enumerate(GOOGLE_LLMS):
        try:
            return llm.invoke(messages, max_retries=0), idx
        except Exception as e:
            last_err = e
            if _is_rate_limit_error(e):
                continue
            else:
                continue
    if last_err:
        raise last_err
    raise RuntimeError("No Google Gemini API keys configured.")

def _transcribe_with_openai(audio_bytes: bytes, file_ext: str = "wav") -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OpenAI fallback not configured.")
    # Use LangChain community OpenAI Whisper parser
    parser = OpenAIWhisperParser(
        api_key=OPENAI_API_KEY,
        model=OPENAI_TRANSCRIBE_MODEL,
    )
    # Try direct bytes; if parser requires a file path, fall back to temp file
    try:
        result = parser.parse(audio_bytes)  # type: ignore[arg-type]
    except Exception:
        tmp_path = os.path.join(VOICE_NOTES_DIR, f"tmp_asr_{uuid.uuid4()}.{file_ext}")
        with open(tmp_path, "wb") as f:
            f.write(audio_bytes)
        try:
            if hasattr(parser, "parse_file"):
                result = parser.parse_file(tmp_path)  # type: ignore[attr-defined]
            else:
                result = parser.parse(tmp_path)  # type: ignore[arg-type]
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    # Normalize output across possible return types
    if isinstance(result, str):
        return result
    try:
        # Document object with page_content
        return getattr(result, "page_content", "")
    except Exception:
        try:
            # List of Documents
            return "\n".join(getattr(doc, "page_content", "") for doc in result)
        except Exception:
            return str(result)

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
    """Use ffmpeg to extract mono WAV audio from a video URL or file path."""
    cmd = [
        "ffmpeg", "-y",
        "-i", url,
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        out_wav_path,
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def _transcribe_audio_bytes(audio_bytes: bytes, lang_hint: str | None = None) -> str:
    """Transcribe bytes via Gemini, with OpenAI fallback, honoring language hints when possible."""
    try:
        b64 = b64encode(audio_bytes).decode("utf-8")
        inst = "Transcribe this audio recording."
        if lang_hint and ("japanese" in lang_hint.lower() or lang_hint.lower() == "ja"):
            inst = "Transcribe this audio in Japanese script (hiragana/katakana/kanji)."
        msg = HumanMessage(content=[
            {"type": "text", "text": inst},
            {"type": "file", "source_type": "base64", "mime_type": "audio/wav", "data": b64},
        ])
        resp, _ = providers.invoke_google([msg])
        return str(getattr(resp, "content", resp))
    except Exception:
        try:
            code = None
            if lang_hint:
                l = lang_hint.strip().lower()
                code = "ja" if l in ("japanese", "ja") else l
            return providers.transcribe_with_openai(audio_bytes, file_ext="wav", language=code)
        except Exception:
            return ""


def generate_scenarios_from_transcript(transcript: str, target_language: str = "Japanese", max_scenes: int = 5) -> list:
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
    try:
        resp, _ = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": prompt}])])
        text = str(getattr(resp, "content", resp))
    except Exception:
        text = providers.openai_chat([HumanMessage(content=prompt)])
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
    return generate_scenarios_from_transcript(transcript, target_language=target_language, max_scenes=max_scenes)

def process_interaction(audio_file, current_scenario_id_str, lang: Optional[str] = None):
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
        transcribed_text = None
        try:
            audio_b64 = b64encode(audio_bytes).decode("utf-8")
            # Prefer Japanese script when lang indicates Japanese
            lang_hint = (lang or "").strip().lower()
            if "japanese" in lang_hint or lang_hint == "ja":
                instruction = "Transcribe this audio in Japanese script (hiragana/katakana/kanji). Do not romanize."
            elif lang_hint:
                instruction = f"Transcribe this audio in {lang} using its native script."
            else:
                instruction = "Transcribe this audio recording."
            message = HumanMessage(
                content=[
                    {"type": "text", "text": instruction},
                    {
                        "type": "file",
                        "source_type": "base64",
                        "mime_type": "audio/webm",
                        "data": audio_b64,
                    },
                ]
            )
            response, key_index = _invoke_google([message])
            transcribed_text = response.content
            try:
                print("[interaction] Heard:", (transcribed_text or "")[:200])
            except Exception:
                pass
            usage.log_usage(
                event="interaction_transcribe",
                provider="gemini",
                model=GOOGLE_MODEL,
                key_label=usage.key_label_from_index(key_index, GOOGLE_KEYS),
                status="success",
            )
        except Exception as gerr:
            if _should_google_fallback(gerr):
                # Try OpenAI fallback (webm not natively supported by Whisper unless ffmpeg converts,
                # but often webm/opus works if container is acceptable. If it fails, bubble up.)
                try:
                    # Prefer providers implementation so we can pass language hint
                    lang_code = "ja" if (lang or "").strip().lower() in ("japanese", "ja") else None
                    transcribed_text = providers.transcribe_with_openai(audio_bytes, file_ext="webm", language=lang_code)
                except Exception:
                    # Fall back to legacy helper
                    transcribed_text = _transcribe_with_openai(audio_bytes, file_ext="webm")
                try:
                    print("[interaction/openai] Heard:", (transcribed_text or "")[:200])
                except Exception:
                    pass
                usage.log_usage(
                    event="interaction_transcribe",
                    provider="openai",
                    model=OPENAI_TRANSCRIBE_MODEL,
                    key_label=usage.OPENAI_LABEL,
                    status="success",
                )
            else:
                raise gerr

        heard_raw = transcribed_text or ""
        transcribed_text = (transcribed_text or "").lower()

        # 3. Recognize Intent (Simplified MVP Logic)
        current_scenario = get_scenario_by_id(current_scenario_id)
        if not current_scenario:
            return {"error": "Scenario not found", "heard": heard_raw}

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
            DEFAULT_SUCCESS_POINTS,
        )
        penalties_cfg = current_scenario.get("penalties") or {}
        incorrect_cfg = penalties_cfg.get("incorrect_answer") or {}
        failure_lives = _coerce_int(
            incorrect_cfg.get("lives")
            or incorrect_cfg.get("life")
            or incorrect_cfg.get("health")
            or incorrect_cfg.get("count"),
            DEFAULT_FAILURE_LIFE_COST,
        )
        language_cfg = penalties_cfg.get("language_mismatch") or {}
        language_failure_lives = _coerce_int(
            language_cfg.get("lives")
            or language_cfg.get("life")
            or language_cfg.get("health")
            or language_cfg.get("count"),
            failure_lives or DEFAULT_FAILURE_LIFE_COST,
        )

        success = False

        def _contains_japanese(text: str) -> bool:
            try:
                for ch in text:
                    o = ord(ch)
                    # Hiragana, Katakana, Kanji common blocks
                    if (0x3040 <= o <= 0x30FF) or (0x31F0 <= o <= 0x31FF) or (0x4E00 <= o <= 0x9FFF):
                        return True
            except Exception:
                pass
            return False

        next_scenario_id = None

        # Heuristic quick pass for clear English yes/no
        if transcribed_text:
            if any(k in transcribed_text for k in ["yes", "yeah", "yep", "i am", "sure", "ok", "okay"]):
                for option in current_scenario.get("options", []):
                    if "yes" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
                        break
            if not next_scenario_id and any(k in transcribed_text for k in ["no", "not", "nope", "nah"]):
                for option in current_scenario.get("options", []):
                    if "no" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
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
                        break
            if not next_scenario_id and any(tok in raw for tok in ["いいえ", "いや", "いえ", "ノー"]):
                for option in current_scenario.get("options", []):
                    if "no" in (option.get("text") or "").lower():
                        next_scenario_id = option.get("next_scenario")
                        if next_scenario_id is not None:
                            success = True
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
                        break

        # Scenario-specific keyword/example matching
        if not next_scenario_id and current_scenario.get("options"):
            try:
                best_score = 0.0
                best_idx = -1
                import re
                raw = heard_raw or ""
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
                if best_idx >= 0 and best_score >= 0.6:
                    next_scenario = current_scenario["options"][best_idx]
                    next_scenario_id = next_scenario.get("next_scenario")
                    if next_scenario_id is not None:
                        success = True
            except Exception:
                pass

        # If target language is Japanese and user spoke non‑Japanese, prompt them to say it in Japanese
        if (lang or "").lower() in ("japanese", "ja") and heard_raw and not _contains_japanese(heard_raw):
            try:
                jp = providers.translate_text(heard_raw, to_language="Japanese", from_language="English")
            except Exception:
                jp = ""
            try:
                pron = providers.romanize(jp, "Japanese") if jp else ""
            except Exception:
                pron = ""
            out = {
                "heard": heard_raw,
                "npcDoesNotUnderstand": True,
                "message": "Please say it in Japanese.",
                "scoreDelta": 0,
                "livesDelta": -language_failure_lives,
            }
            if jp:
                out["repeatExpected"] = jp
                if pron:
                    out["pronunciation"] = pron
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
                prompt = (
                    "You are choosing the best matching option for a user's spoken reply.\n"
                    "The user reply may be in any language (e.g., Japanese).\n"
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
                            }
                except Exception:
                    pass
            # Return heard text so UI can display it; signal that it didn't match
            return {
                "error": "Could not determine intent from speech.",
                "heard": heard_raw,
                "scoreDelta": 0,
                "livesDelta": -failure_lives,
            }

        # 4. Determine Next Scenario
        success = True
        next_scenario = get_scenario_by_id(next_scenario_id)
        if not next_scenario:
            return {"error": "Next scenario not found", "heard": heard_raw, "scoreDelta": 0, "livesDelta": 0}
        
        return {
            "nextScenario": next_scenario,
            "heard": heard_raw,
            "scoreDelta": reward_points if success else 0,
            "livesDelta": 0,
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
        audio_b64 = b64encode(audio_bytes).decode("utf-8")
        # Choose mime type based on ext
        mime = 'audio/wav'
        if ext in ('webm',):
            mime = 'audio/webm'
        elif ext in ('ogg',):
            mime = 'audio/ogg'
        elif ext in ('mp3',):
            mime = 'audio/mp3'
        elif ext in ('m4a',):
            mime = 'audio/mp4'
        transcription_message = HumanMessage(
            content=[
                {"type": "text", "text": "Transcribe this audio recording."},
                {
                    "type": "file",
                    "source_type": "base64",
                    "mime_type": mime,
                    "data": audio_b64,
                },
            ]
        )
        try:
            # Try Gemini quickly (up to 2 attempts across rotated keys), then fallback
            gemini_ok = False
            last_key_index = None
            for attempt in range(2):
                try:
                    transcription_response, key_index = await asyncio.to_thread(
                        providers.invoke_google, [transcription_message]
                    )
                    last_key_index = key_index
                    transcribed_text = transcription_response.content
                    gemini_ok = True
                    break
                except Exception as ge:
                    print(f"Gemini transcribe attempt {attempt+1} failed for {base_filename}: {ge}")
                    if providers.should_google_fallback(ge):
                        break
                    # non-rate-limit error: try once more, then fallback
                    continue
            if gemini_ok:
                usage.log_usage(
                    event="transcribe",
                    provider="gemini",
                    model=config.GOOGLE_MODEL,
                    key_label=providers.key_label_from_index(last_key_index or 0),
                    status="success",
                )
            else:
                raise RuntimeError("Gemini unavailable, falling back")
        except Exception as e:
            # Fallback to OpenAI Whisper
            print(f"Falling back to Whisper for {base_filename}: {e}")
            transcribed_text = providers.transcribe_with_openai(audio_bytes, file_ext=ext)
            usage.log_usage(
                event="transcribe",
                provider="openai",
                model=config.OPENAI_TRANSCRIBE_MODEL,
                key_label=usage.OPENAI_LABEL,
                status="success",
            )
        print(f"Successfully transcribed {base_filename}.")

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
                    if providers.should_google_fallback(ge):
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
    try:
        b64 = b64encode(audio_bytes).decode("utf-8")
        msg = HumanMessage(
            content=[
                {"type": "text", "text": "Transcribe this audio recording."},
                {"type": "file", "source_type": "base64", "mime_type": mime or "audio/webm", "data": b64},
            ]
        )
        resp, key_index = providers.invoke_google([msg])
        heard = str(getattr(resp, "content", resp))
        usage.log_usage(
            event="imitate_transcribe",
            provider="gemini",
            model=config.GOOGLE_MODEL,
            key_label=providers.key_label_from_index(key_index or 0),
            status="success",
        )
    except Exception as ge:
        # Fallback to OpenAI Whisper
        heard = providers.transcribe_with_openai(audio_bytes, file_ext=("webm" if (mime and "webm" in mime) else "wav"))
        usage.log_usage(
            event="imitate_transcribe",
            provider="openai",
            model=config.OPENAI_TRANSCRIBE_MODEL,
            key_label=usage.OPENAI_LABEL,
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
    return {"success": success, "score": round(score, 3), "heard": heard, "makesSense": makes_sense}


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
