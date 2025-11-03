"""
Locust Load Testing for Configuration Validator
Non-Functional Testing Tool: Performance & Scalability

locust -f tests/locust/locustfile.py \
  --host=http://localhost:5001 \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 60s \
  --html report_locust.html \
  --csv report_locust
"""
from locust import HttpUser, task, between
import json


class ConfigValidatorUser(HttpUser):
    """Simulates users validating configurations"""
    
    # Wait 1-3 seconds between tasks (simulates real user behavior)
    wait_time = between(1, 3)
    
    @task(5)  # Weight: 5 (runs 5x more often)
    def validate_simple_config(self):
        """Test: Simple valid configuration"""
        config = """
workloads:
  nginx:
    runtime: podman
    agent: agent_A
        """
        self.client.post(
            "/api/validate-config",
            json={"config": config},
            name="Simple Valid Config"
        )
    
    @task(3)  # Weight: 3
    def validate_complex_config(self):
        """Test: Configuration with dependencies"""
        config = """
workloads:
  frontend:
    runtime: podman
    agent: agent_A
    dependencies:
      backend: {}
  backend:
    runtime: podman
    agent: agent_A
    dependencies:
      database: {}
  database:
    runtime: podman
    agent: agent_A
        """
        self.client.post(
            "/api/validate-config",
            json={"config": config},
            name="Complex Config with Dependencies"
        )
    
    @task(2)  # Weight: 2
    def validate_invalid_config(self):
        """Test: Invalid configuration (error handling)"""
        config = """
workloads:
  nginx:
    runtime: invalid_runtime
        """
        self.client.post(
            "/api/validate-config",
            json={"config": config},
            name="Invalid Config"
        )
    
    @task(1)  # Weight: 1
    def validate_large_config(self):
        """Test: Large configuration (50 workloads)"""
        workloads = "\n".join([
            f"  workload_{i}:\n    runtime: podman\n    agent: agent_A"
            for i in range(50)
        ])
        config = f"workloads:\n{workloads}"
        
        self.client.post(
            "/api/validate-config",
            json={"config": config},
            name="Large Config (50 workloads)"
        )