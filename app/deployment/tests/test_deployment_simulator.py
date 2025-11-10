# deployment/tests/test_deployment_simulator.py
import pytest
from deployment.deployment_simulator import simulate_deployment

SAMPLE_GOOD = {
    "service-a": {"depends_on": ["service-b"], "resources": {"cpu": 1.0, "memory": 512}},
    "service-b": {"depends_on": [], "resources": {"cpu": 1.0, "memory": 256}},
    "service-c": {"depends_on": ["service-a"], "resources": {"cpu": 2.0, "memory": 1024}},
}

SAMPLE_BAD_RESOURCE = {
    "service-a": {"depends_on": ["service-b"], "resources": {"cpu": 500.0, "memory": 512}},
    "service-b": {"depends_on": [], "resources": {"cpu": 600.0, "memory": 256}},
}

SAMPLE_CYCLE = {
    "a": {"depends_on": ["b"], "resources": {"cpu": 1, "memory": 1}},
    "b": {"depends_on": ["a"], "resources": {"cpu": 1, "memory": 1}},
}


def test_simulator_success():
    res = simulate_deployment(SAMPLE_GOOD, cluster_capacity={"cpu": 10.0, "memory": 4096})
    assert res["success"] is True
    assert res["plan_order"]
    assert len(res["timeline"]) > 0


def test_simulator_resource_overcommit():
    # small cluster to force overcommit
    res = simulate_deployment(SAMPLE_BAD_RESOURCE, cluster_capacity={"cpu": 100.0, "memory": 4096})
    # result should be failure due to resource overcommit
    assert res["success"] is False
    assert any(i["type"] == "resource_overcommit" for i in res["issues"])


def test_simulator_cycle_detected():
    res = simulate_deployment(SAMPLE_CYCLE, cluster_capacity={"cpu": 10, "memory": 1024})
    assert res["success"] is False
    assert any(i["type"] == "circular_dependency" for i in res["issues"])
