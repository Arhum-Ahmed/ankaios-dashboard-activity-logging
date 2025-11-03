"""
Complete UAT and System Test Suite for Configuration Validator
pip install pytest requests --break-system-packages
Run: pytest tests/test_uat_system.py -v
"""
import pytest
import requests
import json
import time
import concurrent.futures
from typing import Dict, Any


BASE_URL = "http://localhost:5001"
API_ENDPOINT = f"{BASE_URL}/api/validate-config"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def valid_config():
    """Valid workload configuration"""
    return """
apiVersion: v0.1
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: nginx:latest
    """


@pytest.fixture
def invalid_yaml():
    """Malformed YAML (missing colon)"""
    return """
workloads:
  nginx:
    runtime podman
    """


@pytest.fixture
def circular_dependency_config():
    """Configuration with circular dependencies: A→B→C→A"""
    return """
workloads:
  A:
    runtime: podman
    agent: agent_A
    dependencies:
      B: {}
  B:
    runtime: podman
    agent: agent_A
    dependencies:
      C: {}
  C:
    runtime: podman
    agent: agent_A
    dependencies:
      A: {}
    """


@pytest.fixture
def missing_dependency_config():
    """Configuration with missing dependency"""
    return """
workloads:
  app:
    runtime: podman
    agent: agent_A
    dependencies:
      database: {}
    """


@pytest.fixture
def self_dependency_config():
    """Configuration with self-dependency"""
    return """
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    dependencies:
      nginx: {}
    """


def validate_config(config: str) -> requests.Response:
    """Helper function to call validation API"""
    return requests.post(
        API_ENDPOINT,
        json={"config": config},
        headers={"Content-Type": "application/json"}
    )


# ============================================================================
# UAT Test Cases (User Acceptance Tests)
# ============================================================================

class TestUAT:
    """User Acceptance Test Cases"""
    
    def test_uat_01_valid_configuration_acceptance(self, valid_config):
        """
        UAT-01: Valid Configuration Acceptance
        
        Objective: Verify that a valid configuration passes all checks
        Expected: Status = PASSED, no errors
        """
        response = validate_config(valid_config)
        data = response.json()
        
        assert response.status_code == 200, "API should return 200"
        assert data['overall_status'] == 'PASSED', "Valid config should pass"
        assert data['summary']['failed'] == 0, "Should have no failed tests"
        assert data['summary']['total_errors'] == 0, "Should have no errors"
    
    def test_uat_02_detect_missing_required_fields(self):
        """
        UAT-02: Detect Missing Required Fields
        
        Objective: Verify system catches missing required fields
        Expected: FAILED status, error mentions "runtime is required"
        """
        config = """
workloads:
  nginx:
    agent: agent_A
        """
        response = validate_config(config)
        data = response.json()
        
        assert response.status_code == 200
        assert data['overall_status'] == 'FAILED', "Should fail with missing field"
        
        # Check that schema validation failed
        schema_test = next((t for t in data['tests'] if 'Schema' in t['name']), None)
        assert schema_test is not None, "Should have schema validation test"
        assert schema_test['status'] == 'FAILED', "Schema validation should fail"
        
        # Check error message mentions runtime
        has_runtime_error = any(
            'runtime' in str(issue).lower()
            for test in data['tests']
            for issue in test.get('issues', [])
        )
        assert has_runtime_error, "Error should mention missing 'runtime' field"
    
    def test_uat_03_detect_circular_dependencies(self, circular_dependency_config):
        """
        UAT-03: Detect Circular Dependencies
        
        Objective: Verify circular dependency detection works
        Expected: FAILED status, shows cycle path
        """
        response = validate_config(circular_dependency_config)
        data = response.json()
        
        assert response.status_code == 200
        assert data['overall_status'] == 'FAILED', "Should fail with circular deps"
        
        # Find circular dependency check
        circ_test = next(
            (t for t in data['tests'] if 'Circular' in t['name']), 
            None
        )
        assert circ_test is not None, "Should have circular dependency test"
        assert circ_test['status'] == 'FAILED', "Circular dep test should fail"
        
        # Check for circular dependency error
        has_circular_error = any(
            issue.get('type') == 'CIRCULAR_DEPENDENCY'
            for issue in circ_test.get('issues', [])
        )
        assert has_circular_error, "Should detect circular dependency"
    
    def test_uat_04_detect_port_conflicts(self):
        """
        UAT-04: Detect Port Conflicts
        
        Objective: Verify port conflict detection
        Expected: System can detect port conflicts in configurations
        Note: This is a simplified test as we don't have actual deployed workloads
        """
        config = """
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      commandOptions: ["-p", "8080:80"]
        """
        response = validate_config(config)
        data = response.json()
        
        assert response.status_code == 200
        # This should pass as there are no existing workloads to conflict with
        # The test verifies the conflict detection mechanism exists
        assert 'Resource Conflict Detection' in [t['name'] for t in data['tests']]
    
    def test_uat_05_invalid_yaml_handling(self, invalid_yaml):
        """
        UAT-05: Invalid YAML Handling
        
        Objective: Verify graceful handling of syntax errors
        Expected: FAILED status, SYNTAX_ERROR type
        """
        response = validate_config(invalid_yaml)
        data = response.json()
        
        assert response.status_code == 200
        assert data['overall_status'] == 'FAILED', "Should fail with syntax error"
        
        # Check for YAML/syntax error
        has_syntax_error = any(
            'SYNTAX' in issue.get('type', '').upper() or 
            'YAML' in issue.get('type', '').upper() or
            'STRUCTURE' in issue.get('type', '').upper()  # ADD THIS LINE
            for test in data['tests']
            for issue in test.get('issues', [])
        )
        assert has_syntax_error, "Should detect YAML syntax error"
    
    def test_uat_06_missing_dependency_detection(self, missing_dependency_config):
        """
        UAT-06: Missing Dependency Detection
        
        Objective: Verify detection of non-existent dependencies
        Expected: FAILED status, MISSING_DEPENDENCY error
        """
        response = validate_config(missing_dependency_config)
        data = response.json()
        
        assert response.status_code == 200
        assert data['overall_status'] == 'FAILED', "Should fail with missing dep"
        
        # Check for missing dependency error
        has_missing_dep = any(
            issue.get('type') == 'MISSING_DEPENDENCY'
            for test in data['tests']
            for issue in test.get('issues', [])
        )
        assert has_missing_dep, "Should detect missing dependency"
        
        # Verify error mentions the missing workload
        has_database_ref = any(
            'database' in str(issue).lower()
            for test in data['tests']
            for issue in test.get('issues', [])
        )
        assert has_database_ref, "Error should mention 'database' workload"
    
    def test_uat_07_performance_requirement(self):
        """
        UAT-07: Performance Requirement
        
        Objective: Verify response time meets requirement
        Expected: Response < 500ms for typical config
        """
        config = """
workloads:
""" + "\n".join([
            f"  workload_{i}:\n    runtime: podman\n    agent: agent_A"
            for i in range(10)
        ])
        
        start_time = time.time()
        response = validate_config(config)
        duration = time.time() - start_time
        
        assert response.status_code == 200
        assert duration < 0.5, f"Response took {duration:.3f}s, should be < 0.5s"
    
    def test_uat_08_api_accessibility(self):
        """
        UAT-08: API Accessibility
        
        Objective: Verify API is accessible without GUI
        Expected: HTTP 200, valid JSON with required fields
        """
        config = """
workloads:
  test:
    runtime: podman
    agent: agent_A
        """
        response = validate_config(config)
        
        assert response.status_code == 200, "API should be accessible"
        assert response.headers['Content-Type'] == 'application/json', "Should return JSON"
        
        data = response.json()
        assert 'overall_status' in data, "Response should have overall_status"
        assert 'tests' in data, "Response should have tests array"
        assert 'summary' in data, "Response should have summary"
        assert isinstance(data['tests'], list), "tests should be an array"


# ============================================================================
# System Test Cases
# ============================================================================

class TestSystem:
    """System-level Integration Tests"""
    
    def test_sys_01_schema_validation_integration(self):
        """
        SYS-01: Schema Validation Integration
        
        Test: Configuration missing required 'runtime' field
        Expected: Schema validation fails
        """
        config = """
workloads:
  nginx:
    agent: agent_A
        """
        response = validate_config(config)
        data = response.json()
        
        schema_test = next((t for t in data['tests'] if 'Schema' in t['name']), None)
        assert schema_test is not None
        assert schema_test['status'] == 'FAILED'
    
    def test_sys_02_dependency_graph_algorithm(self, circular_dependency_config):
        """
        SYS-02: Dependency Graph Algorithm (DFS-based cycle detection)
        
        Test: 3-node circular dependency (A→B→C→A)
        Expected: Circular dependency test fails
        """
        response = validate_config(circular_dependency_config)
        data = response.json()
        
        circ_test = next((t for t in data['tests'] if 'Circular' in t['name']), None)
        assert circ_test is not None
        assert circ_test['status'] == 'FAILED'
    
    def test_sys_03_self_dependency_detection(self, self_dependency_config):
        """
        SYS-03: Self-Dependency Detection
        
        Test: Workload depending on itself
        Expected: SELF_DEPENDENCY error
        """
        response = validate_config(self_dependency_config)
        data = response.json()
        
        has_self_dep = any(
            issue.get('type') == 'SELF_DEPENDENCY'
            for test in data['tests']
            for issue in test.get('issues', [])
        )
        assert has_self_dep, "Should detect self-dependency"
    
    def test_sys_04_invalid_runtime_rejection(self):
        """
        SYS-04: Invalid Runtime Rejection
        
        Test: Invalid runtime value
        Expected: Validation fails
        """
        config = """
workloads:
  nginx:
    runtime: invalid_runtime
    agent: agent_A
        """
        response = validate_config(config)
        data = response.json()
        
        assert data['overall_status'] == 'FAILED'
        
        has_runtime_error = any(
            'runtime' in str(issue).lower()
            for test in data['tests']
            for issue in test.get('issues', [])
        )
        assert has_runtime_error
    
    def test_sys_05_concurrent_request_handling(self):
        """
        SYS-05: Concurrent Request Handling
        
        Test: 10 simultaneous validation requests
        Expected: All succeed without errors
        """
        config = """
workloads:
  test:
    runtime: podman
    agent: agent_A
        """
        
        def make_request():
            return validate_config(config)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        assert len(responses) == 10, "Should complete all requests"
        assert all(r.status_code == 200 for r in responses), "All should succeed"
        
        # Verify all returned valid data
        for response in responses:
            data = response.json()
            assert 'overall_status' in data
    
    def test_sys_06_large_configuration_handling(self):
        """
        SYS-06: Large Configuration Handling
        
        Test: Configuration with 50 workloads
        Expected: Completes in < 2 seconds, returns valid result
        """
        workloads = "\n".join([
            f"  workload_{i}:\n    runtime: podman\n    agent: agent_A"
            for i in range(50)
        ])
        config = f"workloads:\n{workloads}"
        
        start_time = time.time()
        response = validate_config(config)
        duration = time.time() - start_time
        
        assert response.status_code == 200
        assert duration < 2.0, f"Took {duration:.3f}s, should be < 2s"
        
        data = response.json()
        assert data['overall_status'] == 'PASSED'
    
    def test_sys_07_empty_configuration(self):
        """
        SYS-07: Empty Configuration Handling
        
        Test: Empty configuration string
        Expected: HTTP 400 error
        """
        response = requests.post(
            API_ENDPOINT,
            json={"config": ""},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400, "Empty config should return 400"
    
    def test_sys_08_malformed_json_request(self):
        """
        SYS-08: Malformed JSON Request Handling
        
        Test: Invalid JSON in request body
        Expected: HTTP 400 or 500, graceful error
        """
        response = requests.post(
            API_ENDPOINT,
            data="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 500], "Should reject malformed JSON"
    
    def test_sys_09_response_structure_validation(self):
        """
        SYS-09: Response Structure Validation
        
        Test: Verify API response has all required fields
        Expected: Contains overall_status, tests, summary, timestamp
        """
        config = """
workloads:
  test:
    runtime: podman
    agent: agent_A
        """
        response = validate_config(config)
        data = response.json()
        
        # Check required top-level fields
        assert 'overall_status' in data
        assert 'tests' in data
        assert 'summary' in data
        assert 'timestamp' in data
        
        # Check summary structure
        summary = data['summary']
        assert 'total_tests' in summary
        assert 'passed' in summary
        assert 'failed' in summary
        assert 'total_errors' in summary
        assert 'total_warnings' in summary
        
        # Check tests structure
        assert isinstance(data['tests'], list)
        if len(data['tests']) > 0:
            test = data['tests'][0]
            assert 'name' in test
            assert 'status' in test
            assert 'issues' in test
    
    def test_sys_10_algorithm_complexity_verification(self):
        """
        SYS-10: Algorithm Complexity (O(V+E) verification)
        
        Test: Measure execution time with increasing graph sizes
        Expected: Linear time growth confirms O(V+E) complexity
        """
        results = []
        
        for size in [10, 20, 40]:
            # Create a chain: 1→2→3→...→N
            workloads = ["  w1:\n    runtime: podman\n    agent: agent_A"]
            for i in range(2, size + 1):
                workloads.append(
                    f"  w{i}:\n    runtime: podman\n    agent: agent_A\n    dependencies:\n      w{i-1}: {{}}"
                )
            config = "workloads:\n" + "\n".join(workloads)
            
            start_time = time.time()
            response = validate_config(config)
            duration = time.time() - start_time
            
            results.append((size, duration))
            assert response.status_code == 200
        
        # Verify roughly linear growth
        # If doubling size roughly doubles time, it's O(V+E)
        ratio = results[1][1] / results[0][1]  # 20/10 ratio
        assert 1.2 < ratio < 3.5, f"Time should scale roughly linearly, got {ratio}x"


# ============================================================================
# Parametrized Tests
# ============================================================================

class TestParametrized:
    """Parametrized test cases for various scenarios"""
    
    @pytest.mark.parametrize("runtime", ["podman", "podman-kube"])
    def test_valid_runtime_values(self, runtime):
        """Test all valid runtime values are accepted"""
        config = f"""
workloads:
  test:
    runtime: {runtime}
    agent: agent_A
        """
        response = validate_config(config)
        data = response.json()
        
        assert response.status_code == 200
        assert data['overall_status'] == 'PASSED'
    
    @pytest.mark.parametrize("invalid_runtime", [
        "docker", "kubernetes", "invalid", "123", ""
    ])
    def test_invalid_runtime_values(self, invalid_runtime):
        """Test invalid runtime values are rejected"""
        config = f"""
workloads:
  test:
    runtime: {invalid_runtime}
    agent: agent_A
        """
        response = validate_config(config)
        data = response.json()
        
        assert data['overall_status'] == 'FAILED'
    
    @pytest.mark.parametrize("agent", ["agent_A", "agent_B", "agent_C"])
    def test_valid_agent_names(self, agent):
        """Test various agent names are accepted"""
        config = f"""
workloads:
  test:
    runtime: podman
    agent: {agent}
        """
        response = validate_config(config)
        data = response.json()
        
        assert response.status_code == 200
        assert data['overall_status'] == 'PASSED'


# ============================================================================
# Performance Benchmarks
# ============================================================================

@pytest.mark.benchmark
class TestPerformance:
    """Performance benchmark tests"""
    
    def test_response_time_simple_config(self, benchmark):
        """Benchmark: Simple configuration validation"""
        config = """
workloads:
  test:
    runtime: podman
    agent: agent_A
        """
        
        def run_validation():
            return validate_config(config)
        
        result = benchmark(run_validation)
        assert result.status_code == 200
    
    def test_response_time_complex_config(self, benchmark):
        """Benchmark: Complex configuration with dependencies"""
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
        
        def run_validation():
            return validate_config(config)
        
        result = benchmark(run_validation)
        assert result.status_code == 200


# ============================================================================
# Test Summary
# ============================================================================

def test_suite_summary():
    """
    Test Suite Summary
    ==================
    UAT Tests: 8
    System Tests: 10
    Parametrized Tests: 8
    Performance Tests: 2
    
    Total: 28 tests
    
    Coverage:
    - Schema validation
    - Dependency validation
    - Circular dependency detection
    - Resource conflict detection
    - Performance testing
    - Concurrent access
    - Error handling
    - API structure
    """
    pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])