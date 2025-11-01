"""
Dependency Validator - Validates workload dependencies
"""
from typing import Dict, List, Set, Tuple
import yaml


class DependencyValidator:
    """Validates workload dependencies and detects issues"""
    
    def __init__(self, current_workloads: List[str] = None):
        """
        Args:
            current_workloads: List of currently deployed workload names
        """
        self.current_workloads = set(current_workloads or [])
        self.errors = []
    
    def validate_dependencies(self, config_yaml: str) -> Tuple[bool, List[Dict]]:
        """
        Validate all dependencies in configuration
        Returns: (is_valid, errors_list)
        """
        self.errors = []
        
        try:
            config = yaml.safe_load(config_yaml)
        except yaml.YAMLError:
            return False, [{
                'type': 'YAML_ERROR',
                'severity': 'ERROR',
                'message': 'Invalid YAML - cannot validate dependencies'
            }]
        
        workloads = config.get('workloads', {})
        new_workload_names = set(workloads.keys())
        all_available = self.current_workloads | new_workload_names
        
        # Check each workload's dependencies
        for workload_name, workload_config in workloads.items():
            dependencies = workload_config.get('dependencies', {})
            
            for dep_name in dependencies:
                # Check if dependency exists
                if dep_name not in all_available:
                    self.errors.append({
                        'type': 'MISSING_DEPENDENCY',
                        'severity': 'ERROR',
                        'workload': workload_name,
                        'dependency': dep_name,
                        'message': f'Dependency "{dep_name}" does not exist',
                        'recommendation': f'Create workload "{dep_name}" first or remove this dependency'
                    })
                
                # Check for self-dependency
                if dep_name == workload_name:
                    self.errors.append({
                        'type': 'SELF_DEPENDENCY',
                        'severity': 'ERROR',
                        'workload': workload_name,
                        'message': f'Workload "{workload_name}" cannot depend on itself'
                    })
        
        # Check for circular dependencies
        has_cycles, cycles = self.detect_circular_dependencies(workloads)
        if has_cycles:
            for cycle in cycles:
                cycle_path = ' -> '.join(cycle)
                self.errors.append({
                    'type': 'CIRCULAR_DEPENDENCY',
                    'severity': 'ERROR',
                    'message': f'Circular dependency detected: {cycle_path}',
                    'cycle': cycle,
                    'recommendation': 'Break the circular dependency by removing one of the dependencies'
                })
        
        is_valid = len(self.errors) == 0
        return is_valid, self.errors
    
    def detect_circular_dependencies(self, workloads: Dict) -> Tuple[bool, List[List[str]]]:
        """
        Detect circular dependencies using DFS
        Returns: (has_cycles, list_of_cycles)
        """
        # Build adjacency list (dependency graph)
        graph = {}
        for workload_name, workload_config in workloads.items():
            deps = workload_config.get('dependencies', {})
            graph[workload_name] = list(deps.keys())
        
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node: str, path: List[str]) -> bool:
            """DFS to detect cycles"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in graph:
                    # Dependency doesn't exist in this config, skip
                    continue
                
                if neighbor not in visited:
                    if dfs(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True
            
            rec_stack.remove(node)
            return False
        
        # Check all nodes for cycles
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return len(cycles) > 0, cycles