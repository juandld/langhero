from __future__ import annotations

from typing import Optional


def normalize_language_token(value: Optional[str]) -> Optional[str]:
    """Normalize a user-facing language string to a compact internal token."""
    if not value:
        return None
    v = value.strip().lower()
    if v in {"ja", "jp", "japanese", "日本語"}:
        return "japanese"
    if v in {"en", "eng", "english"}:
        return "english"
    if v in {"es", "spa", "spanish", "espanol", "español"}:
        return "spanish"
    return v or None


def normalize_target_language(value: Optional[str]) -> str:
    """Normalize to display language names used in scenario JSON."""
    raw = (value or "").strip().lower()
    if not raw:
        return "English"
    if raw in {"ja", "jp", "japanese", "日本語"}:
        return "Japanese"
    if raw in {"en", "eng", "english"}:
        return "English"
    if raw in {"es", "spa", "spanish", "espanol", "español"}:
        return "Spanish"
    return (value or "").strip() or "English"


def contains_japanese(text: str) -> bool:
    try:
        for ch in text or "":
            o = ord(ch)
            if (0x3040 <= o <= 0x30FF) or (0x31F0 <= o <= 0x31FF) or (0x4E00 <= o <= 0x9FFF):
                return True
    except Exception:
        return False
    return False


def infer_target_language(setting: Optional[str] = None, text: Optional[str] = None) -> str:
    """Best-effort heuristic for inferring the target language for a story/scene."""
    t = (text or "").strip()
    s = (setting or "").strip().lower()
    # Strong signal: Japanese script present
    if contains_japanese(t):
        return "Japanese"
    # Spanish hints: punctuation/diacritics and common words
    if any(ch in t for ch in "áéíóúñÁÉÍÓÚÑ¿¡"):
        return "Spanish"
    lowered = t.lower()
    if any(w in lowered.split() for w in ("hola", "gracias", "por", "favor", "buenos", "dias", "qué", "como", "estás")):
        return "Spanish"
    # Setting hints (very lightweight)
    if any(k in s for k in ("japan", "tokyo", "kyoto", "osaka", "samurai", "shogun", "edo", "feudal japan")):
        return "Japanese"
    if any(k in s for k in ("spain", "madrid", "barcelona", "mexico", "bogota", "colombia", "argentina", "latam", "latin america")):
        return "Spanish"
    return "English"


def detect_language_from_text(text: str) -> str:
    """Very lightweight language heuristic (Japanese vs Spanish vs English vs Unknown)."""
    if not text:
        return "unknown"
    jp_count = 0
    es_count = 0
    en_count = 0
    for ch in text:
        code = ord(ch)
        if "a" <= ch.lower() <= "z":
            en_count += 1
        elif (
            0x3040 <= code <= 0x30FF  # Hiragana + Katakana
            or 0x31F0 <= code <= 0x31FF  # Katakana Phonetic Extensions
            or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs (common Kanji)
        ):
            jp_count += 1
        elif ch in "áéíóúÁÉÍÓÚ¿¡ñÑ":
            es_count += 2
    if jp_count > max(en_count, 3):
        return "japanese"
    lowered = text.lower()
    if jp_count == 0:
        if es_count >= 2:
            return "spanish"
        if any(tok in lowered.split() for tok in ("hola", "gracias", "por", "favor", "buenos", "dias", "adios", "perdon")):
            return "spanish"
    if en_count > 0 and en_count >= jp_count:
        return "english"
    return "unknown"

