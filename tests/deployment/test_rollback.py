#tests/test_rollback.py

import os
from app.simulation.rollback_manager import save_snapshot, latest_snapshot, load_snapshot, rollback_to_latest
def test_save_and_load(tmp_path):
    cfg = {"workloads": {"a": {"resources": {"cpu": 1}}}}
    path = save_snapshot(cfg, base_dir=str(tmp_path))
    assert os.path.exists(path)
    latest = latest_snapshot(base_dir=str(tmp_path))
    assert latest == path
    obj = load_snapshot(latest)
    assert "config" in obj
    assert obj["config"] == cfg

def test_rollback_no_snapshot(tmp_path):
    res = rollback_to_latest(base_dir=str(tmp_path))
    assert res is None
