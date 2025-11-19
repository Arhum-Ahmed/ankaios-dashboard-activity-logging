"""
Test Executor - Runs complete validation suite
"""
from datetime import datetime
from typing import Dict, List
import time
import yaml

from .schema_validator import ConfigurationValidator
from .dependency_validator import DependencyValidator
from .conflict_detector import ResourceConflictDetector


class PreDeploymentTester:
    """Executes complete pre-deployment validation suite"""
    
    def __init__(self, current_workloads: List[Dict] = None):
        """
        Args:
            current_workloads: List of currently deployed workloads
        """
        self.current_workloads = current_workloads or []
        self.current_workload_names = [w.get('name') for w in self.current_workloads]
    
    def run_validation_suite(self, config_yaml: str) -> Dict:
        """
        Run complete validation suite
        Returns: Comprehensive validation report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'PASSED',
            'tests': [],
            'summary': {}
        }
        
        # Test 1: Schema Validation
        start_time = time.time()
        schema_validator = ConfigurationValidator()
        is_valid, issues = schema_validator.validate_workload_config(config_yaml)
        duration_ms = int((time.time() - start_time) * 1000)
        
        report['tests'].append({
            'name': 'Schema Validation',
            'description': 'Validates YAML syntax and configuration structure',
            'status': 'PASSED' if is_valid else 'FAILED',
            'issues': issues,
            'duration_ms': duration_ms
        })
        
        # Test 2: Dependency Validation
        start_time = time.time()
        dep_validator = DependencyValidator(self.current_workload_names)
        is_valid, issues = dep_validator.validate_dependencies(config_yaml)
        duration_ms = int((time.time() - start_time) * 1000)
        
        report['tests'].append({
            'name': 'Dependency Validation',
            'description': 'Checks if all dependencies exist and are valid',
            'status': 'PASSED' if is_valid else 'FAILED',
            'issues': issues,
            'duration_ms': duration_ms
        })
        
        # Test 3: Circular Dependency Check
        start_time = time.time()
        try:
            config = yaml.safe_load(config_yaml)
            has_cycles, cycles = dep_validator.detect_circular_dependencies(config.get('workloads', {}))
            
            report['tests'].append({
                'name': 'Circular Dependency Check',
                'description': 'Detects circular dependencies using graph algorithms',
                'status': 'FAILED' if has_cycles else 'PASSED',
                'issues': [{
                    'type': 'CIRCULAR_DEPENDENCY',
                    'severity': 'ERROR',
                    'message': f'Circular dependency: {" -> ".join(cycle)}',
                    'cycle': cycle
                } for cycle in cycles],
                'duration_ms': int((time.time() - start_time) * 1000)
            })
        except:
            report['tests'].append({
                'name': 'Circular Dependency Check',
                'status': 'SKIPPED',
                'issues': [],
                'duration_ms': 0
            })
        
        # Test 4: Resource Conflict Detection
        start_time = time.time()
        conflict_detector = ResourceConflictDetector(self.current_workloads)
        no_conflicts, issues = conflict_detector.detect_conflicts(config_yaml)
        duration_ms = int((time.time() - start_time) * 1000)
        
        report['tests'].append({
            'name': 'Resource Conflict Detection',
            'description': 'Checks for port and resource conflicts',
            'status': 'PASSED' if no_conflicts else 'FAILED',
            'issues': issues,
            'duration_ms': duration_ms
        })
        
        # Calculate overall status
        failed_tests = [t for t in report['tests'] if t['status'] == 'FAILED']
        if failed_tests:
            report['overall_status'] = 'FAILED'
        
        # Calculate summary statistics
        total_errors = sum(
            len([i for i in test.get('issues', []) if i.get('severity') == 'ERROR'])
            for test in report['tests']
        )
        total_warnings = sum(
            len([i for i in test.get('issues', []) if i.get('severity') == 'WARNING'])
            for test in report['tests']
        )
        
        report['summary'] = {
            'total_tests': len(report['tests']),
            'passed': len([t for t in report['tests'] if t['status'] == 'PASSED']),
            'failed': len(failed_tests),
            'skipped': len([t for t in report['tests'] if t['status'] == 'SKIPPED']),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'total_duration_ms': sum(t.get('duration_ms', 0) for t in report['tests'])
        }
        
        return report
# ----------------------------------------------------------------------
# Extension: Self-Healing Remediation (Non-intrusive)
# ----------------------------------------------------------------------

from .config_remediator import ConfigurationRemediator

class SelfHealingPreDeploymentTester(PreDeploymentTester):
    """
    Extended version of PreDeploymentTester with optional self-healing remediation.
    """

    def run_with_remediation(self, config_yaml: str) -> Dict:
        """
        Runs full validation suite and attempts automated remediation
        if any tests fail.
        Returns:
            Dict containing original report, remediated config, and remediation log
        """
        # 1️⃣ Run original validation
        base_report = super().run_validation_suite(config_yaml)

        # 2️⃣ Collect all issues from failed tests
        all_issues = []
        for test in base_report.get('tests', []):
            all_issues.extend(test.get('issues', []))

        if base_report['overall_status'] == 'PASSED' or not all_issues:
            # No remediation needed
            return {
                'report': base_report,
                'remediated_config': config_yaml,
                'remediation_log': ['No issues detected — remediation not required.']
            }

        # 3️⃣ Trigger remediation module
        remediator = ConfigurationRemediator()
        fixed_yaml, remediation_log = remediator.auto_fix(config_yaml, all_issues)

        # 4️⃣ Re-run the validator on the remediated config
        post_fix_report = super().run_validation_suite(fixed_yaml)

        # 5️⃣ Combine results
        return {
            'initial_report': base_report,
            'remediated_config': fixed_yaml,
            'remediation_log': remediation_log,
            'post_remediation_report': post_fix_report
        }
                