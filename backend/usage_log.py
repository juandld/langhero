import os
import json
from datetime import datetime
from typing import Optional

# Usage directory within backend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USAGE_DIR = os.path.join(BASE_DIR, "usage")

OPENAI_LABEL = "openai"

def ensure_usage_paths():
    if not os.path.exists(USAGE_DIR):
        os.makedirs(USAGE_DIR, exist_ok=True)
    # Pre-create today's daily file and current weekly file if missing
    _ = _daily_path()
    _ = _weekly_path()

def _daily_path(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.utcnow()
    fname = f"daily-{dt.strftime('%Y-%m-%d')}.jsonl"
    path = os.path.join(USAGE_DIR, fname)
    if not os.path.exists(path):
        # touch file
        open(path, "a").close()
    return path

def _weekly_path(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.utcnow()
    year, week, _ = dt.isocalendar()
    fname = f"weekly-{year}-W{week:02d}.json"
    path = os.path.join(USAGE_DIR, fname)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({
                "year": year,
                "iso_week": week,
                "updated_at": dt.isoformat(),
                "totals": {"events": 0},
                "providers": {},
                "events": {},
                "models": {},
                # Higher-cardinality rollup for cost estimation and debugging.
                # Key format: "{event}|{provider}|{model}"
                "by_event_provider_model": {},
            }, f)
    return path

def key_label_from_index(index: int, keys: list[str]) -> str:
    try:
        key = keys[index]
    except Exception:
        return f"gemini_key_{index}"
    # Obfuscate key: show index and last 4 chars
    suffix = key[-4:] if key else "????"
    return f"gemini_key_{index}_{suffix}"

def _append_daily(event: dict):
    ensure_usage_paths()
    path = _daily_path()
    event_ts = event.get("timestamp") or datetime.utcnow().isoformat()
    event["timestamp"] = event_ts
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")

def _update_weekly(event: dict):
    ensure_usage_paths()
    path = _weekly_path()
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception:
        data = {
            "year": datetime.utcnow().year,
            "iso_week": datetime.utcnow().isocalendar()[1],
            "updated_at": datetime.utcnow().isoformat(),
            "totals": {"events": 0},
            "providers": {},
            "events": {},
            "models": {},
            "by_event_provider_model": {},
        }

    def inc(obj: dict, key: str, amt: int = 1):
        obj[key] = int(obj.get(key, 0)) + amt

    data["totals"]["events"] = int(data.get("totals", {}).get("events", 0)) + 1
    provider = event.get("provider", "unknown")
    model = event.get("model", "unknown")
    etype = event.get("event", "unknown")
    inc(data.setdefault("providers", {}), provider)
    inc(data.setdefault("events", {}), etype)
    inc(data.setdefault("models", {}), model)
    trip_key = f"{etype}|{provider}|{model}"
    inc(data.setdefault("by_event_provider_model", {}), trip_key)
    data["updated_at"] = datetime.utcnow().isoformat()

    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, path)

def log_usage(event: str, provider: str, model: str, key_label: str, status: str = "success"):
    record = {
        "event": event,
        "provider": provider,
        "model": model,
        "key": key_label,
        "status": status,
    }
    _append_daily(record)
    _update_weekly(record)


def load_weekly_summary(year: Optional[int] = None, iso_week: Optional[int] = None) -> dict:
    """Load a weekly usage summary JSON (default: current ISO week)."""
    dt = datetime.utcnow()
    if year is None or iso_week is None:
        year2, week2, _ = dt.isocalendar()
        year = year if year is not None else year2
        iso_week = iso_week if iso_week is not None else week2
    ensure_usage_paths()
    path = os.path.join(USAGE_DIR, f"weekly-{int(year)}-W{int(iso_week):02d}.json")
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {
            "year": int(year),
            "iso_week": int(iso_week),
            "updated_at": dt.isoformat(),
            "totals": {"events": 0},
            "providers": {},
            "events": {},
            "models": {},
            "by_event_provider_model": {},
        }
    if not isinstance(data, dict):
        return {
            "year": int(year),
            "iso_week": int(iso_week),
            "updated_at": dt.isoformat(),
            "totals": {"events": 0},
            "providers": {},
            "events": {},
            "models": {},
            "by_event_provider_model": {},
        }
    data.setdefault("year", int(year))
    data.setdefault("iso_week", int(iso_week))
    data.setdefault("updated_at", dt.isoformat())
    data.setdefault("totals", {"events": 0})
    data.setdefault("providers", {})
    data.setdefault("events", {})
    data.setdefault("models", {})
    data.setdefault("by_event_provider_model", {})
    return data


def load_recent_events(limit: int = 200, days: int = 7) -> list[dict]:
    """Load recent usage events from daily jsonl files (newest-first)."""
    ensure_usage_paths()
    try:
        limit_n = int(limit)
    except Exception:
        limit_n = 200
    limit_n = max(1, min(limit_n, 2000))
    try:
        days_n = int(days)
    except Exception:
        days_n = 7
    days_n = max(1, min(days_n, 60))

    events: list[dict] = []
    try:
        names = [n for n in os.listdir(USAGE_DIR) if n.startswith("daily-") and n.endswith(".jsonl")]
    except Exception:
        names = []
    # Lexicographic sort works for YYYY-MM-DD; process newest first.
    names.sort(reverse=True)
    for name in names[:days_n]:
        path = os.path.join(USAGE_DIR, name)
        try:
            with open(path, "r") as f:
                lines = f.readlines()
        except Exception:
            continue
        # Take newest records first.
        for line in reversed(lines):
            if len(events) >= limit_n:
                return events
            line = (line or "").strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if isinstance(rec, dict):
                events.append(rec)
    return events
