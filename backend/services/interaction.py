"""
Interaction processing for game dialogue.
"""
from __future__ import annotations

import os
import re
import uuid
import time
from typing import Optional, List
from difflib import SequenceMatcher
from langchain_core.messages import HumanMessage
import config
import providers
import usage_log as usage
from language import contains_japanese
from .scenarios import get_scenario_by_id
from .feedback import generate_social_feedback

VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'voice_notes'))


def _normalize_text_for_match(s: str) -> str:
    """Normalize text for similarity matching."""
    import string
    s = (s or "").lower().strip()
    table = str.maketrans({c: " " for c in string.punctuation})
    s = s.translate(table)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    na, nb = _normalize_text_for_match(a), _normalize_text_for_match(b)
    if not na or not nb:
        return 0.0
    return float(SequenceMatcher(a=na, b=nb).ratio())


def _clamp_float(value: object, default: float = 0.0, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to a range."""
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

        # Save temporary audio file
        audio_bytes = audio_file.read()
        os.makedirs(VOICE_NOTES_DIR, exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        # Transcribe Audio
        lang_hint_value = (lang or "").strip().lower()
        if "japanese" in lang_hint_value or lang_hint_value == "ja":
            instruction = (
                "Transcribe this audio recording. "
                "If the speech is Japanese, write it in Japanese script without romanizing. "
                "If it is another language, transcribe using that language's normal writing system. "
                "Do not translate."
            )
        elif lang_hint_value:
            instruction = (
                "Transcribe this audio recording. "
                f"The expected language is {lang}, but always use the language that is actually spoken. "
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
            print(f"[interaction/{result.provider}] Heard: {(transcribed_text or '')[:200]} ({duration_ms}ms)")
        except Exception:
            pass

        # Log usage
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

        heard_raw = transcribed_text or ""
        transcribed_text = (transcribed_text or "").lower()
        match_confidence = 0.0
        match_type = "none"
        best_match_score = 0.0
        best_match_threshold = None

        # Get current scenario
        current_scenario = get_scenario_by_id(current_scenario_id)
        if not current_scenario:
            return {"error": "Scenario not found", "heard": heard_raw, "confidence": 0.0, "match_type": "missing_scenario"}

        # Infer language if not provided
        if not lang:
            lang = current_scenario.get("language") or ("Japanese" if current_scenario.get("character_dialogue_jp") else "English")

        def _coerce_int(value, default):
            try:
                return max(0, int(value))
            except Exception:
                return default

        reward_points = _coerce_int(
            current_scenario.get("reward_points") or current_scenario.get("points") or current_scenario.get("success_points"),
            config.DEFAULT_SUCCESS_POINTS,
        )

        penalties_cfg = current_scenario.get("penalties") or {}
        incorrect_cfg = penalties_cfg.get("incorrect_answer") or {}
        failure_lives = _coerce_int(
            incorrect_cfg.get("lives") or incorrect_cfg.get("life") or incorrect_cfg.get("health") or incorrect_cfg.get("count"),
            config.DEFAULT_FAILURE_LIFE_COST,
        )

        language_cfg = penalties_cfg.get("language_mismatch") or {}
        language_failure_lives = _coerce_int(
            language_cfg.get("lives") or language_cfg.get("life") or language_cfg.get("health") or language_cfg.get("count"),
            failure_lives or config.DEFAULT_FAILURE_LIFE_COST,
        )

        # Judge focus slider
        judge_story_weight = _clamp_float(judge, default=0.0)

        success = False
        next_scenario_id = None

        # Quick pass for English yes/no
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

        # Japanese yes/no quick pass
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

        # Japanese polite acceptance
        if not next_scenario_id and heard_raw:
            raw = (heard_raw or "").strip()
            if any(tok in raw for tok in ["お願いします", "おねがいします", "下さい", "ください", "欲しい", "ほしい"]):
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
                raw = heard_raw or ""
                threshold = 0.6 - (0.12 * judge_story_weight)

                for idx, opt in enumerate(current_scenario["options"]):
                    candidates: List[str] = []
                    for kw in (opt.get("keywords") or []):
                        if isinstance(kw, str) and kw.strip():
                            candidates.append(kw.strip())
                    for ex in (opt.get("examples") or []):
                        if isinstance(ex, str) and ex.strip():
                            candidates.append(ex.strip())
                        elif isinstance(ex, dict):
                            for k in ("target", "native", "pronunciation"):
                                v = (ex.get(k) or "").strip()
                                if v:
                                    candidates.append(v)

                    for cand in candidates:
                        score = 0.0
                        if cand and cand in raw:
                            score = max(score, 0.95)
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

        # Check for wrong language
        if judge_story_weight < 0.66 and (lang or "").lower() in ("japanese", "ja") and heard_raw and not contains_japanese(heard_raw):
            feedback = generate_social_feedback(success=False, match_type="wrong_language")
            out = {
                "heard": heard_raw,
                "npcDoesNotUnderstand": True,
                "message": "Please say it in Japanese.",
                "scoreDelta": 0,
                "livesDelta": -language_failure_lives,
                "confidence": 0.0,
                "match_type": "wrong_language",
                "socialFeedback": feedback.get("message"),
                "socialSentiment": feedback.get("sentiment"),
                "styleGained": None,
                "stylePoints": 0,
            }
            if next_scenario_id:
                out["repeatNextScenario"] = next_scenario_id
            return out

        # Semantic choice via LLM
        if not next_scenario_id and current_scenario.get("options"):
            try:
                opts = current_scenario["options"]
                lines = []
                for idx, opt in enumerate(opts, start=1):
                    line = f"{idx}. {opt.get('text') or ''}"
                    exs = opt.get('examples') or []
                    if exs:
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
                    "Judging focus: STORY-FIRST (prioritize narrative progression)."
                    if judge_story_weight >= 0.66
                    else "Judging focus: LEARNING-FIRST (prefer target-language intent)."
                )

                prompt = (
                    "You are choosing the best matching option for a user's spoken reply.\n"
                    f"{focus_line}\n"
                    "Given the scenario context and these options, reply with ONLY the number of the best option (1-based).\n"
                    "If none fit, reply 0.\n\n"
                    f"Context: {current_scenario.get('description') or ''}\n"
                    f"Character line JP: {current_scenario.get('character_dialogue_jp') or ''}\n"
                    f"Character line EN: {current_scenario.get('character_dialogue_en') or ''}\n\n"
                    f"Options:\n{options_block}\n\n"
                    f"User said: {heard_raw}\n\nAnswer:"
                )

                resp, key_index = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": prompt}])])
                out = str(getattr(resp, "content", resp)).strip()
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
                    out = providers.openai_chat([HumanMessage(content=prompt)])
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

        # Handle no match
        if not next_scenario_id:
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
                                feedback = generate_social_feedback(success=False, match_type="wrong_language")
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
                                    "socialFeedback": feedback.get("message"),
                                    "socialSentiment": feedback.get("sentiment"),
                                    "styleGained": None,
                                    "stylePoints": 0,
                                }
                except Exception:
                    pass

            feedback = generate_social_feedback(success=False, match_type="no_match")
            return {
                "error": "Could not determine intent from speech.",
                "heard": heard_raw,
                "scoreDelta": 0,
                "livesDelta": -failure_lives,
                "confidence": float(best_match_score or 0.0),
                "match_type": match_type if match_type != "none" else "no_match",
                "best_match_score": float(best_match_score or 0.0),
                "best_match_threshold": float(best_match_threshold) if best_match_threshold is not None else None,
                "socialFeedback": feedback.get("message"),
                "socialSentiment": feedback.get("sentiment"),
                "styleGained": None,
                "stylePoints": 0,
            }

        # Success path
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

        # Extract style from matched option
        matched_style = None
        for opt in current_scenario.get("options", []):
            if opt.get("next_scenario") == next_scenario_id:
                matched_style = opt.get("style")
                break

        feedback = generate_social_feedback(success=True, match_type=match_type, style=matched_style)

        return {
            "nextScenario": next_scenario,
            "heard": heard_raw,
            "scoreDelta": reward_points if success else 0,
            "livesDelta": 0,
            "confidence": float(match_confidence or 0.0),
            "match_type": match_type,
            "best_match_score": float(best_match_score or 0.0),
            "best_match_threshold": float(best_match_threshold) if best_match_threshold is not None else None,
            "socialFeedback": feedback.get("message"),
            "socialSentiment": feedback.get("sentiment"),
            "styleGained": feedback.get("styleGained"),
            "stylePoints": feedback.get("stylePoints", 0),
        }

    except Exception as e:
        return {"error": str(e), "scoreDelta": 0, "livesDelta": 0}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def imitate_say(audio_bytes: bytes, mime: str, expected_text: str, target_lang: Optional[str] = None) -> dict:
    """Transcribe the audio and compare to expected_text. Returns {success, score, heard, makesSense}."""
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

    score = _similarity(heard or "", expected_text or "")
    success = score >= 0.72

    makes_sense = False
    try:
        makes_sense = providers.makes_sense(heard or "", language=(target_lang or ""))
    except Exception:
        makes_sense = False

    try:
        print(f"[imitate] Expect='{(expected_text or '')[:60]}' Heard='{(heard or '')[:60]}' score={score:.3f}")
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
