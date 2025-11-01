"""
Conflict Detector - Detects resource conflicts (ports, volumes, etc.)
"""
import re
from typing import Dict, List, Tuple
import yaml


class ResourceConflictDetector:
    """Detects resource conflicts between workloads"""
    
    def __init__(self, current_workloads: List[Dict] = None):
        """
        Args:
            current_workloads: List of currently deployed workloads
                               Each workload should have 'name' and 'runtimeConfig'
        """
        self.current_workloads = current_workloads or []
        self.errors = []
    
    def detect_conflicts(self, config_yaml: str) -> Tuple[bool, List[Dict]]:
        """
        Detect all resource conflicts
        Returns: (has_conflicts, errors_list)
        """
        self.errors = []
        
        try:
            config = yaml.safe_load(config_yaml)
        except yaml.YAMLError:
            return False, [{
                'type': 'YAML_ERROR',
                'severity': 'ERROR',
                'message': 'Invalid YAML - cannot check conflicts'
            }]
        
        # Check port conflicts
        self._check_port_conflicts(config)
        
        has_conflicts = len(self.errors) > 0
        return not has_conflicts, self.errors
    
    def _check_port_conflicts(self, config: Dict):
        """Check for port conflicts"""
        port_map = {}  # port -> workload_name
        
        # Map existing workload ports
        for workload in self.current_workloads:
            workload_name = workload.get('name', 'unknown')
            runtime_config = workload.get('runtimeConfig', '')
            ports = self._extract_ports(runtime_config)
            
            for port in ports:
                port_map[port] = workload_name
        
        # Check new workloads for conflicts
        new_workloads = config.get('workloads', {})
        for workload_name, workload_config in new_workloads.items():
            runtime_config = workload_config.get('runtimeConfig', '')
            ports = self._extract_ports(runtime_config)
            
            for port in ports:
                if port in port_map and port_map[port] != workload_name:
                    self.errors.append({
                        'type': 'PORT_CONFLICT',
                        'severity': 'ERROR',
                        'workload': workload_name,
                        'port': port,
                        'conflicting_workload': port_map[port],
                        'message': f'Port {port} is already used by workload "{port_map[port]}"',
                        'recommendation': f'Use a different port or stop workload "{port_map[port]}"'
                    })
                else:
                    # Add to map to check conflicts within new config
                    port_map[port] = workload_name
    
    def _extract_ports(self, runtime_config: str) -> List[int]:
        """
        Extract host port numbers from runtime configuration
        Handles formats like:
        - "-p 8080:80"
        - 'commandOptions: ["-p", "8080:80"]'
        - "8080:80"
        """
        ports = []
        
        # Pattern to match port mappings: host_port:container_port
        patterns = [
            r'-p["\s]+(\d+):\d+',  # -p 8080:80 or -p "8080:80"
            r'"(\d+):\d+"',         # "8080:80"
            r'\s(\d+):\d+\s',       # 8080:80
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, runtime_config)
            ports.extend([int(m) for m in matches])
        
        return list(set(ports))  # Remove duplicates