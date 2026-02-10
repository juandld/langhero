"""
Narrative interaction endpoints for game dialogue processing.
"""

import json
from typing import Optional
from fastapi import APIRouter, File, UploadFile, Form, Response
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import providers
from services.interaction import process_interaction, imitate_say
from services.suggestions import generate_option_suggestions

router = APIRouter(prefix="/narrative", tags=["narrative"])


# --- Ask Bimbo (intent matching) ---

class AskBimboOption(BaseModel):
    text: str
    style: str = ""

class AskBimboRequest(BaseModel):
    player_text: str
    options: list[AskBimboOption]

class AskBimboResponse(BaseModel):
    matched_index: int
    confidence: str
    bimbo_says: str
    translation: str = ""
    pronunciation: str = ""


@router.post("/ask-bimbo", response_model=AskBimboResponse)
async def ask_bimbo(req: AskBimboRequest):
    """Match player's English intent to the closest available response option."""
    text = (req.player_text or "").strip()
    print(f"[ask-bimbo] Request: player_text={text!r}, options_count={len(req.options)}")
    for i, o in enumerate(req.options):
        print(f"[ask-bimbo]   option[{i}]: text={o.text!r}, style={o.style!r}")

    if not text:
        print("[ask-bimbo] Early return: empty text")
        return AskBimboResponse(
            matched_index=-1, confidence="none",
            bimbo_says="Type what you want to say and I'll help you find the right words!"
        )

    numbered = "\n".join(
        f"{i}. {o.text} [{o.style}]" for i, o in enumerate(req.options)
    ) if req.options else "(no options available)"

    prompt = f"""You are Bimbo, a witty time-travel companion helping a player learn Japanese through a story game.

The player typed what they want to express (in English). Your job:
1. Translate their intent into natural Japanese.
2. Give a short, funny, personality-driven remark about what they want to say (1-2 sentences). Be entertaining, not generic.
3. If their intent matches one of the available dialogue options, identify which one.

Player said: "{text}"

Available options:
{numbered}

Return JSON with exactly these fields:
- "bimbo_says": your funny, in-character remark about the player's intent
- "matched_index": the 0-based index of the best-matching option, or -1 if the player's intent is truly off-script
- "confidence": "high", "medium", "low", or "none"
- "translation": the player's intent translated into natural Japanese (always provide this, even for wild/creative inputs)

Return ONLY valid JSON, no markdown."""

    print(f"[ask-bimbo] Prompt length: {len(prompt)} chars")

    try:
        raw = providers.openai_chat(
            [HumanMessage(content=prompt)],
            model="gpt-4o-mini",
            temperature=0.7,
        )
        print(f"[ask-bimbo] LLM raw response: {raw!r}")

        # Parse LLM JSON response
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            print(f"[ask-bimbo] Stripped markdown fences: {cleaned!r}")

        parsed = json.loads(cleaned)
        print(f"[ask-bimbo] Parsed JSON: {parsed}")

        translation = parsed.get("translation", "")
        pronunciation = ""
        if translation:
            try:
                pronunciation = providers.romanize(translation, "Japanese")
                print(f"[ask-bimbo] Romanized: {pronunciation!r}")
            except Exception as rom_err:
                print(f"[ask-bimbo] Romanize error (non-fatal): {rom_err}")

        result = AskBimboResponse(
            matched_index=int(parsed.get("matched_index", -1)),
            confidence=parsed.get("confidence", "medium"),
            bimbo_says=parsed.get("bimbo_says", "Try saying one of the options!"),
            translation=translation,
            pronunciation=pronunciation,
        )
        print(f"[ask-bimbo] Response: index={result.matched_index}, confidence={result.confidence}, "
              f"says={result.bimbo_says!r}, translation={result.translation!r}, pronunciation={result.pronunciation!r}")
        return result
    except Exception as e:
        import traceback
        print(f"[ask-bimbo] ERROR: {e}")
        print(f"[ask-bimbo] Traceback:\n{traceback.format_exc()}")
        return AskBimboResponse(
            matched_index=-1, confidence="none",
            bimbo_says="Hmm, I'm having trouble thinking right now. Try tapping an option to hear it!"
        )


@router.post("/interaction")
async def handle_interaction(
    audio_file: UploadFile = File(...),
    current_scenario_id: str = Form(...),
    lang: str = Form(None),
    judge: str = Form(None),
):
    """
    Receives audio and the current scenario ID,
    processes them, and returns the next scenario.
    """
    judge_value = None
    try:
        if judge is not None and str(judge).strip() != "":
            judge_value = float(judge)
    except Exception:
        judge_value = None
    result = process_interaction(audio_file.file, current_scenario_id, lang, judge=judge_value)
    return result


@router.post("/imitate")
async def imitate_endpoint(
    audio_file: UploadFile = File(...),
    expected: str = Form(...),
    next_scenario: int = Form(None),
    lang: str = Form(None),
):
    """Transcribe learner audio and check similarity to expected.

    Returns {success, score, heard, nextScenario?}
    """
    ct = (audio_file.content_type or '').lower()
    if 'webm' in ct:
        mime = 'audio/webm'
    elif 'ogg' in ct:
        mime = 'audio/ogg'
    elif 'm4a' in ct:
        mime = 'audio/mp4'
    elif 'mp3' in ct:
        mime = 'audio/mp3'
    else:
        mime = 'audio/wav'
    audio_bytes = audio_file.file.read()
    res = imitate_say(audio_bytes, mime, expected, lang)
    if res.get('success') and next_scenario is not None:
        try:
            ns = int(next_scenario)
            res['nextScenario'] = ns
        except Exception:
            pass
    return res


@router.post("/translate")
async def translate_endpoint(
    text: str = Form(None),
    native: str = Form(...),
    target: str = Form(...),
    audio_file: UploadFile = File(None),
):
    """Translate user text (or speech) from native -> target and return pronunciation.

    Returns { native, target, pronunciation }
    """
    try:
        # If audio is provided, transcribe it first
        if audio_file is not None:
            ct = (audio_file.content_type or '').lower()
            if 'webm' in ct:
                mime = 'audio/webm'
            elif 'ogg' in ct:
                mime = 'audio/ogg'
            elif 'm4a' in ct:
                mime = 'audio/mp4'
            elif 'mp3' in ct:
                mime = 'audio/mp3'
            else:
                mime = 'audio/wav'
            audio_bytes = audio_file.file.read()
            result = providers.transcribe_audio(
                audio_bytes,
                file_ext=("webm" if "webm" in mime else "wav"),
                mime_type=mime,
                instructions="Transcribe this audio recording.",
                context=providers.CONTEXT_TRANSLATE,
            )
            native_text = result.text
        else:
            native_text = (text or '').strip()

        if not native_text:
            return Response(status_code=400)

        # Translate to target
        target_text = providers.translate_text(native_text, to_language=target, from_language=native)

        # Pronunciation (romaji) when target is Japanese
        pron = providers.romanize(target_text, target)

        return {"native": native_text, "target": target_text, "pronunciation": pron}
    except Exception as e:
        return {"error": str(e)}


@router.get("/options")
async def get_speaking_options(
    scenario_id: int,
    n_per_option: int = 3,
    lang: Optional[str] = None,
    native: Optional[str] = None,
    stage: Optional[str] = None
):
    """Return child-friendly example utterances for the current scenario options.

    Query: scenario_id (int), n_per_option (int, default 3), lang (optional target language), stage (examples|hints)
    """
    try:
        data = generate_option_suggestions(
            scenario_id,
            n_per_option,
            target_language=lang or None,
            native_language=native or None,
            stage=stage or "examples",
        )
        return data
    except Exception as e:
        return {"question": "", "options": [], "error": str(e)}
