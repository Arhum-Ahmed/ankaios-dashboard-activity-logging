# app/simulation/validator_service.py
from typing import Dict, Any, Optional
from . import deployment_simulator, rollback_manager
import io
import yaml
import copy

SchemaValidator = None
DependencyValidator = None
ResourceConflictDetector = None

try:
    from app.validators.schema_validator import SchemaValidator as _SV
    SchemaValidator = _SV
except Exception:
    SchemaValidator = None

try:
    from app.validators.dependency_validator import DependencyValidator as _DV
    DependencyValidator = _DV
except Exception:
    DependencyValidator = None

try:
    from app.validators.conflict_detector import ResourceConflictDetector as _RC
    ResourceConflictDetector = _RC
except Exception:
    ResourceConflictDetector = None

def _translate_for_validators(config: Dict[str, Any]) -> Dict[str, Any]:
    cfg_copy = copy.deepcopy(config) if isinstance(config, dict) else config
    if not isinstance(cfg_copy, dict):
        return cfg_copy
    workloads = cfg_copy.get("workloads", {})
    if not isinstance(workloads, dict):
        return cfg_copy
    for name, w in list(workloads.items()):
        if not isinstance(w, dict):
            continue
        if "depends_on" in w and "dependencies" not in w:
            depends = w.get("depends_on") or []
            if isinstance(depends, list):
                dep_map = {d: {} for d in depends}
                w["dependencies"] = dep_map
            else:
                try:
                    possible_map = dict(depends)
                    w["dependencies"] = possible_map
                except Exception:
                    w["dependencies"] = {}
        workloads[name] = w
    cfg_copy["workloads"] = workloads
    return cfg_copy

class ValidatorService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.schema_validator = SchemaValidator() if SchemaValidator else None
        try:
            self.dependency_validator = DependencyValidator() if DependencyValidator else None
        except Exception:
            self.dependency_validator = DependencyValidator if DependencyValidator else None
        self.conflict_detector = ResourceConflictDetector() if ResourceConflictDetector else None

    def _to_yaml_text(self, config: Dict[str, Any]) -> str:
        try:
            return yaml.safe_dump(config)
        except Exception:
            return str(config)

    def _safe_call(self, obj, possible_methods, config_input):
        for method in possible_methods:
            if hasattr(obj, method):
                fn = getattr(obj, method)
                try:
                    return fn(config_input)
                except TypeError:
                    try:
                        return fn(io.StringIO(config_input))
                    except Exception:
                        raise
                except Exception:
                    raise
        raise AttributeError(f"{obj.__class__.__name__} has none of {possible_methods}")

    def run_pre_checks(self, config: Dict) -> Dict[str, Any]:
        results = {"schema": None, "dependency": None, "conflicts": None, "ok": True, "issues": []}
        translated = _translate_for_validators(config) if isinstance(config, dict) else config
        yaml_text = self._to_yaml_text(translated)
        if self.schema_validator:
            try:
                ok, issues = self._safe_call(self.schema_validator, ["validate", "validate_workload_config", "validate_schema"], yaml_text)
            except Exception as e:
                ok, issues = False, [{"type": "schema_validator_exception", "message": str(e)}]
            results["schema"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)
        if self.dependency_validator:
            try:
                ok, issues = self._safe_call(self.dependency_validator, ["validate", "validate_dependencies"], yaml_text)
            except Exception as e:
                ok, issues = False, [{"type": "dependency_validator_exception", "message": str(e)}]
            results["dependency"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)
        if self.conflict_detector:
            try:
                ok, issues = self._safe_call(self.conflict_detector, ["detect", "detect_conflicts"], yaml_text)
            except Exception as e:
                ok, issues = False, [{"type": "conflict_detector_exception", "message": str(e)}]
            results["conflicts"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)
        return results

    def apply_config(self, config: Dict, cluster_capacity: Optional[Dict] = None) -> Dict[str, Any]:
        pre = self.run_pre_checks(config)
        report = { "pre_check": pre, "simulation": None, "snapshot_path": None, "rollback": None }
        if not pre.get("ok", False):
            report["error"] = "precheck_failed"
            return report
        workloads = config.get("workloads", {}) if isinstance(config, dict) else {}
        sim = deployment_simulator.simulate_deployment(workloads, cluster_capacity=cluster_capacity)
        report["simulation"] = sim
        if sim.get("success"):
            try:
                path = rollback_manager.save_snapshot(config, base_dir=self.base_dir)
                report["snapshot_path"] = path
            except Exception as e:
                report["snapshot_error"] = {"message": str(e)}
        else:
            try:
                restored = rollback_manager.rollback_to_latest(base_dir=self.base_dir)
                report["rollback"] = { "restored": restored is not None, "restored_config": restored }
            except Exception as e:
                report["rollback"] = { "restored": False, "error": str(e) }
        return report
