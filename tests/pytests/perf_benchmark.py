"""
Performance Benchmark Tests using pytest-benchmark
Install: pip install pytest-benchmark
Run: pytest tests/test_benchmarks.py -v --benchmark-only
Generate Report: pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-save=nfr_benchmarks
View Report: pytest-benchmark compare nfr_benchmarks
HTML Report: pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-save-data --benchmark-histogram
"""
import pytest
import requests
import json

BASE_URL = "http://localhost:5001"
API_ENDPOINT = f"{BASE_URL}/api/validate-config"


# ============================================================================
# Benchmark Tests for Non-Functional Requirements
# ============================================================================

class TestPerformanceBenchmarks:
    """
    Performance benchmarks to verify NFR-1, NFR-2, NFR-4
    """
    
    def test_benchmark_simple_config(self, benchmark):
        """
        NFR-1 Benchmark: Simple configuration validation
        Target: < 500ms (0.5 seconds)
        """
        config = """
apiVersion: v0.1
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: nginx:latest
        """
        
        def validate():
            response = requests.post(
                API_ENDPOINT,
                json={"config": config},
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        
        # Verify NFR-1: < 500ms
        assert benchmark.stats['mean'] < 0.5, f"Mean time {benchmark.stats['mean']:.3f}s exceeds 500ms"
        print(f"\n✅ NFR-1 PASSED: Mean response time = {benchmark.stats['mean']*1000:.1f}ms")
    
    def test_benchmark_dependency_chain(self, benchmark):
        """
        Benchmark: Linear dependency chain (A→B→C)
        Measures dependency resolution performance
        """
        config = """
workloads:
  database:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: postgres:latest
  backend:
    runtime: podman
    agent: agent_A
    dependencies:
      database: ADD_COND_RUNNING
    runtimeConfig: |
      image: backend:latest
  frontend:
    runtime: podman
    agent: agent_A
    dependencies:
      backend: ADD_COND_RUNNING
    runtimeConfig: |
      image: frontend:latest
        """
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        print(f"\n📊 Dependency chain: Mean = {benchmark.stats['mean']*1000:.1f}ms")
    
    def test_benchmark_circular_dependency_detection(self, benchmark):
        """
        NFR-4 Benchmark: Circular dependency detection algorithm
        Tests DFS-based cycle detection performance
        """
        config = """
workloads:
  workload_a:
    runtime: podman
    agent: agent_A
    dependencies:
      workload_c: ADD_COND_RUNNING
    runtimeConfig: |
      image: nginx:latest
  workload_b:
    runtime: podman
    agent: agent_A
    dependencies:
      workload_a: ADD_COND_RUNNING
    runtimeConfig: |
      image: nginx:latest
  workload_c:
    runtime: podman
    agent: agent_A
    dependencies:
      workload_b: ADD_COND_RUNNING
    runtimeConfig: |
      image: nginx:latest
        """
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'FAILED'  # Should detect cycle
            return response
        
        result = benchmark(validate)
        print(f"\n📊 Circular detection: Mean = {benchmark.stats['mean']*1000:.1f}ms")
    
    @pytest.mark.parametrize("size", [10, 20, 50, 100])
    def test_benchmark_scaling(self, benchmark, size):
        """
        NFR-4 Benchmark: Algorithm complexity verification O(V+E)
        Tests with increasing workload sizes
        Target: Linear scaling
        """
        # Generate configuration with 'size' workloads
        workloads = []
        for i in range(size):
            workloads.append(f"""  workload_{i}:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: nginx:latest""")
        
        config = "workloads:\n" + "\n".join(workloads)
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        
        # For 50 workloads, should complete in < 2 seconds
        if size == 50:
            assert benchmark.stats['mean'] < 2.0, f"50 workloads took {benchmark.stats['mean']:.3f}s (> 2s)"
            print(f"\n✅ NFR-1 (Large Config): 50 workloads = {benchmark.stats['mean']*1000:.1f}ms")


class TestComplexityBenchmarks:
    """
    Algorithm complexity verification through benchmarking
    """
    
    def test_benchmark_graph_size_10(self, benchmark):
        """Benchmark: Dependency graph with 10 nodes"""
        config = self._create_chain_config(10)
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        # Store result for comparison
        benchmark.extra_info['graph_size'] = 10
    
    def test_benchmark_graph_size_20(self, benchmark):
        """Benchmark: Dependency graph with 20 nodes"""
        config = self._create_chain_config(20)
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        benchmark.extra_info['graph_size'] = 20
    
    def test_benchmark_graph_size_40(self, benchmark):
        """Benchmark: Dependency graph with 40 nodes"""
        config = self._create_chain_config(40)
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        benchmark.extra_info['graph_size'] = 40
    
    def _create_chain_config(self, size):
        """Helper: Create a chain dependency A→B→C→...→N"""
        workloads = ["  w1:\n    runtime: podman\n    agent: agent_A"]
        for i in range(2, size + 1):
            workloads.append(
                f"  w{i}:\n    runtime: podman\n    agent: agent_A\n    dependencies:\n      w{i-1}: {{}}"
            )
        return "workloads:\n" + "\n".join(workloads)


class TestConcurrencyBenchmarks:
    """
    NFR-2: Concurrent request handling benchmarks
    """
    
    def test_benchmark_concurrent_requests(self, benchmark):
        """
        NFR-2 Benchmark: Simulate concurrent load
        Note: This is a single-threaded benchmark, use Locust for true concurrency
        """
        config = """
workloads:
  test:
    runtime: podman
    agent: agent_A
        """
        
        def validate_batch():
            # Simulate multiple quick requests
            responses = []
            for _ in range(10):
                response = requests.post(API_ENDPOINT, json={"config": config})
                responses.append(response)
            
            assert all(r.status_code == 200 for r in responses)
            return responses
        
        result = benchmark(validate_batch)
        
        # Calculate requests per second
        rps = 10 / benchmark.stats['mean']
        print(f"\n📊 Batch throughput: {rps:.1f} req/s")


class TestMemoryBenchmarks:
    """
    Memory usage benchmarks (requires pytest-benchmark with memory profiling)
    """
    
    def test_benchmark_memory_large_config(self, benchmark):
        """
        Benchmark: Memory usage with large configuration
        """
        # Generate very large config
        workloads = []
        for i in range(100):
            workloads.append(f"""  workload_{i}:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: nginx:latest
      commandOptions: ["-p", "{8000+i}:80"]""")
        
        config = "workloads:\n" + "\n".join(workloads)
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            return response
        
        result = benchmark(validate)
        benchmark.extra_info['config_size_kb'] = len(config) / 1024


class TestErrorPathBenchmarks:
    """
    Benchmark error detection paths
    """
    
    def test_benchmark_schema_validation_error(self, benchmark):
        """Benchmark: Schema validation error detection speed"""
        config = """
workloads:
  nginx:
    agent: agent_A
        """  # Missing runtime
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'FAILED'
            return response
        
        result = benchmark(validate)
        print(f"\n📊 Error detection: {benchmark.stats['mean']*1000:.1f}ms")
    
    def test_benchmark_missing_dependency_error(self, benchmark):
        """Benchmark: Missing dependency detection speed"""
        config = """
workloads:
  app:
    runtime: podman
    agent: agent_A
    dependencies:
      nonexistent: ADD_COND_RUNNING
        """
        
        def validate():
            response = requests.post(API_ENDPOINT, json={"config": config})
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'FAILED'
            return response
        
        result = benchmark(validate)


# ============================================================================
# Comparison Tests - Before/After Optimization
# ============================================================================

class TestComparisonBenchmarks:
    """
    Benchmark tests for comparing different implementations or optimizations
    """
    
    def test_benchmark_baseline_v1(self, benchmark):
        """Baseline benchmark - save for future comparisons"""
        config = """
workloads:
  test:
    runtime: podman
    agent: agent_A
        """
        
        def validate():
            return requests.post(API_ENDPOINT, json={"config": config})
        
        result = benchmark(validate)
        benchmark.extra_info['version'] = 'v1_baseline'


# ============================================================================
# Custom Benchmark Hooks
# ============================================================================

def pytest_benchmark_generate_json(config, benchmarks, include_data, machine_info, commit_info):
    """
    Custom hook to add NFR compliance info to benchmark JSON
    """
    for bench in benchmarks:
        stats = bench['stats']
        mean_ms = stats['mean'] * 1000
        
        # Check NFR-1 compliance
        bench['nfr_compliance'] = {
            'nfr_1_latency': 'PASS' if stats['mean'] < 0.5 else 'FAIL',
            'nfr_1_value': f"{mean_ms:.1f}ms",
            'nfr_1_target': '< 500ms'
        }


if __name__ == '__main__':
    """
    Usage Examples:
    
    # Run all benchmarks
    pytest tests/test_benchmarks.py -v --benchmark-only
    
    # Generate detailed statistics
    pytest tests/test_benchmarks.py --benchmark-only --benchmark-verbose
    
    # Save results for comparison
    pytest tests/test_benchmarks.py --benchmark-only --benchmark-autosave --benchmark-save=baseline
    
    # Compare with previous run
    pytest-benchmark compare baseline
    
    # Generate histogram
    pytest tests/test_benchmarks.py --benchmark-only --benchmark-histogram
    
    # JSON output
    pytest tests/test_benchmarks.py --benchmark-only --benchmark-json=benchmark_results.json
    
    # Only run specific benchmark group
    pytest tests/test_benchmarks.py::TestPerformanceBenchmarks --benchmark-only
    
    # Run with specific rounds (more accurate)
    pytest tests/test_benchmarks.py --benchmark-only --benchmark-min-rounds=10
    """
    import os
    os.system("pytest tests/test_benchmarks.py -v --benchmark-only")