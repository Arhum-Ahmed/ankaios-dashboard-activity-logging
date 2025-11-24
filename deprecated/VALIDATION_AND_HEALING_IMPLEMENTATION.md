
# Configuration Validation & Auto-Healing Implementation

## Overview

This document describes the complete implementation of the configuration validation and auto-healing system integrated with the Ankaios dashboard. The system validates YAML configuration files before deployment, automatically detects and fixes common issues, and persists healed configurations for future deployments.

**Key Feature**: When you run `./ank -k apply config/your-file.yaml`, the system:
1. Validates the configuration against 4 test suites (schema, dependency, circular dependency, resource conflicts).
2. If validation fails, attempts automatic remediation using rule-based fixes.
3. Persists the healed configuration (backing up the original with a timestamp).
4. Re-validates the healed configuration.
5. If re-validation passes, applies the healed configuration using the real `ank` CLI.

---

## Files Modified & Created

### 1. **Wrapper Script: `./ank` (root directory)**

**Purpose**: Intercept `ank -k apply <config>` commands and add validation + healing before applying.

**Key Changes**:
- All logging now goes to `stderr` (using `>&2`) so `stdout` contains only clean YAML when needed.
- Implements `validate_config()` function that:
  - Calls the dashboard's public validator endpoint (`POST /api/validate-config`).
  - If validation passes, returns the original YAML on stdout.
  - If validation fails:
    - Prints detailed failure messages to stderr.
    - Extracts validator issues and invokes the local remediator.
    - Shows remediation log (what was fixed).
    - Persists healed YAML to the original file path (creates timestamped backup `file.bak.<ts>`).
    - Re-validates the healed YAML.
    - If re-validation passes, returns healed YAML on stdout.
    - If re-validation fails, returns error and aborts (does not apply).
- Main apply logic captures the validated/healed config and pipes it to `ank -k apply`.

**Usage**:
```bash
./ank -k apply config/myconfig.yaml
```

**Example Output** (on success):
```
[INFO] Validating configuration: config/myconfig.yaml
[SUCCESS] Configuration validated!
[INFO] Applying configuration...
[SUCCESS] Configuration applied
```

**Example Output** (on remediation):
```
[INFO] Validating configuration: config/myconfig.yaml
[INFO] Validating configuration: config/myconfig.yaml
[ERROR] Validation FAILED for config/myconfig.yaml. Details:
- [Dependency Validation] FAILED
  issues: [{"message":"Workload 'nginx' cannot depend on itself",...}]
[INFO] Attempting auto-heal locally
[INFO] Remediation log:
Removed self-dependency from "nginx".
[SUCCESS] Healed configuration persisted to config/myconfig.yaml (backup: config/myconfig.yaml.bak.1763352160)
[INFO] Applying configuration...
[SUCCESS] Configuration applied
```

---

### 2. **Remediator: `app/validators/config_remediator.py`**

**Purpose**: Automatically fix common configuration issues detected by validators.

**Key Improvements & Fixes Implemented**:

1. **Self-Dependency Removal** (FIX 6b)
   - Pattern: `issue.get('type') == 'SELF_DEPENDENCY'` or message contains "cannot depend on itself"
   - Action: Removes the workload from its own dependencies.
   - Example: `nginx: { dependencies: { nginx: {} } }` → `nginx: { dependencies: {} }`

2. **Circular Dependency Breaking** (FIX 6c)
   - Pattern: `issue.get('type') == 'CIRCULAR_DEPENDENCY'` with a cycle list
   - Action: Removes the first edge in the detected cycle (e.g., `cycle: [A, B]` removes dependency of A on B).
   - Example: `A -> B -> A` becomes `A -> B` (breaks the cycle).

3. **MultiLine String Normalization** (FIX: runtimeConfig handling)
   - Strips carriage returns (`\r`) and null characters (`\x00`).
   - Removes leading and trailing empty lines.
   - Removes common indentation so block scalars align properly.
   - Ensures YAML dump uses SafeDumper with a custom string representer.
   - Multi-line strings are emitted as block literals (`|-` or `|`) so the Ankaios parser accepts them.

4. **Existing Fixes** (maintained from prior work):
   - FIX 1: Add missing `runtime` field → defaults to `podman`.
   - FIX 2: Correct invalid `runtime` → defaults to `podman`.
   - FIX 3: Add missing `agent` field → defaults to `agent_A`.
   - FIX 4: Rename invalid workload names (spaces, uppercase) → lowercase with underscores.
   - FIX 5: Insert minimal `runtimeConfig` → defaults to `image: alpine:latest`.
   - FIX 6: Remove invalid dependencies (that don't exist).
   - FIX 7: Adjust port conflicts by incrementing conflicting port numbers.

**Implementation Details**:
```python
def auto_fix(self, config_yaml: str, issues: List[dict]) -> Tuple[str, List[str]]:
    """
    Applies automated fixes to the configuration YAML.
    Args:
        config_yaml: original YAML text
        issues: list of validator issues (dicts with 'type', 'message', 'workload', etc.)
    Returns:
        (fixed_yaml_string, remediation_log_list)
    """
```

**Remediation Log**: A list of strings describing each action taken (e.g., `["Removed self-dependency from 'nginx'."]`).

---

### 3. **Dashboard API: `app/DashboardAPI.py`**

**New Endpoint**: `POST /api/validate-config`
- **Purpose**: Public (no auth) validator endpoint accessible by the wrapper.
- **Request**: JSON with `config` field containing YAML as string.
- **Response**: Comprehensive JSON report with:
  - `overall_status`: "PASSED" or "FAILED"
  - `tests`: Array of test results (schema, dependency, circular, conflict)
  - `summary`: Counts (passed, failed, errors, warnings, duration)
  - `timestamp`: ISO timestamp

**Example Request**:
```bash
curl -s -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d "{\"config\": $(jq -Rs . < config/myconfig.yaml)}" | jq
```

**Example Response** (on validation failure):
```json
{
  "overall_status": "FAILED",
  "summary": {
    "failed": 2,
    "passed": 2,
    "total_errors": 2,
    "total_tests": 4
  },
  "tests": [
    {
      "name": "Schema Validation",
      "status": "PASSED",
      "issues": []
    },
    {
      "name": "Dependency Validation",
      "status": "FAILED",
      "issues": [
        {
          "type": "SELF_DEPENDENCY",
          "severity": "ERROR",
          "message": "Workload 'nginx' cannot depend on itself",
          "workload": "nginx"
        }
      ]
    },
    {
      "name": "Circular Dependency Check",
      "status": "FAILED",
      "issues": [
        {
          "type": "CIRCULAR_DEPENDENCY",
          "severity": "ERROR",
          "message": "Circular dependency: nginx -> nginx",
          "cycle": ["nginx", "nginx"]
        }
      ]
    },
    {
      "name": "Resource Conflict Detection",
      "status": "PASSED",
      "issues": []
    }
  ]
}
```

---

### 4. **Validation Framework: `app/validators/test_executor.py`**

**No Changes Required** — uses existing `PreDeploymentTester` class.

**Test Suite Includes**:
1. **Schema Validation**: YAML syntax, required fields (runtime, agent, runtimeConfig).
2. **Dependency Validation**: All referenced dependencies exist.
3. **Circular Dependency Check**: Detects `A -> B -> A` patterns using graph algorithms.
4. **Resource Conflict Detection**: Checks for port/resource conflicts across workloads.

---

## Workflow Diagram

```
User runs: ./ank -k apply config/myconfig.yaml
                |
                v
    [WRAPPER] Calls validate_config()
                |
                v
        Dashboard /api/validate-config
                |
        +-------+--------+
        |                |
   PASSED            FAILED
        |                |
        v                v
    Return YAML    Extract Issues
                        |
                        v
                   Run Remediator
                        |
        +---------------+
        |               |
     Fixes         No Fixes
     Applied       Needed
        |               |
        v               v
    Persist        Return
    Healed YAML    Original
        |
        v
    Re-Validate
        |
    +---+---+
    |       |
 PASSED   FAILED
    |       |
    v       v
  Apply   Abort
```

---

## Validation Tests in Detail

### Test 1: Schema Validation
- **What it checks**: YAML syntax, presence of required fields, type correctness.
- **Failure example**: Missing `runtime`, missing `agent`, malformed YAML.
- **Auto-fix available**: Yes (add defaults or correct types).

### Test 2: Dependency Validation
- **What it checks**: All workloads referenced in dependencies actually exist.
- **Failure example**: Workload `A` depends on `B`, but `B` is not defined.
- **Auto-fix available**: Yes (remove invalid dependency).

### Test 3: Circular Dependency Check
- **What it checks**: No cycles in the dependency graph (e.g., `A -> B -> A`).
- **Failure example**: `A` depends on itself, or `A -> B -> C -> A`.
- **Auto-fix available**: Yes (break cycle by removing one edge).

### Test 4: Resource Conflict Detection
- **What it checks**: No two workloads use the same port or resource.
- **Failure example**: Two workloads bind to port 8080.
- **Auto-fix available**: Yes (increment conflicting port).

---

## Usage Examples

### Example 1: Basic Validation-Only (No Apply)

**Command**:
```bash
curl -s -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d "{\"config\": $(jq -Rs . < config/demo_fail.yaml)}" | jq
```

**Expected Output** (on validation failure):
```json
{
  "overall_status": "FAILED",
  "summary": { "failed": 2, "passed": 2, ... },
  "tests": [ ... validation failures ... ]
}
```

---

### Example 2: Validate + Heal + Apply (Full Workflow)

**Command**:
```bash
./ank -k apply config/demo_fail.yaml
```

**Expected Flow**:
1. Validates `config/demo_fail.yaml`.
2. Detects self-dependency issue.
3. Runs remediator and removes the self-dependency.
4. Persists healed YAML to `config/demo_fail.yaml` (backup: `config/demo_fail.yaml.bak.1763352160`).
5. Re-validates healed YAML (now passes).
6. Applies healed YAML using `ank -k apply`.

**Console Output**:
```
[INFO] Validating configuration: config/demo_fail.yaml
[INFO] Validating configuration: config/demo_fail.yaml
[ERROR] Validation FAILED for config/demo_fail.yaml. Details:
- [Dependency Validation] FAILED
  issues: [{"message":"Workload 'demo' cannot depend on itself",...}]
- [Circular Dependency Check] FAILED
  issues: [{"cycle":["demo","demo"],"message":"Circular dependency: demo -> demo",...}]
[INFO] Attempting auto-heal locally
[INFO] Remediation log:
Removed self-dependency from "demo".
[SUCCESS] Healed configuration persisted to config/demo_fail.yaml (backup: config/demo_fail.yaml.bak.1763352160)
[INFO] Applying configuration...
Successfully applied the manifest(s).
...
[SUCCESS] Configuration applied
```

---

### Example 3: Check Deployed Workloads

**Command**:
```bash
./ank -k get workloads
```

**Expected Output**:
```
WORKLOAD NAME   AGENT     RUNTIME   EXECUTION STATE
demo            agent_A   podman    Running(Ok)
```

---

## Backup & Recovery

Each time the wrapper heals and overwrites a config file, it creates a timestamped backup:
- **Backup filename**: `config/myconfig.yaml.bak.<unix_timestamp>`
- **Location**: Same directory as original.
- **Content**: Original (pre-heal) configuration.

**Example**:
```bash
# List backups
ls -l config/demo_fail.yaml*

# Restore from backup if needed
cp config/demo_fail.yaml.bak.1763352160 config/demo_fail.yaml

# Compare original and healed
diff -u config/demo_fail.yaml.bak.1763352160 config/demo_fail.yaml
```

---

## Troubleshooting

### Issue: Wrapper says "control characters are not allowed"
- **Cause**: YAML contains carriage returns (`\r`) or null bytes (`\x00`).
- **Solution**: The remediator now strips these automatically. If the error persists:
  1. Check the healed file: `cat -v config/myconfig.yaml | head -20`
  2. Compare with backup: `cat -v config/myconfig.yaml.bak.* | head -20`
  3. Manually clean: `tr -d '\r' < config/myconfig.yaml > config/myconfig.yaml.clean && mv config/myconfig.yaml.clean config/myconfig.yaml`

### Issue: Validator returned 400 Bad Request
- **Cause**: JSON payload malformed (bad quoting or escaping).
- **Solution**: Ensure you use `jq -Rs .` to safely encode YAML content:
  ```bash
  curl -s -X POST http://localhost:5001/api/validate-config \
    -H "Content-Type: application/json" \
    -d "{\"config\": $(jq -Rs . < config/myconfig.yaml)}" | jq
  ```

### Issue: Wrapper fails with "No response from dashboard validator"
- **Cause**: Dashboard not running or endpoint unreachable.
- **Solution**:
  1. Check dashboard status: `ps aux | grep flask` or `ps aux | grep python.*main.py`
  2. Ensure running on port 5001: `curl http://localhost:5001/ -v`
  3. Restart dashboard: `./run_dashboard.sh`

### Issue: Remediator couldn't fix all issues
- **Cause**: Validation errors that the current remediator doesn't have rules for.
- **Solution**: Check the remediation log for which issues remain. You can:
  1. Add new fix rules to `app/validators/config_remediator.py`.
  2. Manually edit the config file to fix the remaining issues.
  3. Re-run wrapper apply.

---

## Configuration & Environment Variables

### Dashboard URL
- **Default**: `http://localhost:5001`
- **Override**: Set `DASHBOARD_URL` env var before running wrapper:
  ```bash
  export DASHBOARD_URL="http://192.168.1.100:5001"
  ./ank -k apply config/myconfig.yaml
  ```

### Auto-Apply Behavior (Currently Always ON)
- The wrapper automatically persists healed configs and applies them.
- Future enhancements (on request):
  - `--dry-run` flag: validate + heal but don't apply.
  - `--no-overwrite` flag: write healed config to `file.healed.yaml` instead of overwriting.
  - `ANK_AUTO_APPLY` env var: control auto-apply behavior.

---

## Extending the Remediator

To add a new fix rule for a specific validation failure:

1. **Identify the validator issue type/message** (e.g., from the validator JSON output).
2. **Add a new `elif` block** in `ConfigurationRemediator.auto_fix()`:
   ```python
   elif issue.get('type') == 'MY_ISSUE_TYPE' or "my issue pattern" in msg:
       # your fix logic here
       remediation_log.append(f'Fixed MY_ISSUE for {workload_name}.')
   ```
3. **Test** by running the wrapper on a config that triggers your issue.

**Example**: Adding a fix for a custom issue type `MISSING_LABEL`:
```python
elif issue.get('type') == 'MISSING_LABEL':
    if 'labels' not in w:
        w['labels'] = {}
    w['labels']['auto-healed'] = 'true'
    remediation_log.append(f'Added default labels to {workload_name}.')
```

---

## Testing Checklist

Use this checklist to verify the system works end-to-end:

- [ ] Create a failing YAML with a self-dependency.
- [ ] Run validator-only: `curl ... /api/validate-config` → should show FAILED.
- [ ] Run wrapper apply: `./ank -k apply config/failing.yaml` → should heal and apply.
- [ ] Check backup created: `ls -l config/failing.yaml.bak.*` → should exist.
- [ ] Check healed file: `sed -n '1,200p' config/failing.yaml` → self-dependency removed.
- [ ] Re-validate healed: `curl ... /api/validate-config` on healed file → should show PASSED.
- [ ] Re-apply (idempotence): `./ank -k apply config/failing.yaml` → should apply without remediation.
- [ ] Check workloads deployed: `./ank -k get workloads` → should list the new workload.

---

## Architecture & Design Decisions

### Why Validate on Every Apply?
- Prevents deployment of broken configs.
- Auto-healing reduces manual intervention.
- Audit trail via activity logging (existing feature).

### Why Persist the Healed Config?
- Future applies on the same file don't need remediation (idempotence).
- Backup ensures you can see what changed.
- Prevents re-healing the same file repeatedly.

### Why Not Require Dashboard?
- Wrapper falls back to no validation if dashboard is unreachable.
- Remediator is local (Python code) so wrapper can heal offline.

### Why SafeDumper + Representer for YAML?
- Ensures block scalars (`|`) are emitted for multi-line strings.
- Prevents control characters in output that the Ankaios parser rejects.

---

## Summary of Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `./ank` | Modified | Wrapper: validate, heal, persist, re-validate, apply. |
| `app/validators/config_remediator.py` | Enhanced | Add self-dependency fix, circular-dependency fix, multiline normalization. |
| `app/DashboardAPI.py` | Existing | Uses existing public `/api/validate-config` endpoint. |

---

## Next Steps (Optional Enhancements)

1. **Non-Destructive Healing**: Write healed config to `file.healed.yaml` instead of overwriting (confirm before applying).
2. **CI/Batch Mode**: Add `/api/validate-multiple` endpoint to validate entire config directories and return aggregated reports.
3. **Prometheus Metrics**: Track remediation success/failure rates.
4. **Slack Notifications**: Alert on failed remediation attempts.
5. **Custom Remediation Rules**: Allow users to define their own fix patterns via config file.

---

## Questions & Support

- **How do I see the exact changes the remediator made?** Check the remediation log printed to stderr during wrapper execution, and compare original vs. healed files: `diff -u config/file.bak.* config/file`
- **Can I disable auto-healing?** Currently it's always on. I can add a `--no-heal` flag if needed.
- **What happens if remediation fails?** The wrapper aborts the apply and prints the validator report. You can then manually fix the config or add new remediation rules.
- **How do I know what remediator fixes are available?** Review the `if/elif` chain in `ConfigurationRemediator.auto_fix()` method in `app/validators/config_remediator.py`.

---

**End of Documentation**

For latest updates and issues, refer to the git commit history and code comments in the modified files.
