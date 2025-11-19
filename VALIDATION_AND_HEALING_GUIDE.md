# Configuration Validation and Auto-Healing Integration Guide

## Overview

The dashboard now integrates **automatic configuration validation and healing** into the workload deployment pipeline. When a workload is deployed via `ank-server apply workloads`, the system:

1. **Validates** the workload configuration against schema, dependencies, and conflicts
2. **Auto-heals** common issues if validation fails
3. **Re-validates** the healed configuration
4. **Deploys** only if the final configuration is valid

This ensures that invalid configurations are automatically fixed when possible, reducing deployment failures.

---

## Architecture

### Components

#### 1. **DeploymentValidator** (`validators/deployment_validator.py`)
Main orchestrator that manages the validation → healing → revalidation flow.

**Key Methods:**
- `validate_and_heal(config_yaml, auto_heal=True)`: Orchestrates the complete flow
- `_run_validation_suite(config_yaml)`: Runs all validation tests
- `_extract_errors_from_report()`: Extracts error-level issues from validation report

#### 2. **ConfigurationRemediator** (`validators/config_remediator.py`)
Auto-fixes common configuration issues:
- Missing required fields (runtime, agent)
- Invalid field values
- Naming issues (spaces, case)
- Missing dependencies
- Port conflicts

#### 3. **Enhanced AnkCommunicationService** (`app/AnkCommunicationService.py`)
Integrates validation into the deployment flow:

**Key Methods:**
- `validate_and_heal_config(config_yaml, user_id)`: Validates and heals a configuration
- `apply_workload_with_validation(workload_config, user_id)`: Deploys with validation
- `add_new_workload(json, user_id)`: New workload deployment with validation

#### 4. **Enhanced DashboardAPI** (`app/DashboardAPI.py`)
New API endpoints for validation and healing:

**New Endpoints:**
- `POST /api/validate-and-heal`: Validate and heal configuration
- Updated `POST /addNewWorkload`: Now includes validation and healing status

---

## Validation and Healing Flow

### Step 1: Initial Validation

The system runs comprehensive validation checks:

1. **YAML Parsing**: Checks if YAML is syntactically valid
2. **Schema Validation**: Validates workload configuration against Ankaios schema
3. **Dependency Validation**: Ensures all dependencies exist
4. **Circular Dependency Check**: Detects circular dependencies
5. **Resource Conflict Detection**: Identifies port and resource conflicts

### Step 2: Auto-Healing (if enabled)

If validation fails, the `ConfigurationRemediator` attempts to fix:

| Issue | Fix |
|-------|-----|
| Missing `runtime` | Sets to `podman` (default) |
| Invalid `runtime` | Replaces with `podman` |
| Missing `agent` | Sets to `agent_A` (default) |
| Naming with spaces/uppercase | Converts to valid format (lowercase, underscores) |
| Missing `runtimeConfig` | Inserts minimal config: `image: alpine:latest` |
| Invalid dependency reference | Removes the invalid dependency |
| Port conflict | Increments port number |

### Step 3: Re-validation

After healing, the configuration is re-validated to ensure it passes all checks.

### Step 4: Deployment

Only if final validation passes, the workload is deployed via `ank-server apply`.

---

## Usage Examples

### 1. Deploy a Workload with Automatic Validation and Healing

**Python API Call:**

```python
from AnkCommunicationService import AnkCommunicationService

service = AnkCommunicationService()

workload_config = {
    "workloadName": "my-app",
    "runtime": "podman",
    "agent": "agent_A",
    "runtimeConfig": "image: myapp:latest",
    "restartPolicy": "ALWAYS"
}

result = service.apply_workload_with_validation(workload_config, user_id="user123")

if result['status'] == 'success':
    print("✓ Workload deployed successfully!")
    if result['healed']:
        print(f"  Config was healed: {result['validation_result']['healing_report']['logs']}")
elif result['status'] == 'validation_failed':
    print("✗ Validation failed:")
    print(f"  Errors: {result['validation_result']['healing_report']}")
else:
    print("✗ Deployment failed:", result['message'])
```

### 2. REST API: Validate and Heal Configuration

**Request:**

```bash
curl -X POST http://localhost:5001/api/validate-and-heal \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  my-app:\n    runtime: podman\n    agent: agent_A\n    runtimeConfig: \"image: myapp:latest\""
  }'
```

**Response:**

```json
{
  "success": true,
  "original_valid": false,
  "healed": true,
  "final_valid": true,
  "deployment_status": "ready",
  "config": "workloads:\n  my-app:\n    runtime: podman\n    agent: agent_A\n    runtimeConfig: image: myapp:latest\n",
  "validation_report": {
    "overall_status": "FAILED",
    "tests": [...]
  },
  "healing_report": {
    "attempted": true,
    "logs": [
      "Added missing 'runtime' to my-app: set to 'podman'.",
      "✓ Configuration healed and re-validated successfully!"
    ]
  }
}
```

### 3. Deploy via REST API with Automatic Healing

**Request:**

```bash
curl -X POST http://localhost:5001/addNewWorkload \
  -H "Content-Type: application/json" \
  -d '{
    "workloadName": "my-app",
    "runtime": "podman",
    "agent": "agent_A",
    "runtimeConfig": "image: myapp:latest",
    "restartPolicy": "ALWAYS"
  }'
```

**Response:**

```json
{
  "status": "success",
  "message": "Workload deployed successfully.",
  "workload_name": "my-app",
  "healed": false,
  "validation_result": {
    "success": true,
    "original_valid": true,
    "final_valid": true,
    "healing_report": {
      "logs": ["Configuration is valid. No healing required."]
    }
  }
}
```

---

## Validation Report Structure

Each validation run generates a comprehensive report:

```python
{
    'overall_status': 'PASSED|FAILED',
    'tests': [
        {
            'name': 'Schema Validation',
            'status': 'PASSED|FAILED',
            'issues': [
                {
                    'type': 'SCHEMA_ERROR',
                    'severity': 'ERROR|WARNING',
                    'message': 'Description of the issue',
                    'workload': 'workload_name'
                }
            ],
            'error_count': 0,
            'warning_count': 0
        },
        # ... more tests
    ],
    'total_errors': 0,
    'total_warnings': 0
}
```

---

## Healing Report Structure

The healing report provides details about remediation attempts:

```python
{
    'attempted': True,
    'logs': [
        'Added missing "runtime" to my-app: set to "podman".',
        '✓ Configuration healed and re-validated successfully!'
    ],
    'issues_healed': [
        {
            'type': 'MISSING_FIELD',
            'field': 'runtime',
            'action': 'Added default value "podman"'
        }
    ],
    'remaining_issues': []  # If any issues couldn't be auto-fixed
}
```

---

## Configuration: Enabling/Disabling Auto-Healing

By default, auto-healing is **enabled**. To disable it:

```python
# Disable auto-healing
validation_result = service.validate_and_heal_config(
    config_yaml,
    auto_heal=False  # Disable auto-healing
)
```

When disabled, the system only validates without attempting repairs.

---

## Activity Logging

All validation and healing actions are logged to the activity log:

- **Action**: `validate_config` (for validation-only checks)
- **Status**: `success`, `validation_failed`, `deployment_failed`
- **Metadata**: Includes validation details, healing status, error counts

**Query Activity Logs:**

```python
from ActivityLogger import ActivityLogger

activity_logger = ActivityLogger()

# Get all validation activities
validation_logs = activity_logger.get_logs(
    action='validate_config',
    limit=50
)

for log in validation_logs:
    print(f"User: {log['user_id']}")
    print(f"Status: {log['status']}")
    print(f"Healed: {log['metadata'].get('healed')}")
```

---

## Extending the Remediator

To add custom healing logic for your specific issues:

1. **Edit** `validators/config_remediator.py`
2. **Add** a new fix pattern in the `auto_fix()` method:

```python
# FIX N: Your custom issue
elif "Your specific error message" in msg:
    # Your fix logic here
    workloads[workload_name]["your_field"] = "fixed_value"
    remediation_log.append(f'Fixed your issue in {workload_name}.')
```

3. **Test** your fix with a validation call

---

## Troubleshooting

### Issue: Configuration still fails after healing

**Solution**: Check `remaining_issues` in the healing report. Some issues can't be auto-fixed and require manual intervention.

```python
if result['healing_report'].get('remaining_issues'):
    print("Manual fixes required:")
    for issue in result['healing_report']['remaining_issues']:
        print(f"  - {issue['message']}")
```

### Issue: Auto-healing not working

**Ensure:**
1. `auto_heal=True` is passed to `validate_and_heal_config()`
2. The validation error matches one of the patterns in `config_remediator.py`
3. Check logs for detailed error messages

### Issue: Healed configuration is invalid

This shouldn't happen, but if it does:
1. Check the `validation_report['healed_validation']` for specific errors
2. Report an issue with the exact error and configuration

---

## Command Line Integration

To integrate with shell scripts using `ank-server`:

```bash
#!/bin/bash

# Before applying workloads, validate them
python3 -c "
from AnkCommunicationService import AnkCommunicationService
import sys

service = AnkCommunicationService()
result = service.validate_and_heal_config(open('config.yaml').read())

if result['success']:
    print('Configuration validated and ready for deployment')
    exit(0)
else:
    print('Configuration validation failed')
    exit(1)
"

if [ $? -eq 0 ]; then
    ank-server -c apply config.yaml
else
    echo "Deployment cancelled due to validation failure"
    exit 1
fi
```

---

## Performance Considerations

- **Validation overhead**: ~50-200ms per configuration (depends on complexity)
- **Healing overhead**: ~10-50ms (if healing is needed)
- **Caching**: Validation results are not cached; each deployment triggers fresh validation

For performance-critical scenarios, consider:
1. Running validation separately before deployment
2. Caching validation results if configuration doesn't change
3. Disabling conflict detection for large-scale deployments

---

## Future Enhancements

Potential improvements to the validation and healing system:

- [ ] Machine learning-based intelligent healing
- [ ] Custom healing rules per organization
- [ ] Validation result caching
- [ ] Parallel test execution
- [ ] Custom validators plugin system
- [ ] Integration with external validation services
- [ ] Dry-run mode to preview healed configurations
- [ ] Rollback on post-deployment validation failures

