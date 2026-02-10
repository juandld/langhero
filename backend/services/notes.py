"""
Notes management utilities.
"""
from __future__ import annotations

import os
import re
from typing import Optional
import datetime
import config
import note_store

VOICE_NOTES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'voice_notes'))

STOPWORDS = set(
    "the a an and or but for with without on in at to from of by this that those these "
    "is are was were be been being i you he she it we they them me my your our their as "
    "not just into over under again more most some any few many much very can could should would".split()
)


def _infer_topics(text: Optional[str], title: Optional[str]) -> list:
    """Infer topics from text or title."""
    source = (title or "").strip() or (text or "").strip()
    if not source:
        return []

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

    # Ensure transcripts dir exists
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    AUDIO_EXTS = ('.wav', '.ogg', '.webm', '.m4a', '.mp3')
    wav_files = [f for f in os.listdir(VOICE_NOTES_DIR) if f.lower().endswith(AUDIO_EXTS)]
    wav_files.sort(key=lambda f: os.path.getmtime(os.path.join(VOICE_NOTES_DIR, f)), reverse=True)

    for filename in wav_files:
        base_filename = filename[:-4]
        audio_path = os.path.join(VOICE_NOTES_DIR, filename)
        data, transcription, title = note_store.load_note_json(base_filename)

        if data is None:
            # JSON not yet created (transcription pending)
            mtime = os.path.getmtime(audio_path)
            date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            length_sec = note_store.audio_length_seconds(audio_path)
            notes.append({
                "filename": filename,
                "transcription": transcription,
                "title": title,
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
