# deployment/rollback_manager.py
"""
Simple file-backed rollback manager.
It stores snapshots of valid configs in a .ankaios_history directory and can restore last-good version.
"""

import os
import json
import time
from typing import Dict, Optional
from pathlib import Path

HISTORY_DIR = ".ankaios_history"


def ensure_history_dir(base_dir: str = ".") -> Path:
    p = Path(base_dir) / HISTORY_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_snapshot(cfg: Dict, base_dir: str = ".", name: Optional[str] = None) -> str:
    """
    Save snapshot as JSON. Return path to snapshot.
    """
    hist = ensure_history_dir(base_dir)
    if name is None:
        ts = int(time.time() * 1000)
        name = f"snapshot_{ts}.json"
    dest = hist / name
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return str(dest)


def list_snapshots(base_dir: str = ".") -> list:
    hist = ensure_history_dir(base_dir)
    items = sorted(hist.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p) for p in items]


def load_snapshot(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def latest_snapshot(base_dir: str = ".") -> Optional[str]:
    snaps = list_snapshots(base_dir)
    return snaps[0] if snaps else None


def rollback_to_latest(base_dir: str = ".", restore_path: Optional[str] = None) -> Optional[Dict]:
    """
    Returns the restored config dict, or None if no snapshot exists.
    """
    snap = restore_path or latest_snapshot(base_dir)
    if not snap:
        return None
    return load_snapshot(snap)
