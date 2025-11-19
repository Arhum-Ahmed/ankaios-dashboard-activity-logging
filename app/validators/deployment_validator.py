"""
Deployment Validator - Orchestrates validation, healing, and deployment
This service integrates the complete validation -> healing -> revalidation -> deployment flow
"""

import yaml
from typing import Tuple, Dict, List
from .schema_validator import ConfigurationValidator
from .dependency_validator import DependencyValidator
from .conflict_detector import ResourceConflictDetector
from .config_remediator import ConfigurationRemediator


class DeploymentValidator:
    """
    Orchestrates the complete deployment validation and healing flow.
    
    When a workload deployment is requested:
    1. Validate the configuration
    2. If validation fails, attempt to heal using remediator
    3. Re-validate the healed configuration
    4. Only allow deployment if final validation passes
    """
    
    def __init__(self, current_workloads: List[Dict] = None):
        """
        Args:
            current_workloads: List of currently deployed workloads (for dependency checking)
        """
        self.current_workloads = current_workloads or []
        self.current_workload_names = [w.get('name') for w in self.current_workloads]
        
        self.schema_validator = ConfigurationValidator()
        self.dep_validator = DependencyValidator(self.current_workload_names)
        self.conflict_detector = ResourceConflictDetector()
        self.remediator = ConfigurationRemediator()
    
    def validate_and_heal(self, config_yaml: str, auto_heal: bool = True) -> Dict:
        """
        Main orchestration method: Validate → Heal → Revalidate → Report
        
        Args:
            config_yaml: Configuration YAML as string
            auto_heal: If True, automatically attempt to heal validation failures
        
        Returns:
            {
                'success': bool,
                'original_valid': bool,
                'healed': bool,
                'final_valid': bool,
                'config': str (final YAML),
                'validation_report': dict,
                'healing_report': dict
            }
        """
        result = {
            'success': False,
            'original_valid': False,
            'healed': False,
            'final_valid': False,
            'config': config_yaml,
            'validation_report': {},
            'healing_report': {
                'attempted': False,
                'logs': [],
                'issues_healed': []
            }
        }
        
        # ========================================
        # STEP 1: INITIAL VALIDATION
        # ========================================
        validation_report = self._run_validation_suite(config_yaml)
        result['validation_report'] = validation_report
        
        # Check if initial validation passed
        all_errors = self._extract_errors_from_report(validation_report)
        result['original_valid'] = len(all_errors) == 0
        
        if result['original_valid']:
            result['success'] = True
            result['final_valid'] = True
            result['healing_report']['logs'].append("Configuration is valid. No healing required.")
            return result
        
        # ========================================
        # STEP 2: HEALING (if enabled and validation failed)
        # ========================================
        if auto_heal:
            result['healing_report']['attempted'] = True
            
            healed_yaml, remediation_logs = self.remediator.auto_fix(config_yaml, all_errors)
            result['healing_report']['logs'] = remediation_logs
            result['config'] = healed_yaml
            result['healed'] = healed_yaml != config_yaml
            
            # ========================================
            # STEP 3: RE-VALIDATION OF HEALED CONFIG
            # ========================================
            if result['healed']:
                healed_validation_report = self._run_validation_suite(healed_yaml)
                result['validation_report']['healed_validation'] = healed_validation_report
                
                healed_errors = self._extract_errors_from_report(healed_validation_report)
                result['final_valid'] = len(healed_errors) == 0
                
                if result['final_valid']:
                    result['success'] = True
                    remediation_logs.append("✓ Configuration healed and re-validated successfully!")
                else:
                    remediation_logs.append(
                        f"✗ Configuration healed but {len(healed_errors)} issues remain. "
                        "Manual intervention required."
                    )
                    result['healing_report']['remaining_issues'] = healed_errors
            else:
                remediation_logs.append("No automatic fixes could be applied.")
                result['final_valid'] = False
        else:
            result['healing_report']['logs'].append(
                "Auto-healing disabled. Configuration validation failed and manual fixes required."
            )
            result['final_valid'] = False
        
        return result
    
    def _run_validation_suite(self, config_yaml: str) -> Dict:
        """
        Run complete validation suite (schema, dependencies, conflicts)
        
        Returns:
            Comprehensive validation report with all test results
        """
        report = {
            'overall_status': 'PASSED',
            'tests': [],
            'total_errors': 0,
            'total_warnings': 0
        }
        
        try:
            config = yaml.safe_load(config_yaml)
        except Exception as e:
            report['overall_status'] = 'FAILED'
            report['tests'].append({
                'name': 'YAML Parse',
                'status': 'FAILED',
                'issues': [{
                    'severity': 'ERROR',
                    'message': f'Invalid YAML: {str(e)}'
                }]
            })
            return report
        
        # Test 1: Schema Validation
        is_valid, schema_issues = self.schema_validator.validate_workload_config(config_yaml)
        errors = [i for i in schema_issues if i.get('severity') == 'ERROR']
        warnings = [i for i in schema_issues if i.get('severity') == 'WARNING']
        
        report['tests'].append({
            'name': 'Schema Validation',
            'status': 'PASSED' if is_valid else 'FAILED',
            'issues': schema_issues,
            'error_count': len(errors),
            'warning_count': len(warnings)
        })
        
        if len(errors) > 0:
            report['overall_status'] = 'FAILED'
        report['total_errors'] += len(errors)
        report['total_warnings'] += len(warnings)
        
        # Test 2: Dependency Validation
        is_valid, dep_issues = self.dep_validator.validate_dependencies(config_yaml)
        errors = [i for i in dep_issues if i.get('severity') == 'ERROR']
        warnings = [i for i in dep_issues if i.get('severity') == 'WARNING']
        
        report['tests'].append({
            'name': 'Dependency Validation',
            'status': 'PASSED' if is_valid else 'FAILED',
            'issues': dep_issues,
            'error_count': len(errors),
            'warning_count': len(warnings)
        })
        
        if len(errors) > 0:
            report['overall_status'] = 'FAILED'
        report['total_errors'] += len(errors)
        report['total_warnings'] += len(warnings)
        
        # Test 3: Circular Dependency Check
        try:
            has_cycles, cycles = self.dep_validator.detect_circular_dependencies(
                config.get('workloads', {})
            )
            
            cycle_issues = [{
                'type': 'CIRCULAR_DEPENDENCY',
                'severity': 'ERROR',
                'message': f'Circular dependency detected: {" -> ".join(cycle)}'
            } for cycle in cycles]
            
            report['tests'].append({
                'name': 'Circular Dependency Check',
                'status': 'FAILED' if has_cycles else 'PASSED',
                'issues': cycle_issues,
                'error_count': len(cycle_issues) if has_cycles else 0
            })
            
            if has_cycles:
                report['overall_status'] = 'FAILED'
                report['total_errors'] += len(cycle_issues)
        except Exception as e:
            report['tests'].append({
                'name': 'Circular Dependency Check',
                'status': 'FAILED',
                'issues': [{
                    'severity': 'ERROR',
                    'message': f'Circular dependency check failed: {str(e)}'
                }],
                'error_count': 1
            })
            report['overall_status'] = 'FAILED'
            report['total_errors'] += 1
        
        # Test 4: Resource Conflict Detection
        try:
            conflicts = self.conflict_detector.check_port_conflicts(config.get('workloads', {}))
            
            conflict_issues = [{
                'type': 'RESOURCE_CONFLICT',
                'severity': 'WARNING',
                'message': f'Port conflict: {conflict}'
            } for conflict in conflicts]
            
            report['tests'].append({
                'name': 'Resource Conflict Detection',
                'status': 'FAILED' if conflicts else 'PASSED',
                'issues': conflict_issues,
                'warning_count': len(conflict_issues)
            })
            
            report['total_warnings'] += len(conflict_issues)
        except Exception as e:
            report['tests'].append({
                'name': 'Resource Conflict Detection',
                'status': 'FAILED',
                'issues': [{
                    'severity': 'WARNING',
                    'message': f'Conflict detection failed: {str(e)}'
                }],
                'warning_count': 1
            })
            report['total_warnings'] += 1
        
        return report
    
    def _extract_errors_from_report(self, validation_report: Dict) -> List[Dict]:
        """
        Extract all error-level issues from validation report
        
        Returns:
            List of error issues suitable for remediator input
        """
        errors = []
        for test in validation_report.get('tests', []):
            for issue in test.get('issues', []):
                if issue.get('severity') == 'ERROR':
                    errors.append(issue)
        return errors
