"""
Scenario option suggestion generation.
"""
from __future__ import annotations

import os
from typing import List, Optional
from langchain_core.messages import HumanMessage
import config
import providers
import voice_select
import usage_log as usage
from .scenarios import get_scenario_by_id


def _scenario_context_text(s: dict) -> str:
    """Build context text from scenario."""
    parts = []
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
    target_language: Optional[str] = None,
    native_language: Optional[str] = None,
    stage: str = "examples",
) -> dict:
    """Generate example utterances for each option in the given scenario.

    Returns JSON:
    {
      "question": "What do you say?",
      "options": [
         {"option_text": "Yes", "examples": [...], "next_scenario": 2},
         {"option_text": "No",  "examples": [...], "next_scenario": 3}
      ]
    }
    """
    scenario = get_scenario_by_id(scenario_id)
    if not scenario:
        return {"question": "", "options": []}

    opts = scenario.get("options") or []
    context_txt = _scenario_context_text(scenario)
    n = max(1, int(n_per_option or 3))

    question = "What do you say to the kind man?"
    if scenario.get("question"):
        question = str(scenario["question"]).strip()
    elif scenario.get("description"):
        question = "What do you say?"

    option_lines = "\n".join([f"- {o.get('text','')}" for o in opts])

    # System instruction
    sys = (
        "You help a child learn speaking through example phrases. "
        "Return short, simple, positive phrases a child might say."
    )
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
        f"Available option meanings:\n{option_lines}\n\n"
        f"Task: For each option, generate {n} example phrases the learner could say.\n"
        " Keep each phrase under 12 words. Avoid quotes, bullets, or numbering.\n"
        + (
            ' Respond ONLY as compact JSON like {"options": [[{"native": "...", "target": "..."}, ...], ...]} '
            if native_language or target_language
            else ' Respond ONLY as compact JSON: {"options":[[phrases for option1],[phrases for option2], ...]}.'
        )
    )

    suggestions_any: list | None = None
    suggestions: list[list[dict]] = []

    try:
        # Try Gemini first
        resp, key_index = providers.invoke_google([HumanMessage(content=[{"type": "text", "text": sys + "\n\n" + user}])])
        raw = str(getattr(resp, "content", resp))
        try:
            import json
            data = json.loads(raw)
            suggestions_any = data.get("options") or []
        except Exception:
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
        raw = providers.openai_chat([HumanMessage(content=sys + "\n\n" + user)])
        try:
            import json
            data = json.loads(raw)
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
                        native = ""
                        target = str(item).strip()
                    if native or target:
                        items.append({"native": native, "target": target})
                out.append(items)
            else:
                out.append([{"native": "", "target": str(group).strip()}])
        return out

    suggestions = _coerce_pair_list(suggestions_any or [])

    out = {"question": question, "options": []}
    for i, o in enumerate(opts):
        group = suggestions[i] if i < len(suggestions) and isinstance(suggestions[i], list) else []
        seen = set()
        items = []

        for idx, pair in enumerate(group):
            native_txt = (pair.get("native") or "").strip().strip('"').strip("'")
            target_txt = (pair.get("target") or "").strip().strip('"').strip("'")
            key = target_txt.lower()

            # Translate missing sides if languages are provided
            if (not target_txt) and native_language and target_language and native_txt:
                try:
                    target_txt = providers.translate_text(native_txt, to_language=target_language, from_language=native_language)
                except Exception:
                    target_txt = native_txt
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
            selected_voice = None
            try:
                os.makedirs(config.EXAMPLES_AUDIO_DIR, exist_ok=True)
                example_dict = {"native": native_txt, "target": target_txt}
                selected_voice = voice_select.select_voice(
                    scenario=scenario,
                    option=o,
                    example=example_dict,
                    role="npc",
                )
                fname = f"scenario-{scenario_id}-opt{i}-ex{len(items)}.mp3"
                fpath = os.path.join(config.EXAMPLES_AUDIO_DIR, fname)
                if not os.path.exists(fpath):
                    audio_bytes = providers.tts_with_openai(target_txt, voice=selected_voice, fmt="mp3")
                    with open(fpath, "wb") as wf:
                        wf.write(audio_bytes)
                audio_rel = f"/examples/{fname}"
            except Exception:
                audio_rel = None

            items.append({"native": native_txt, "target": target_txt, "audio": audio_rel, "voice": selected_voice})
            if len(items) >= n:
                break

        out["options"].append({
            "option_text": o.get("text", ""),
            "examples": items,
            "next_scenario": o.get("next_scenario"),
        })

    return out
