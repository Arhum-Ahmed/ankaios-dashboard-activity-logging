# Quick Reference: Config Validation & Auto-Healing

## One-Minute Overview

When you deploy a workload, the system now:
1. **Validates** the configuration (schema, dependencies, conflicts)
2. **Auto-heals** any fixable issues
3. **Re-validates** the healed config
4. **Deploys** only if valid

## API Usage

### Deploy with automatic validation and healing:
```bash
curl -X POST http://localhost:5001/addNewWorkload \
  -H "Content-Type: application/json" \
  -d '{
    "workloadName": "my-app",
    "runtime": "podman",
    "agent": "agent_A",
    "runtimeConfig": "image: myapp:latest"
  }'
```

### Just validate and heal (don't deploy):
```bash
curl -X POST http://localhost:5001/api/validate-and-heal \
  -H "Content-Type: application/json" \
  -d '{"config": "workloads:\n  my-app:\n    runtime: podman\n    agent: agent_A"}'
```

## Python Usage

### Deploy with validation:
```python
from AnkCommunicationService import AnkCommunicationService

service = AnkCommunicationService()
result = service.apply_workload_with_validation(
    {"workloadName": "my-app", "runtime": "podman", ...},
    user_id="user123"
)

if result['status'] == 'success':
    print("✓ Deployed!")
    if result['healed']:
        print(f"Config was auto-healed")
else:
    print("✗ Failed:", result['message'])
```

### Just validate and heal:
```python
result = service.validate_and_heal_config(
    "workloads:\n  my-app:\n    runtime: podman",
    user_id="user123"
)
```

## What Gets Auto-Fixed

| Issue | Auto-Fix |
|-------|----------|
| Missing `runtime` | ✓ Sets to `podman` |
| Missing `agent` | ✓ Sets to `agent_A` |
| Invalid `runtime` value | ✓ Fixes to valid value |
| Invalid dependency | ✓ Removes reference |
| Port conflict | ✓ Increments port |
| Bad naming (spaces/case) | ✓ Fixes format |

## What Cannot Be Auto-Fixed

- Circular dependencies
- Invalid YAML syntax
- Multiple missing critical fields (complex cases)
- Custom validation rule violations

## Response Status Codes

| Status | Meaning |
|--------|---------|
| `success` | Config valid, deployed ✓ |
| `validation_failed` | Config still invalid after healing ✗ |
| `deployment_failed` | Config valid but deployment error ✗ |

## Key Files

| File | Purpose |
|------|---------|
| `app/validators/deployment_validator.py` | Main validation & healing orchestrator |
| `app/validators/config_remediator.py` | Auto-fix logic |
| `app/AnkCommunicationService.py` | Integration with Ankaios SDK |
| `app/DashboardAPI.py` | REST API endpoints |

## Logging

All actions logged to activity log:
```python
activity_logger.get_logs(action='validate_config')
```

## Disable Auto-Healing

```python
result = service.validate_and_heal_config(config, auto_heal=False)
```

## Test It

```bash
python3 test_validation_integration.py
```

---

**Full docs**: See `VALIDATION_AND_HEALING_GUIDE.md`
