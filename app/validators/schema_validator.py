"""
Schema Validator - Validates workload configuration against schema
"""
import yaml
import re
from typing import Tuple, List, Dict, Any


class ConfigurationValidator:
    """Validates Ankaios workload configurations"""
    
    VALID_RUNTIMES = ['podman', 'docker', 'podman-kube']
    VALID_RESTART_POLICIES = ['NEVER', 'ALWAYS', 'ON_FAILURE']
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_workload_config(self, config_yaml: str) -> Tuple[bool, List[Dict]]:
        """
        Main validation method
        Returns: (is_valid, errors_and_warnings_list)
        """
        self.errors = []
        self.warnings = []
        
        # Step 1: Parse YAML
        try:
            config = yaml.safe_load(config_yaml)
        except yaml.YAMLError as e:
            self.errors.append({
                'type': 'SYNTAX_ERROR',
                'severity': 'ERROR',
                'message': f'Invalid YAML syntax: {str(e)}',
                'line': getattr(e, 'problem_mark', None)
            })
            return False, self.errors
        
        # Step 2: Validate structure
        if not isinstance(config, dict):
            self.errors.append({
                'type': 'STRUCTURE_ERROR',
                'severity': 'ERROR',
                'message': 'Configuration must be a dictionary/object'
            })
            return False, self.errors
        
        # Step 3: Validate workloads section
        if 'workloads' not in config:
            self.errors.append({
                'type': 'MISSING_SECTION',
                'severity': 'ERROR',
                'message': 'Configuration must have a "workloads" section'
            })
            return False, self.errors
        
        workloads = config.get('workloads', {})
        
        # Step 4: Validate each workload
        for workload_name, workload_config in workloads.items():
            self._validate_workload(workload_name, workload_config)
        
        # Combine errors and warnings
        all_issues = self.errors + self.warnings
        is_valid = len(self.errors) == 0
        
        return is_valid, all_issues
    
    def _validate_workload(self, name: str, config: Dict[str, Any]):
        """Validate individual workload configuration"""
        
        # Check naming conventions
        if not name:
            self.errors.append({
                'type': 'NAMING_ERROR',
                'severity': 'ERROR',
                'workload': name,
                'message': 'Workload name cannot be empty'
            })
        
        if ' ' in name:
            self.errors.append({
                'type': 'NAMING_ERROR',
                'severity': 'ERROR',
                'workload': name,
                'message': f'Workload name "{name}" contains spaces'
            })
        
        if not name.islower() and name:
            self.warnings.append({
                'type': 'NAMING_WARNING',
                'severity': 'WARNING',
                'workload': name,
                'message': f'Workload name "{name}" should be lowercase (convention)'
            })
        
        # Check required fields
        if 'runtime' not in config:
            self.errors.append({
                'type': 'MISSING_FIELD',
                'severity': 'ERROR',
                'workload': name,
                'message': 'Field "runtime" is required'
            })
        else:
            runtime = config['runtime']
            if runtime not in self.VALID_RUNTIMES:
                self.errors.append({
                    'type': 'INVALID_VALUE',
                    'severity': 'ERROR',
                    'workload': name,
                    'message': f'Invalid runtime "{runtime}". Must be one of: {", ".join(self.VALID_RUNTIMES)}'
                })
        
        if 'agent' not in config:
            self.errors.append({
                'type': 'MISSING_FIELD',
                'severity': 'ERROR',
                'workload': name,
                'message': 'Field "agent" is required'
            })
        
        # Check restart policy if present
        if 'restartPolicy' in config:
            policy = config['restartPolicy']
            if policy not in self.VALID_RESTART_POLICIES:
                self.errors.append({
                    'type': 'INVALID_VALUE',
                    'severity': 'ERROR',
                    'workload': name,
                    'message': f'Invalid restartPolicy "{policy}". Must be one of: {", ".join(self.VALID_RESTART_POLICIES)}'
                })
        
        # Check runtime config
        if 'runtimeConfig' not in config:
            self.warnings.append({
                'type': 'MISSING_FIELD',
                'severity': 'WARNING',
                'workload': name,
                'message': 'No runtimeConfig specified'
            })
        else:
            runtime_config = config['runtimeConfig']
            
            # Check for image specification
            if 'image' not in runtime_config.lower():
                self.warnings.append({
                    'type': 'MISSING_IMAGE',
                    'severity': 'WARNING',
                    'workload': name,
                    'message': 'No container image specified in runtimeConfig',
                    'recommendation': 'Add "image: <container-image>" to runtimeConfig'
                })
    
    def validate_file(self, filepath: str) -> Tuple[bool, List[Dict]]:
        """Validate a YAML file"""
        try:
            with open(filepath, 'r') as f:
                config_yaml = f.read()
            return self.validate_workload_config(config_yaml)
        except FileNotFoundError:
            return False, [{
                'type': 'FILE_ERROR',
                'severity': 'ERROR',
                'message': f'File not found: {filepath}'
            }]
        except Exception as e:
            return False, [{
                'type': 'FILE_ERROR',
                'severity': 'ERROR',
                'message': f'Error reading file: {str(e)}'
            }]