# deployment/tests/test_rollback_manager.py
import os
import shutil
from deployment.rollback_manager import save_snapshot, latest_snapshot, load_snapshot, list_snapshots

TEST_DIR = "tests_tmp_history"


def setup_function(fn):
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)


def teardown_function(fn):
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)


def test_save_and_load_snapshot():
    cfg = {"workloads": {"x": {"resources": {"cpu": 1, "memory": 1}}}}
    p = save_snapshot(cfg, base_dir=TEST_DIR, name="snap.json")
    assert os.path.exists(p)
    snaps = list_snapshots(TEST_DIR)
    assert len(snaps) >= 1
    latest = latest_snapshot(TEST_DIR)
    assert latest is not None
    obj = load_snapshot(latest)
    assert obj["workloads"]["x"]["resources"]["cpu"] == 1
