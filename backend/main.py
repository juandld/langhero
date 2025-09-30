import logging

# Silence verbose loggers
logging.basicConfig(level=logging.INFO)
loggers_to_silence = [
    "google.generativeai",
    "langchain",
    "langchain_core",
    "langchain_google_genai",
]
for logger_name in loggers_to_silence:
    # Use ERROR to reduce noisy quota retry warnings
    logging.getLogger(logger_name).setLevel(logging.ERROR)

from fastapi import FastAPI, File, UploadFile, Form, Response, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from services import (
    process_interaction,
    get_notes,
    transcribe_and_save,
    generate_option_suggestions,
    list_scenarios,
    reload_scenarios,
    list_scenario_versions,
    save_scenarios_version,
    activate_scenario_version,
    imitate_say,
    generate_scenarios_from_video,
)
from models import TagsUpdate
from utils import on_startup
import uvicorn
import socket
import os
from datetime import datetime
import uuid
import asyncio
from langchain_core.messages import HumanMessage
import providers
import config

app = FastAPI()

# Configure CORS to allow requests from the SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for voice notes
VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'transcriptions'))
NARRATIVES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'narratives'))
EXAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples_audio'))
# Ensure mount directories exist before mounting static routes
os.makedirs(VOICE_NOTES_DIR, exist_ok=True)
os.makedirs(EXAMPLES_DIR, exist_ok=True)
app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR), name="voice_notes")
app.mount("/examples", StaticFiles(directory=EXAMPLES_DIR), name="examples")

@app.on_event("startup")
async def startup_event():
    await on_startup()

@app.post("/narrative/interaction")
async def handle_interaction(
    audio_file: UploadFile = File(...), 
    current_scenario_id: str = Form(...),
    lang: str = Form(None),
):
    """
    This endpoint receives audio and the current scenario ID,
    processes them, and returns the next scenario.
    """
    result = process_interaction(audio_file.file, current_scenario_id, lang)
    return result

@app.post("/narrative/imitate")
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
        # Attach the target scenario so the UI can advance
        try:
            ns = int(next_scenario)
            res['nextScenario'] = ns
        except Exception:
            pass
    return res

@app.post("/narrative/translate")
async def translate_endpoint(
    request: Request,
    text: str = Form(None),
    native: str = Form(...),
    target: str = Form(...),
    audio_file: UploadFile = File(None),
):
    """Translate user text (or speech) from native -> target and return pronunciation.

    Returns { native, target, pronunciation }
    """
    try:
        # If audio is provided, transcribe it first (assume native language)
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
            # Use Whisper fallback to handle many languages robustly
            native_text = providers.transcribe_with_openai(audio_bytes, file_ext=("webm" if 'webm' in mime else 'wav'))
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

@app.get("/narrative/options")
async def get_speaking_options(scenario_id: int, n_per_option: int = 3, lang: str | None = None, native: str | None = None, stage: str | None = None):
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

@app.get("/api/notes")
async def read_notes():
    """API endpoint to retrieve all notes."""
    return get_notes()

@app.post("/api/notes")
async def create_note(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    date: str = Form(None),
    place: str = Form(None)
):
    """API endpoint to upload a new note."""
    ct = (file.content_type or '').lower()
    if 'webm' in ct:
        ext = 'webm'
    elif 'ogg' in ct:
        ext = 'ogg'
    elif 'm4a' in ct:
        ext = 'm4a'
    elif 'mp3' in ct:
        ext = 'mp3'
    else:
        ext = 'wav'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}_{uuid.uuid4().hex[:6]}.{ext}"
    file_path = os.path.join(VOICE_NOTES_DIR, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())
    
    # Start transcription and title generation in the background
    print(f"File saved: {filename}. Adding transcription to background tasks.")
    background_tasks.add_task(transcribe_and_save, file_path)
    
    return {"filename": filename, "message": "File upload successful, transcription started."}

@app.post("/api/notes/{filename}/retry")
async def retry_note(background_tasks: BackgroundTasks, filename: str):
    """Manually trigger reprocessing (transcribe/title) for a specific note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
    background_tasks.add_task(transcribe_and_save, file_path)
    return {"status": "queued"}

@app.delete("/api/notes/{filename}")
async def delete_note(filename: str):
    """API endpoint to delete a note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        # Delete associated JSON (and legacy txt)
        base_filename = os.path.splitext(filename)[0]
        json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
        legacy_txt_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.txt")
        if os.path.exists(json_path):
            os.remove(json_path)
        if os.path.exists(legacy_txt_path):
            os.remove(legacy_txt_path)
        return Response(status_code=200)
    return Response(status_code=404)

@app.patch("/api/notes/{filename}/tags")
async def update_tags(filename: str, payload: TagsUpdate):
    """Update user-defined tags for a note (stored in JSON)."""
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")
    # Ensure a JSON exists
    if not os.path.exists(json_path):
        return Response(status_code=404)
    try:
        import json
        with open(json_path, 'r') as f:
            data = json.load(f)
        # Normalize tags into list of {label, color}
        tags = []
        for t in payload.tags:
            tags.append({"label": t.label, "color": t.color})
        data["tags"] = tags
        with open(json_path, 'w') as f:
            json.dump(data, f, ensure_ascii=False)
        return {"status": "ok", "tags": tags}
    except Exception as e:
        return {"error": str(e)}

# ----------------- Narratives API -----------------

@app.get("/api/narratives")
async def list_narratives():
    if not os.path.exists(NARRATIVES_DIR):
        os.makedirs(NARRATIVES_DIR)
    files = [f for f in sorted(os.listdir(NARRATIVES_DIR)) if f.endswith('.txt')]
    return files

@app.get("/api/narratives/{filename}")
async def get_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        return {"content": content}
    return Response(status_code=404)

@app.delete("/api/narratives/{filename}")
async def delete_narrative(filename: str):
    path = os.path.join(NARRATIVES_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        return Response(status_code=200)
    return Response(status_code=404)

@app.post("/api/narratives")
async def create_narrative_from_notes(request: Request):
    """Create a simple narrative by concatenating selected notes' titles and transcriptions.

    Expects JSON body: [{"filename": "...wav"}, ...]
    Writes a .txt file into narratives/ and returns its filename.
    """
    try:
        items = await request.json()
        if not isinstance(items, list):
            return Response(status_code=400)
        parts = []
        for it in items:
            name = (it or {}).get('filename')
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
            title = base
            text = ''
            if os.path.exists(json_path):
                import json
                with open(json_path, 'r') as jf:
                    data = json.load(jf)
                title = data.get('title') or title
                text = data.get('transcription') or ''
            parts.append(f"# {title}\n\n{text}\n\n")
        if not parts:
            return Response(status_code=400)
        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        from datetime import datetime
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        with open(out, 'w') as f:
            f.write("\n".join(parts))
        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/narratives/generate")
async def generate_narrative(request: Request):
    """Generate a narrative from selected notes and optional extra context via Gemini/OpenAI.

    Body JSON:
    {
      "items": [{"filename": "...wav"}, ...],
      "extra_text": "optional",
      "provider": "auto" | "gemini" | "openai",
      "model": "optional override",
      "temperature": 0.2,
      "system": "optional system instruction"
    }
    Returns: {"filename": "narrative-...txt"}
    """
    try:
        body = await request.json()
        items = (body or {}).get("items", [])
        extra_text = (body or {}).get("extra_text", "")
        provider_choice = ((body or {}).get("provider") or "auto").lower()
        model_override = (body or {}).get("model")
        temperature = float((body or {}).get("temperature") or 0.2)
        system_inst = (body or {}).get("system") or (
            "You are an expert editor. Synthesize a cohesive, structured narrative from the provided notes and context. "
            "Focus on clarity, key insights, and concrete action items. Keep it concise and readable."
        )

        # Collect sources
        if not isinstance(items, list):
            return Response(status_code=400)
        sources = []
        for it in items:
            name = (it or {}).get("filename")
            if not name or not isinstance(name, str):
                continue
            base = os.path.splitext(name)[0]
            json_path = os.path.join(TRANSCRIPTS_DIR, f"{base}.json")
            title = base
            text = ""
            if os.path.exists(json_path):
                import json
                with open(json_path, "r") as jf:
                    data = json.load(jf)
                title = data.get("title") or title
                text = data.get("transcription") or ""
            sources.append((title, text))

        if not sources and not extra_text.strip():
            return Response(status_code=400)

        # Build prompt
        parts = [system_inst.strip(), "\n\nContext Notes:\n"]
        for i, (title, text) in enumerate(sources, start=1):
            parts.append(f"[{i}] {title}\n{text}\n")
        if extra_text.strip():
            parts.append("\nAdditional Context:\n" + extra_text.strip() + "\n")
        parts.append("\nWrite the narrative now.")
        prompt_text = "\n".join(parts)

        # Call provider
        content = None
        key_index = None
        provider_used = provider_choice
        model_used = model_override or (config.GOOGLE_MODEL if provider_choice != "openai" else config.OPENAI_NARRATIVE_MODEL)
        if provider_choice in ("auto", "gemini"):
            try:
                resp, key_index = await asyncio.to_thread(
                    providers.invoke_google,
                    [HumanMessage(content=[{"type": "text", "text": prompt_text}])],
                    model_override if provider_choice == "gemini" and model_override else None,
                )
                content = str(getattr(resp, "content", resp))
                provider_used = "gemini"
                model_used = model_override or config.GOOGLE_MODEL
            except Exception:
                if provider_choice == "gemini":
                    raise
                provider_used = "openai"
                model_used = model_override or config.OPENAI_NARRATIVE_MODEL
                content = providers.openai_chat([HumanMessage(content=prompt_text)], model=model_override, temperature=temperature)
        else:
            provider_used = "openai"
            model_used = model_override or config.OPENAI_NARRATIVE_MODEL
            content = providers.openai_chat([HumanMessage(content=prompt_text)], model=model_override, temperature=temperature)

        if not os.path.exists(NARRATIVES_DIR):
            os.makedirs(NARRATIVES_DIR)
        name = f"narrative-{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        out = os.path.join(NARRATIVES_DIR, name)
        with open(out, "w") as f:
            f.write(content or "")

        try:
            usage.log_usage(
                event="narrative",
                provider=provider_used,
                model=model_used,
                key_label=(providers.key_label_from_index(key_index or 0) if provider_used == "gemini" else usage.OPENAI_LABEL),
                status="success",
            )
        except Exception:
            pass

        return {"filename": name}
    except Exception as e:
        return {"error": str(e)}

# ----------------- Scenarios Admin -----------------

@app.get("/api/scenarios")
async def api_list_scenarios():
    return list_scenarios()

@app.post("/api/scenarios/import")
async def api_import_scenarios(request: Request):
    """Replace scenarios with provided list. Body: {"scenarios": [...]}"""
    try:
        body = await request.json()
        scenarios = (body or {}).get("scenarios")
        if not isinstance(scenarios, list):
            return Response(status_code=400)
        reload_scenarios(scenarios)
        return {"status": "ok", "count": len(scenarios)}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/scenarios/from_video")
async def api_generate_scenarios_from_video(request: Request):
    """Generate and activate scenarios from a video URL.

    Body JSON: { "url": "https://...", "target_language": "Japanese", "max_scenes": 5, "activate": true }
    """
    try:
        body = await request.json()
        url = (body or {}).get("url")
        if not url or not isinstance(url, str):
            return Response(status_code=400)
        target_language = (body or {}).get("target_language") or "Japanese"
        max_scenes = (body or {}).get("max_scenes") or 5
        activate = bool((body or {}).get("activate", True))
        scenarios = await asyncio.to_thread(generate_scenarios_from_video, url, target_language, max_scenes)
        if not scenarios:
            return {"error": "generation_failed"}
        if activate:
            reload_scenarios(scenarios)
        return {"status": "ok", "count": len(scenarios), "activated": activate, "scenarios": scenarios}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/scenario-versions")
async def api_list_scenario_versions():
    return list_scenario_versions()

@app.post("/api/scenario-versions/save")
async def api_save_scenarios(request: Request):
    try:
        body = await request.json()
        label = (body or {}).get("label")
        filename = save_scenarios_version(label)
        return {"status": "ok", "filename": filename}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/scenario-versions/activate")
async def api_activate_scenarios(request: Request):
    try:
        body = await request.json()
        filename = (body or {}).get("filename")
        if not filename or not isinstance(filename, str):
            return Response(status_code=400)
        activate_scenario_version(filename)
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import os
    host = os.getenv("HOST", "0.0.0.0")
    try:
        port = int(os.getenv("PORT", "8000"))
    except Exception:
        port = 8000

    def _find_free_port() -> int:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        p = s.getsockname()[1]
        s.close()
        return p

    try:
        uvicorn.run(app, host=host, port=port)
    except OSError as e:
        # Address in use, fall back to a free port
        if getattr(e, 'errno', None) in (98, 48):  # 98 Linux, 48 macOS
            alt = _find_free_port()
            print(f"Port {port} in use. Falling back to {alt}.")
            uvicorn.run(app, host=host, port=alt)
        else:
            raise
