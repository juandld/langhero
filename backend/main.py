"""
LangHero Backend - FastAPI Application

A language learning game backend with real-time audio interactions,
scenario management, and AI-powered dialogue processing.
"""

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
    logging.getLogger(logger_name).setLevel(logging.ERROR)

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import socket
import config
from utils import on_startup

# Import route modules
from routes.meta import router as meta_router
from routes.streaming import router as streaming_router
from routes.narrative import router as narrative_router
from routes.voice import router as voice_router
from routes.notes import router as notes_router
from routes.narratives import router as narratives_router
from routes.scenarios import router as scenarios_router
from routes.scenario_versions import router as scenario_versions_router
from routes.panels import router as panels_router
from routes.published import router as published_router
from routes.import_routes import router as import_router
from routes.stories import router as stories_router
from routes.story_panels import router as story_panels_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    await on_startup()
    yield


app = FastAPI(lifespan=lifespan)

# ----------------- CORS Configuration -----------------

cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

allowed_regex = getattr(config, "ALLOWED_ORIGIN_REGEX", None)
if allowed_regex:
    cors_kwargs["allow_origin_regex"] = allowed_regex
else:
    origins = getattr(config, "ALLOWED_ORIGINS", None)
    if origins:
        cors_kwargs["allow_origins"] = origins
    else:
        cors_kwargs["allow_origin_regex"] = r"^http://(localhost|127\\.0\\.0\\.1)(:\\d+)?$"

app.add_middleware(CORSMiddleware, **cors_kwargs)

# ----------------- Static Files -----------------

VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'voice_notes'))
EXAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples_audio'))
IMAGE_CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'image_cache'))

os.makedirs(VOICE_NOTES_DIR, exist_ok=True)
os.makedirs(EXAMPLES_DIR, exist_ok=True)
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)

app.mount("/voice_notes", StaticFiles(directory=VOICE_NOTES_DIR), name="voice_notes")
app.mount("/examples", StaticFiles(directory=EXAMPLES_DIR), name="examples")
app.mount("/images/generated", StaticFiles(directory=IMAGE_CACHE_DIR), name="generated_images")

# ----------------- Register Routers -----------------

app.include_router(meta_router)
app.include_router(streaming_router)
app.include_router(narrative_router)
app.include_router(voice_router)
app.include_router(notes_router)
app.include_router(narratives_router)
app.include_router(scenarios_router)
app.include_router(scenario_versions_router)
app.include_router(panels_router)
app.include_router(published_router)
app.include_router(import_router)
app.include_router(stories_router)
app.include_router(story_panels_router)

# ----------------- Entry Point -----------------

if __name__ == "__main__":
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
        if getattr(e, 'errno', None) in (98, 48):  # Address in use
            alt = _find_free_port()
            print(f"Port {port} in use. Falling back to {alt}.")
            uvicorn.run(app, host=host, port=alt)
        else:
            raise
