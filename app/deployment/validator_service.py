# deployment/validator_service.py
"""
Orchestrator to run existing validators (schema, dependency, conflict), simulate deployments,
save last-good snapshot, and rollback if simulation fails.

Adapts to validators if they are present in your codebase. If not present, pre-checks pass-through.
"""

from typing import Dict, Any, Optional
from . import deployment_simulator, rollback_manager

# Defensive imports: adapt these names to your actual validator classes if necessary.
SchemaValidator = None
DependencyValidator = None
ResourceConflictDetector = None

try:
    # try relative imports that match many repo layouts
    from app.validators.schema_validator import SchemaValidator as _SV
    SchemaValidator = _SV
except Exception:
    try:
        from schema_validator import SchemaValidator as _SV2
        SchemaValidator = _SV2
    except Exception:
        SchemaValidator = None

try:
    from app.validators.dependency_validator import DependencyValidator as _DV
    DependencyValidator = _DV
except Exception:
    try:
        from dependency_validator import DependencyValidator as _DV2
        DependencyValidator = _DV2
    except Exception:
        DependencyValidator = None

try:
    from app.validators.conflict_detector import ResourceConflictDetector as _RC
    ResourceConflictDetector = _RC
except Exception:
    try:
        from conflict_detector import ResourceConflictDetector as _RC2
        ResourceConflictDetector = _RC2
    except Exception:
        ResourceConflictDetector = None


class ValidatorService:
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        self.schema_validator = SchemaValidator() if SchemaValidator else None
        self.dependency_validator = DependencyValidator() if DependencyValidator else None
        self.conflict_detector = ResourceConflictDetector() if ResourceConflictDetector else None

    def run_pre_checks(self, config: Dict) -> Dict[str, Any]:
        """
        Run your existing validators; return dict with results.
        Expected validator signatures: validate(config) -> (ok: bool, issues: list)
        If a validator is not present, it's skipped and considered ok.
        """
        results = {"schema": None, "dependency": None, "conflicts": None, "ok": True, "issues": []}

        if self.schema_validator:
            try:
                ok, issues = self.schema_validator.validate(config)
            except Exception as e:
                ok, issues = False, [{"type": "schema_validator_exception", "message": str(e)}]
            results["schema"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)

        if self.dependency_validator:
            try:
                ok, issues = self.dependency_validator.validate(config)
            except Exception as e:
                ok, issues = False, [{"type": "dependency_validator_exception", "message": str(e)}]
            results["dependency"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)

        if self.conflict_detector:
            try:
                ok, issues = self.conflict_detector.detect(config)
            except Exception as e:
                ok, issues = False, [{"type": "conflict_detector_exception", "message": str(e)}]
            results["conflicts"] = {"ok": ok, "issues": issues}
            if not ok:
                results["ok"] = False
                results["issues"].extend(issues)

        return results

    def apply_config(self, config: Dict, cluster_capacity: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run pre-checks, simulate, and either accept and snapshot config or rollback.
        Returns a report dict with:
          - pre_check
          - simulation
          - snapshot_path (if accepted)
          - rollback (if performed)
        """
        pre = self.run_pre_checks(config)
        report = {"pre_check": pre, "simulation": None, "snapshot_path": None, "rollback": None}
        if not pre["ok"]:
            return report

        # Expect config to have 'workloads' top-level key
        workloads = config.get("workloads", {}) if isinstance(config, dict) else {}
        sim = deployment_simulator.simulate_deployment(workloads, cluster_capacity=cluster_capacity)
        report["simulation"] = sim
        if sim["success"]:
            # save snapshot as last-good
            path = rollback_manager.save_snapshot(config, base_dir=self.base_dir)
            report["snapshot_path"] = path
            return report
        else:
            # simulation failed -> attempt rollback
            restored = rollback_manager.rollback_to_latest(base_dir=self.base_dir)
            report["rollback"] = {
                "restored": restored is not None,
                "restored_config": restored,
            }
            return report
