# deployment/deployment_simulator.py
"""
Deployment simulator:
- Topologically orders workloads according to depends_on (detects cycles)
- Simulates resource allocation (CPU, memory) on a provided cluster capacity
- Produces a timeline of events and a final success/failure summary
"""

from typing import Dict, List, Tuple, Any, Optional
import time


class SimulationError(Exception):
    pass


def topo_sort(workloads: Dict[str, Dict]) -> Tuple[bool, List[str], Optional[List[List[str]]]]:
    """
    Return (ok, order, cycles_if_any)
    workloads: {name: {"depends_on": [...], ...}, ...}
    """
    visited = {}
    result = []
    cycles = []

    def dfs(node, stack):
        if node not in workloads:
            # Unknown node — treat as leaf (no dependencies) for topo purposes
            visited[node] = 2
            result.append(node)
            return True
        if visited.get(node) == 1:
            # currently visiting -> cycle
            cycles.append(stack + [node])
            return False
        if visited.get(node) == 2:
            return True
        visited[node] = 1
        deps = workloads[node].get("depends_on", []) or []
        for d in deps:
            ok = dfs(d, stack + [node])
            # continue checking to find cycles, don't short-circuit
            if not ok:
                pass
        visited[node] = 2
        result.append(node)
        return True

    for w in workloads.keys():
        if visited.get(w) is None:
            dfs(w, [])
    if cycles:
        return False, [], cycles
    # reverse so dependencies come before dependents
    return True, list(reversed(result)), None


def simulate_deployment(
    workloads: Dict[str, Dict],
    cluster_capacity: Dict[str, float] = None,
    simulate_crash_prob: float = 0.0,
) -> Dict[str, Any]:
    """
    Simulate starting workloads in topological order.

    Args:
      workloads: mapping of service -> dict with at least "resources": {"cpu": float, "memory": float}
      cluster_capacity: {"cpu": float, "memory": float}. If None, defaults to very large.
      simulate_crash_prob: reserved for future random crash simulation (not used currently).

    Returns:
      {
        "success": bool,
        "issues": list,
        "plan_order": list[str],
        "timeline": list[dict],
      }
    """
    if cluster_capacity is None:
        # default: large capacity
        cluster_capacity = {"cpu": 1e6, "memory": 1e9}

    ok, order, cycles = topo_sort(workloads)
    if not ok:
        return {
            "success": False,
            "issues": [{"type": "circular_dependency", "cycles": cycles}],
            "plan_order": [],
            "timeline": [],
        }

    used = {"cpu": 0.0, "memory": 0.0}
    timeline: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

    for svc in order:
        svc_meta = workloads.get(svc, {}) or {}
        resources = svc_meta.get("resources", {}) or {}
        cpu = float(resources.get("cpu", 0.0))
        mem = float(resources.get("memory", 0.0))

        timeline.append({
            "event": "starting",
            "service": svc,
            "timestamp": time.time(),
            "cpu": cpu,
            "memory": mem,
            "used_cpu_before": used["cpu"],
            "used_mem_before": used["memory"],
        })

        # check overcommit
        if (used["cpu"] + cpu) > cluster_capacity.get("cpu", 0.0) or (used["memory"] + mem) > cluster_capacity.get("memory", 0.0):
            msg = (
                f"Resource overcommit when starting {svc}: "
                f"CPU {used['cpu'] + cpu}/{cluster_capacity.get('cpu')}, "
                f"MEM {used['memory'] + mem}/{cluster_capacity.get('memory')}"
            )
            issues.append({"type": "resource_overcommit", "service": svc, "message": msg})
            timeline.append({
                "event": "failed_to_start",
                "service": svc,
                "timestamp": time.time(),
                "note": msg,
                "cpu": cpu,
                "memory": mem,
            })
            return {
                "success": False,
                "issues": issues,
                "plan_order": order,
                "timeline": timeline,
            }

        # commit resource usage
        used["cpu"] += cpu
        used["memory"] += mem
        timeline.append({
            "event": "started",
            "service": svc,
            "timestamp": time.time(),
            "cpu": cpu,
            "memory": mem,
            "used_cpu_after": used["cpu"],
            "used_mem_after": used["memory"],
        })

    return {
        "success": True,
        "issues": issues,
        "plan_order": order,
        "timeline": timeline,
    }
