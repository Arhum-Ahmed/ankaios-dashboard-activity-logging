# deployment/validator_service.py
"""
Unified validator orchestrator:
Runs schema, dependency, and conflict validators.
Handles both YAML file-based and dict-based validators automatically.
"""

from typing import Dict, Any, Optional
from . import deployment_simulator, rollback_manager
import io
import yaml

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


class ValidatorService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.schema_validator = SchemaValidator() if SchemaValidator else None
        self.dependency_validator = DependencyValidator() if DependencyValidator else None
        self.conflict_detector = ResourceConflictDetector() if ResourceConflictDetector else None

    def _prepare_input(self, config):
        """Convert dict to file-like if validator expects .read()."""
        if isinstance(config, dict):
            yaml_text = yaml.safe_dump(config)
            return io.StringIO(yaml_text)
        return config

    def _safe_call(self, obj, possible_methods, config):
        """Try to call the first available validator method safely."""
        for method in possible_methods:
            if hasattr(obj, method):
                fn = getattr(obj, method)
                try:
                    return fn(config)
                except AttributeError as e:
                    # Handle case where validator tries config.read()
                    if "'dict' object has no attribute 'read'" in str(e):
                        return fn(self._prepare_input(config))
                    raise
        raise AttributeError(f"{obj.__class__.__name__} has none of {possible_methods}")

    def run_pre_checks(self, config: Dict) -> Dict[str, Any]:
        results = {"schema": None, "dependency": None, "conflicts": None, "ok": True, "issues": []}

        if self.schema_validator:
            try:
                ok, issues = self._safe_call(self.schema_validator, ["validate", "validate_schema"], config)
            except Exception as e:
                ok, issues = False, [{"type": "schema_validator_exception", "message": str(e)}]
            results["schema"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)

        if self.dependency_validator:
            try:
                ok, issues = self._safe_call(self.dependency_validator, ["validate", "validate_dependencies"], config)
            except Exception as e:
                ok, issues = False, [{"type": "dependency_validator_exception", "message": str(e)}]
            results["dependency"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)

        if self.conflict_detector:
            try:
                ok, issues = self._safe_call(self.conflict_detector, ["detect", "detect_conflicts"], config)
            except Exception as e:
                ok, issues = False, [{"type": "conflict_detector_exception", "message": str(e)}]
            results["conflicts"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)

        return results

    def apply_config(self, config: Dict, cluster_capacity: Optional[Dict] = None) -> Dict[str, Any]:
        pre = self.run_pre_checks(config)
        report = {"pre_check": pre, "simulation": None, "snapshot_path": None, "rollback": None}

        if not pre["ok"]:
            return report

        workloads = config.get("workloads", {}) if isinstance(config, dict) else {}
        sim = deployment_simulator.simulate_deployment(workloads, cluster_capacity=cluster_capacity)
        report["simulation"] = sim

        if sim["success"]:
            path = rollback_manager.save_snapshot(config, base_dir=self.base_dir)
            report["snapshot_path"] = path
        else:
            restored = rollback_manager.rollback_to_latest(base_dir=self.base_dir)
            report["rollback"] = {"restored": restored is not None, "restored_config": restored}

        return report
