# app/simulation/deployment_simulator.py
from typing import Dict, List, Tuple, Any, Optional
import time

class SimulationError(Exception):
    pass

def topo_sort(workloads: Dict[str, Dict]) -> Tuple[bool, List[str], Optional[List[List[str]]], List[str]]:
    """
    Perform topological sorting on workloads with dependencies.

    Returns:
        ok: True if no cycles, False otherwise
        ordered: list of workloads in deployment order
        cycles: list of detected cycles (None if no cycles)
        missing: list of missing dependencies
    """
    visited = {}
    result: List[str] = []
    cycles: List[List[str]] = []
    missing: set = set()

    def dfs(node: str, stack: List[str]) -> bool:
        if node not in workloads:
            missing.add(node)
            return True
        if visited.get(node) == 1:  # visiting -> cycle
            cycles.append(stack + [node])
            return False
        if visited.get(node) == 2:  # already visited
            return True

        visited[node] = 1
        deps = workloads[node].get("depends_on", []) or []

        # also accept 'dependencies' mapping but treat keys as deps
        if not deps and isinstance(workloads[node].get("dependencies", None), dict):
            deps = list(workloads[node]["dependencies"].keys())

        for d in deps:
            ok = dfs(d, stack + [node])
            if not ok:
                pass

        visited[node] = 2
        result.append(node)
        return True

    for w in workloads.keys():
        if visited.get(w) is None:
            dfs(w, [])

    if cycles:
        return False, [], cycles, list(missing)

    # Correct order: dependencies appear before dependents
    ordered = result.copy()
    return True, ordered, None, list(missing)

def simulate_deployment(
    workloads: Dict[str, Dict],
    cluster_capacity: Dict[str, float] = None,
    simulate_crash_prob: float = 0.0,
) -> Dict[str, Any]:
    if cluster_capacity is None:
        cluster_capacity = {"cpu": 1e6, "memory": 1e9}

    ok, order, cycles, missing = topo_sort(workloads)
    if not ok:
        return {
            "success": False,
            "issues": [{"type": "circular_dependency", "cycles": cycles}],
            "plan_order": [],
            "timeline": [],
        }

    issues: List[Dict[str, Any]] = []
    if missing:
        issues.append({
            "type": "missing_dependency",
            "nodes": missing,
            "message": f"Missing referenced workloads: {list(missing)}"
        })

    used = {"cpu": 0.0, "memory": 0.0}
    timeline: List[Dict[str, Any]] = []

    for svc in order:
        svc_meta = workloads.get(svc) or {}
        resources = svc_meta.get("resources", {}) or {}
        try:
            cpu = float(resources.get("cpu", 0.0))
            mem = float(resources.get("memory", 0.0))
        except Exception:
            cpu = 0.0
            mem = 0.0

        ts = time.time()
        timeline.append({
            "event": "starting",
            "service": svc,
            "timestamp": ts,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
            "cpu": cpu,
            "memory": mem,
            "used_cpu_before": used["cpu"],
            "used_mem_before": used["memory"],
        })

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
                "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
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

        used["cpu"] += cpu
        used["memory"] += mem
        timeline.append({
            "event": "started",
            "service": svc,
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
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
