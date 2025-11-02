# test_validators_cli.sh
#!/bin/bash

echo "Testing Validators Directly (No GUI/API)"
echo "=========================================="

cd app

# Test 1: Schema Validator
echo "Test 1: Schema Validator"
python3 << 'EOF'
from validators.schema_validator import ConfigurationValidator

validator = ConfigurationValidator()

# Valid config
valid = """
workloads:
  nginx:
    runtime: podman
    agent: agent_A
"""
is_valid, issues = validator.validate_workload_config(valid)
print(f"Valid config: {'PASS' if is_valid else 'FAIL'}")

# Invalid config
invalid = """
workloads:
  Bad Name:
    runtime: invalid
"""
is_valid, issues = validator.validate_workload_config(invalid)
print(f"Invalid config detected: {'PASS' if not is_valid else 'FAIL'}")
print(f"Errors found: {len([i for i in issues if i['severity'] == 'ERROR'])}")
EOF
echo ""

# Test 2: Dependency Validator
echo "Test 2: Dependency Validator"
python3 << 'EOF'
from validators.dependency_validator import DependencyValidator

validator = DependencyValidator([])

# Circular dependency
circular = """
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
      A: {}
"""
is_valid, issues = validator.validate_dependencies(circular)
has_circular = any(i['type'] == 'CIRCULAR_DEPENDENCY' for i in issues)
print(f"Circular dependency detected: {'PASS' if has_circular else 'FAIL'}")

# Missing dependency
missing = """
workloads:
  app:
    runtime: podman
    agent: agent_A
    dependencies:
      database: {}
"""
is_valid, issues = validator.validate_dependencies(missing)
has_missing = any(i['type'] == 'MISSING_DEPENDENCY' for i in issues)
print(f"Missing dependency detected: {'PASS' if has_missing else 'FAIL'}")
EOF
echo ""

# Test 3: Conflict Detector
echo "Test 3: Port Conflict Detector"
python3 << 'EOF'
from validators.conflict_detector import ResourceConflictDetector

current = [
    {'name': 'nginx', 'runtimeConfig': 'commandOptions: ["-p", "8080:80"]'}
]
detector = ResourceConflictDetector(current)

# Conflicting port
conflict = """
workloads:
  apache:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      commandOptions: ["-p", "8080:80"]
"""
no_conflicts, issues = detector.detect_conflicts(conflict)
has_conflict = any(i['type'] == 'PORT_CONFLICT' for i in issues)
print(f"Port conflict detected: {'PASS' if has_conflict else 'FAIL'}")

# No conflict
no_conflict = """
workloads:
  apache:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      commandOptions: ["-p", "8081:80"]
"""
no_conflicts, issues = detector.detect_conflicts(no_conflict)
print(f"No false positives: {'PASS' if no_conflicts else 'FAIL'}")
EOF
echo ""

cd ..
echo "Direct Python Tests Complete"