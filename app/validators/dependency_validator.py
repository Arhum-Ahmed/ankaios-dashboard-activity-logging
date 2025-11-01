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
        except yaml.YAMLError as e:
            return False, [{
                'type': 'YAML_ERROR',
                'severity': 'ERROR',
                'message': f'Invalid YAML syntax: {str(e)}'
            }]
        
        # ADD THIS CHECK:
        if not isinstance(config, dict):
            return False, [{
                'type': 'INVALID_CONFIG',
                'severity': 'ERROR',
                'message': f'Configuration must be a YAML object/dictionary, got {type(config).__name__}'
            }]
        
        workloads = config.get('workloads', {})
        new_workload_names = set(workloads.keys())
        all_available = self.current_workloads | new_workload_names
        
        # ... rest of the function
    
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