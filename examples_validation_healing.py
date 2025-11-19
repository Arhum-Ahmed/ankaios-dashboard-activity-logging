#!/usr/bin/env python3
"""
Example: How to use the configuration validation and auto-healing system
This demonstrates real-world usage patterns
"""

import sys
import os
import json

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from AnkCommunicationService import AnkCommunicationService
from ActivityLogger import ActivityLogger


def example_1_simple_deployment():
    """Example 1: Simple workload deployment with automatic validation"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Simple Workload Deployment")
    print("="*70)
    
    service = AnkCommunicationService()
    
    # Create a workload configuration
    workload = {
        "workloadName": "nginx-server",
        "runtime": "podman",
        "agent": "agent_A",
        "runtimeConfig": "image: nginx:latest\nports:\n  - containerPort: 80\n    hostPort: 8080",
        "restartPolicy": "ALWAYS"
    }
    
    print("\nDeploying workload:", workload["workloadName"])
    
    # Deploy with automatic validation and healing
    result = service.apply_workload_with_validation(
        workload,
        user_id="admin@example.com"
    )
    
    # Check the result
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Healed: {result.get('healed', False)}")
    
    if result['status'] == 'success':
        print("✓ Workload deployed successfully!")
    else:
        print("✗ Deployment failed")
        print(f"Error details: {result.get('error', 'Unknown error')}")


def example_2_invalid_config_auto_healed():
    """Example 2: Invalid configuration that gets auto-healed"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Invalid Config (Missing Fields) - Auto-Healed")
    print("="*70)
    
    service = AnkCommunicationService()
    
    # This config is missing 'runtime' and 'agent' - they will be auto-fixed
    incomplete_workload = {
        "workloadName": "redis-cache",
        "runtimeConfig": "image: redis:latest\nports:\n  - containerPort: 6379",
        "restartPolicy": "ON_FAILURE"
        # Missing: runtime, agent
    }
    
    print("\nDeploying incomplete workload:", incomplete_workload["workloadName"])
    
    result = service.apply_workload_with_validation(
        incomplete_workload,
        user_id="developer@example.com"
    )
    
    print(f"Status: {result['status']}")
    print(f"Healed: {result.get('healed', False)}")
    
    if result.get('healed'):
        print("\n✓ Configuration was automatically healed!")
        healing_logs = result['validation_result']['healing_report'].get('logs', [])
        for log in healing_logs:
            print(f"  - {log}")
    
    if result['status'] == 'success':
        print("\n✓ Workload deployed with auto-healed configuration!")


def example_3_validation_only():
    """Example 3: Validate without deploying"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Validation Only (No Deployment)")
    print("="*70)
    
    service = AnkCommunicationService()
    
    # Just validate the configuration
    config_yaml = """
workloads:
  database:
    runtime: podman-kube
    agent: agent_B
    runtimeConfig: "image: postgres:latest"
    restartPolicy: ALWAYS
    dependencies:
      init-data:
        condition: RUNNING
"""
    
    print("\nValidating configuration...")
    
    validation_result = service.validate_and_heal_config(
        config_yaml,
        user_id="qa@example.com"
    )
    
    print(f"Original Valid: {validation_result['original_valid']}")
    print(f"Final Valid: {validation_result['final_valid']}")
    print(f"Healed: {validation_result['healed']}")
    print(f"Deployment Status: {validation_result['deployment_status']}")
    
    # Show validation details
    print("\nValidation Tests:")
    for test in validation_result['validation_report'].get('tests', []):
        status = "✓" if test['status'] == 'PASSED' else "✗"
        print(f"  {status} {test['name']}: {test['status']}")
    
    if validation_result['healing_report']['logs']:
        print("\nHealing Report:")
        for log in validation_result['healing_report']['logs']:
            print(f"  - {log}")


def example_4_api_validation_endpoint():
    """Example 4: Using the REST API validation endpoint"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Using REST API Validation Endpoint")
    print("="*70 + "\n")
    
    print("This example shows how to use the REST API:")
    print("""
# Validate and heal via curl:
curl -X POST http://localhost:5001/api/validate-and-heal \\
  -H "Content-Type: application/json" \\
  -d '{
    "config": "workloads:\\n  myapp:\\n    agent: agent_A\\n    runtimeConfig: \\"image: nginx\\""
  }'

Response:
{
  "success": true,
  "original_valid": false,
  "healed": true,
  "final_valid": true,
  "deployment_status": "ready",
  "healing_report": {
    "logs": [
      "Added missing \\"runtime\\" to myapp: set to \\"podman\\".",
      "✓ Configuration healed and re-validated successfully!"
    ]
  }
}
    """)


def example_5_activity_logging():
    """Example 5: Check activity logs for validation history"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Activity Logging")
    print("="*70)
    
    try:
        activity_logger = ActivityLogger()
        
        # Get recent validation activities
        print("\nRecent validation activities:")
        print("(Note: Requires database/activity log storage configured)")
        
        # Example of how to query logs
        print("""
Example query:
logs = activity_logger.get_logs(
    action='validate_config',
    limit=10
)

for log in logs:
    print(f"User: {log['user_id']}")
    print(f"Time: {log['timestamp']}")
    print(f"Status: {log['status']}")
    print(f"Healed: {log['metadata'].get('healed', False)}")
    print(f"Errors: {log['metadata'].get('total_errors', 0)}")
        """)
    except Exception as e:
        print(f"Activity logging not available: {e}")


def example_6_advanced_config():
    """Example 6: Complex workload with dependencies"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Complex Configuration with Dependencies")
    print("="*70)
    
    service = AnkCommunicationService()
    
    # A more complex workload configuration
    complex_workload = {
        "workloadName": "app-service",
        "runtime": "podman",
        "agent": "agent_B",
        "runtimeConfig": "image: myapp:v1.0\nports:\n  - containerPort: 3000\n    hostPort: 3000",
        "restartPolicy": "ON_FAILURE",
        "dependencies": {
            "database": "RUNNING",
            "cache": "READY"
        },
        "tags": [
            {"key": "environment", "value": "production"},
            {"key": "team", "value": "backend"}
        ]
    }
    
    print(f"\nDeploying complex workload: {complex_workload['workloadName']}")
    print(f"Dependencies: {complex_workload['dependencies']}")
    print(f"Tags: {complex_workload['tags']}")
    
    result = service.apply_workload_with_validation(
        complex_workload,
        user_id="devops@example.com"
    )
    
    # Show detailed result
    print(f"\nDeployment Result:")
    print(f"  Status: {result['status']}")
    print(f"  Message: {result['message']}")
    print(f"  Healed: {result.get('healed', False)}")
    
    if result['status'] == 'success':
        print("\n✓ Complex workload deployed successfully!")


def main():
    print("\n" + "="*70)
    print("CONFIGURATION VALIDATION & AUTO-HEALING - USAGE EXAMPLES")
    print("="*70)
    
    print("""
This script demonstrates 6 real-world usage patterns:

1. Simple workload deployment
2. Invalid config that gets auto-healed
3. Validation-only (no deployment)
4. Using the REST API
5. Checking activity logs
6. Complex configurations with dependencies
    """)
    
    # Run examples (commented some to avoid actual deployment)
    example_1_simple_deployment()
    example_2_invalid_config_auto_healed()
    example_3_validation_only()
    example_4_api_validation_endpoint()
    example_5_activity_logging()
    example_6_advanced_config()
    
    print("\n" + "="*70)
    print("Examples completed!")
    print("="*70)
    print("""
For more information:
- See VALIDATION_AND_HEALING_GUIDE.md for comprehensive documentation
- See QUICK_REFERENCE.md for API quick reference
- Run: python3 test_validation_integration.py for integration tests
    """)


if __name__ == "__main__":
    main()
