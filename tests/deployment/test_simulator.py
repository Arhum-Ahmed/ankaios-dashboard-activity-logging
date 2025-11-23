# import pytest
# from simulation.deployment_simulator import simulate_deployment, topo_sort

# def test_topo_sort_simple():
#     w = {
#         "a": {"depends_on": ["b"]},
#         "b": {"depends_on": []},
#     }
#     ok, order, cycles, missing = topo_sort(w)
#     assert ok is True
#     assert cycles is None
#     assert set(order) == {"a", "b"}
#     assert order.index("b") < order.index("a")

# def test_topo_sort_cycle():
#     w = {
#         "a": {"depends_on": ["b"]},
#         "b": {"depends_on": ["a"]},
#     }
#     ok, order, cycles, missing = topo_sort(w)
#     assert ok is False
#     assert cycles and len(cycles) >= 1

# def test_simulate_success():
#     w = {
#         "a": {"depends_on": ["b"], "resources": {"cpu": 1, "memory": 512}},
#         "b": {"depends_on": [], "resources": {"cpu": 1, "memory": 256}},
#     }
#     res = simulate_deployment(w, cluster_capacity={"cpu": 4, "memory": 4096})
#     assert res["success"] is True
#     assert any(ev["event"] == "started" for ev in res["timeline"])

# def test_simulate_overcommit():
#     w = {
#         "a": {"depends_on": [], "resources": {"cpu": 10, "memory": 4096}},
#         "b": {"depends_on": ["a"], "resources": {"cpu": 10, "memory": 4096}},
#     }
#     res = simulate_deployment(w, cluster_capacity={"cpu": 8, "memory": 8192})
#     assert res["success"] is False
#     assert any(i["type"] == "resource_overcommit" for i in res["issues"])
# test_deployment_simulator.py
import pytest
from simulation.deployment_simulator import simulate_deployment, topo_sort

def test_topo_sort_simple():
    # Passing scenario: simple DAG
    w = {
        "a": {"depends_on": ["b"]},
        "b": {"depends_on": []},
    }
    ok, order, cycles, missing = topo_sort(w)
    assert ok is True
    assert cycles is None
    assert set(order) == {"a", "b"}
    assert order.index("b") < order.index("a")

def test_topo_sort_cycle():
    # Failing scenario: circular dependency
    w = {
        "a": {"depends_on": ["b"]},
        "b": {"depends_on": ["a"]},
    }
    ok, order, cycles, missing = topo_sort(w)
    assert ok is False
    assert cycles and len(cycles) >= 1

def test_simulate_success():
    # Passing scenario: enough cluster resources
    w = {
        "a": {"depends_on": ["b"], "resources": {"cpu": 1, "memory": 512}},
        "b": {"depends_on": [], "resources": {"cpu": 1, "memory": 256}},
    }
    res = simulate_deployment(w, cluster_capacity={"cpu": 4, "memory": 4096})
    assert res["success"] is True
    assert any(ev["event"] == "started" for ev in res["timeline"])

def test_simulate_overcommit():
    # Failing scenario: resource overcommit
    w = {
        "a": {"depends_on": [], "resources": {"cpu": 10, "memory": 4096}},
        "b": {"depends_on": ["a"], "resources": {"cpu": 10, "memory": 4096}},
    }
    res = simulate_deployment(w, cluster_capacity={"cpu": 8, "memory": 8192})
    assert res["success"] is False
    assert any(i["type"] == "resource_overcommit" for i in res["issues"])
