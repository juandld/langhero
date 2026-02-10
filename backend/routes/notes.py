"""
Notes CRUD endpoints for voice note management.
"""

import os
import json
from datetime import datetime
import uuid
from fastapi import APIRouter, File, UploadFile, Form, Response, BackgroundTasks
from models import TagsUpdate
from services.transcription import transcribe_and_save
from services.notes import get_notes
import config

router = APIRouter(prefix="/api/notes", tags=["notes"])

VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'voice_notes'))
TRANSCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'transcriptions'))


@router.get("")
async def read_notes():
    """API endpoint to retrieve all notes."""
    return get_notes()


@router.post("")
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

    os.makedirs(VOICE_NOTES_DIR, exist_ok=True)
    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    # Start transcription and title generation in the background
    print(f"File saved: {filename}. Adding transcription to background tasks.")
    background_tasks.add_task(transcribe_and_save, file_path)

    return {"filename": filename, "message": "File upload successful, transcription started."}


@router.post("/{filename}/retry")
async def retry_note(background_tasks: BackgroundTasks, filename: str):
    """Manually trigger reprocessing (transcribe/title) for a specific note."""
    file_path = os.path.join(VOICE_NOTES_DIR, filename)
    if not os.path.exists(file_path):
        return Response(status_code=404)
    background_tasks.add_task(transcribe_and_save, file_path)
    return {"status": "queued"}


@router.delete("/{filename}")
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


@router.patch("/{filename}/tags")
async def update_tags(filename: str, payload: TagsUpdate):
    """Update user-defined tags for a note (stored in JSON)."""
    base_filename = os.path.splitext(filename)[0]
    json_path = os.path.join(TRANSCRIPTS_DIR, f"{base_filename}.json")

    if not os.path.exists(json_path):
        return Response(status_code=404)

    try:
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
