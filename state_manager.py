"""
state_manager.py
Tracks which BSE announcements have already been sent, to prevent duplicate alerts.
Persisted as a JSON file on disk.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "seen_announcements.json"

# How many days of history to keep (older entries are purged)
RETENTION_DAYS = 7


def _load() -> dict:
    """Load the persisted state from disk."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read state file: %s. Starting fresh.", e)
    return {}


def _save(state: dict):
    """Persist the state to disk."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _purge_old_entries(state: dict) -> dict:
    """Remove entries older than RETENTION_DAYS to keep the file small."""
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).isoformat()
    return {k: v for k, v in state.items() if v >= cutoff}


def is_new(announcement_id: str) -> bool:
    """Return True if this announcement has NOT been seen before."""
    state = _load()
    return announcement_id not in state


def mark_seen(announcement_id: str):
    """Record this announcement as seen (with current timestamp)."""
    state = _load()
    state[announcement_id] = datetime.now().isoformat()
    state = _purge_old_entries(state)
    _save(state)
    logger.debug("Marked as seen: %s", announcement_id)


def get_seen_count() -> int:
    """Return number of tracked (seen) announcements."""
    return len(_load())
