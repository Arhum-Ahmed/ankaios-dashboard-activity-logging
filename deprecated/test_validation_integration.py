#!/usr/bin/env python3
"""
Test script demonstrating the configuration validation and auto-healing integration.
This shows how workload deployment is now protected by automatic validation and healing.
"""

import sys
import os
import yaml

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from validators.deployment_validator import DeploymentValidator
from validators.config_remediator import ConfigurationRemediator


def test_scenario(name: str, config_yaml: str, expected_healing: bool = False):
    """Test a specific scenario"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    
    validator = DeploymentValidator()
    result = validator.validate_and_heal(config_yaml, auto_heal=True)
    
    print(f"\nOriginal Valid:   {result['original_valid']}")
    print(f"Healed:           {result['healed']}")
    print(f"Final Valid:      {result['final_valid']}")
    print(f"Success (Ready):  {result['success']}")
    
    print(f"\nValidation Report ({result['validation_report'].get('overall_status')}):")
    for test in result['validation_report'].get('tests', []):
        status = test.get('status', 'UNKNOWN')
        errors = test.get('error_count', 0)
        warnings = test.get('warning_count', 0)
        print(f"  - {test['name']}: {status} (E:{errors} W:{warnings})")
    
    if result['healing_report'].get('logs'):
        print(f"\nHealing Report:")
        for log in result['healing_report']['logs']:
            print(f"  - {log}")
    
    if result['final_valid']:
        print(f"\n✓ READY FOR DEPLOYMENT")
    else:
        print(f"\n✗ NOT READY FOR DEPLOYMENT")
        if result['healing_report'].get('remaining_issues'):
            print(f"Remaining issues that need manual fixing:")
            for issue in result['healing_report']['remaining_issues']:
                print(f"  - {issue.get('message', 'Unknown issue')}")
    
    return result


def main():
    print("\n" + "="*70)
    print("ANKAIOS DASHBOARD - VALIDATION AND AUTO-HEALING INTEGRATION TEST")
    print("="*70)
    
    # Test 1: Valid configuration (no healing needed)
    valid_config = """
workloads:
  valid-app:
    runtime: podman
    agent: agent_A
    runtimeConfig: "image: nginx:latest"
    restartPolicy: ALWAYS
"""
    result1 = test_scenario(
        "Valid Configuration (No Healing Needed)",
        valid_config,
        expected_healing=False
    )
    
    # Test 2: Missing runtime (should be healed)
    missing_runtime = """
workloads:
  missing-runtime-app:
    agent: agent_A
    runtimeConfig: "image: alpine:latest"
    restartPolicy: ALWAYS
"""
    result2 = test_scenario(
        "Missing Runtime Field (Auto-Healed)",
        missing_runtime,
        expected_healing=True
    )
    
    # Test 3: Missing agent (should be healed)
    missing_agent = """
workloads:
  missing-agent-app:
    runtime: podman
    runtimeConfig: "image: alpine:latest"
    restartPolicy: ALWAYS
"""
    result3 = test_scenario(
        "Missing Agent Field (Auto-Healed)",
        missing_agent,
        expected_healing=True
    )
    
    # Test 4: Missing required fields (should be partially healed)
    minimal_config = """
workloads:
  minimal-app:
    runtimeConfig: "image: busybox:latest"
"""
    result4 = test_scenario(
        "Multiple Missing Fields (Partial Healing)",
        minimal_config,
        expected_healing=True
    )
    
    # Test 5: Invalid YAML (should fail validation)
    invalid_yaml = """
workloads:
  broken-app:
    runtime: podman
    agent: agent_A
    runtimeConfig: "image: alpine:latest
    # Missing closing quote
"""
    result5 = test_scenario(
        "Invalid YAML Syntax (Cannot Heal)",
        invalid_yaml,
        expected_healing=False
    )
    
    # Test 6: Circular dependency (if applicable)
    circular_dep = """
workloads:
  app-a:
    runtime: podman
    agent: agent_A
    runtimeConfig: "image: alpine:latest"
    dependencies:
      app-b: RUNNING
  app-b:
    runtime: podman
    agent: agent_A
    runtimeConfig: "image: alpine:latest"
    dependencies:
      app-a: RUNNING
"""
    result6 = test_scenario(
        "Circular Dependencies (Cannot Auto-Heal)",
        circular_dep,
        expected_healing=False
    )
    
    # Summary
    print(f"\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    results = [
        ("Valid Config", result1, True),
        ("Missing Runtime", result2, True),
        ("Missing Agent", result3, True),
        ("Multiple Missing Fields", result4, False),  # May not be fully healed
        ("Invalid YAML", result5, False),
        ("Circular Dependency", result6, False),
    ]
    
    for test_name, result, expected_success in results:
        status = "✓ PASS" if result['success'] == expected_success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n" + "="*70)
    print("Integration test completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
