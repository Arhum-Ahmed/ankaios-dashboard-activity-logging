"""
Unit tests for validators
Run with: pytest tests/
"""
import pytest
from app.validators.schema_validator import ConfigurationValidator
from app.validators.dependency_validator import DependencyValidator
from app.validators.conflict_detector import ResourceConflictDetector


class TestSchemaValidator:
    
    def test_valid_config(self):
        """Test that valid configuration passes"""
        validator = ConfigurationValidator()
        valid_yaml = """
apiVersion: v0.1
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    runtimeConfig: "image: nginx:latest"
        """
        is_valid, issues = validator.validate_workload_config(valid_yaml)
        assert is_valid == True
        errors = [i for i in issues if i['severity'] == 'ERROR']
        assert len(errors) == 0
    
    def test_invalid_yaml_syntax(self):
        """Test that invalid YAML is caught"""
        validator = ConfigurationValidator()
        invalid_yaml = "workloads:\n  nginx:\n    runtime podman"  # Missing colon
        is_valid, issues = validator.validate_workload_config(invalid_yaml)
        assert is_valid == False
        assert any(i['type'] == 'SYNTAX_ERROR' for i in issues)
    
    def test_missing_required_fields(self):
        """Test that missing fields are detected"""
        validator = ConfigurationValidator()
        incomplete_yaml = """
workloads:
  nginx:
    agent: agent_A
        """
        is_valid, issues = validator.validate_workload_config(incomplete_yaml)
        assert is_valid == False
        assert any('runtime' in i['message'].lower() for i in issues)
    
    def test_invalid_runtime(self):
        """Test that invalid runtime value is caught"""
        validator = ConfigurationValidator()
        invalid_yaml = """
workloads:
  nginx:
    runtime: invalid_runtime
    agent: agent_A
        """
        is_valid, issues = validator.validate_workload_config(invalid_yaml)
        assert is_valid == False
        assert any('runtime' in i['message'].lower() for i in issues)


class TestDependencyValidator:
    
    def test_missing_dependency(self):
        """Test detection of missing dependency"""
        validator = DependencyValidator(current_workloads=[])
        config = """
workloads:
  app:
    runtime: podman
    agent: agent_A
    dependencies:
      database: {}
        """
        is_valid, issues = validator.validate_dependencies(config)
        assert is_valid == False
        assert any(i['type'] == 'MISSING_DEPENDENCY' for i in issues)
    
    def test_circular_dependency(self):
        """Test detection of circular dependency"""
        validator = DependencyValidator(current_workloads=[])
        config = """
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
        is_valid, issues = validator.validate_dependencies(config)
        assert is_valid == False
        assert any(i['type'] == 'CIRCULAR_DEPENDENCY' for i in issues)
    
    def test_self_dependency(self):
        """Test detection of self-dependency"""
        validator = DependencyValidator(current_workloads=[])
        config = """
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    dependencies:
      nginx: {}
        """
        is_valid, issues = validator.validate_dependencies(config)
        assert is_valid == False
        assert any(i['type'] == 'SELF_DEPENDENCY' for i in issues)


class TestConflictDetector:
    
    def test_port_conflict(self):
        """Test detection of port conflicts"""
        current = [
            {'name': 'nginx', 'runtimeConfig': 'commandOptions: ["-p", "8080:80"]'}
        ]
        detector = ResourceConflictDetector(current)
        
        new_config = """
workloads:
  apache:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      commandOptions: ["-p", "8080:80"]
        """
        
        no_conflicts, issues = detector.detect_conflicts(new_config)
        assert no_conflicts == False
        assert any(i['type'] == 'PORT_CONFLICT' for i in issues)
    
    def test_no_port_conflict(self):
        """Test that different ports don't conflict"""
        current = [
            {'name': 'nginx', 'runtimeConfig': 'commandOptions: ["-p", "8080:80"]'}
        ]
        detector = ResourceConflictDetector(current)
        
        new_config = """
workloads:
  apache:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      commandOptions: ["-p", "8081:80"]
        """
        
        no_conflicts, issues = detector.detect_conflicts(new_config)
        assert no_conflicts == True
        assert len(issues) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])