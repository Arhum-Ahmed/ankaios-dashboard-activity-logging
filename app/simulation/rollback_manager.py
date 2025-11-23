# app/simulation/rollback_manager.py
import os
import json
import time
from typing import Dict, Optional, List
from pathlib import Path
import tempfile
import hashlib

HISTORY_DIR = ".ankaios_history"
MAX_SNAPSHOTS = 50

def ensure_history_dir(base_dir: str = ".") -> Path:
    p = Path(base_dir) / HISTORY_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p

def _snapshot_metadata(cfg: Dict) -> Dict:
    meta = {
        "ts": int(time.time() * 1000),
        "iso_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode("utf-8")).hexdigest(),
    }
    return meta

def _atomic_write_json(path: Path, data: Dict):
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tf:
        json.dump(data, tf, indent=2)
        tf.flush()
        os.fsync(tf.fileno())
        tmpname = tf.name
    os.replace(tmpname, str(path))

def save_snapshot(cfg: Dict, base_dir: str = ".", name: Optional[str] = None) -> str:
    hist = ensure_history_dir(base_dir)
    meta = _snapshot_metadata(cfg)
    if name is None:
        name = f"snapshot_{meta['ts']}.json"
    dest = hist / name

    latest = latest_snapshot(base_dir)
    if latest:
        try:
            latest_obj = load_snapshot(latest)
            latest_meta = latest_obj.get("_meta", {})
            if latest_meta.get("sha256") == meta["sha256"]:
                return latest
        except Exception:
            pass

    wrapper = {"_meta": meta, "config": cfg}
    _atomic_write_json(dest, wrapper)
    _prune_history(hist, keep=MAX_SNAPSHOTS)
    return str(dest)

def list_snapshots(base_dir: str = ".") -> List[str]:
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
    snap = restore_path or latest_snapshot(base_dir)
    if not snap:
        return None
    obj = load_snapshot(snap)
    if isinstance(obj, dict) and "config" in obj:
        return obj["config"]
    return obj

def _prune_history(history_path: Path, keep: int = 50):
    files = sorted(history_path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[keep:]:
        try:
            old.unlink()
        except Exception:
            pass
