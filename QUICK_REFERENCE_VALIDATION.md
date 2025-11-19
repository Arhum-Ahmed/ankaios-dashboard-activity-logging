# Quick Start: Validation & Healing

## TL;DR

**One command**: Validate, auto-heal (if needed), and deploy your YAML:
```bash
./ank -k apply config/your-config.yaml
```

What happens:
1. ✅ Config validated (schema, dependencies, cycles, conflicts).
2. ❌ If validation fails:
   - Remediator attempts automatic fixes.
   - Healed config persisted (original backed up as `.bak.<timestamp>`).
   - Re-validated and applied.
3. ✅ Applied to Ankaios server.

---

## Verify It Works

**Create a failing config** (has self-dependency):
```bash
cat > config/demo_fail.yaml <<'EOF'
apiVersion: v0.1
workloads:
  demo:
    runtime: podman
    agent: agent_A
    dependencies:
      demo: {}
    runtimeConfig: |
      image: alpine:latest
EOF
```

**Run the wrapper**:
```bash
./ank -k apply config/demo_fail.yaml
```

**Expected output**:
```
[INFO] Validating configuration: config/demo_fail.yaml
[ERROR] Validation FAILED ... (shows self-dependency error)
[INFO] Attempting auto-heal locally
[INFO] Remediation log:
Removed self-dependency from "demo".
[SUCCESS] Healed configuration persisted to config/demo_fail.yaml (backup: config/demo_fail.yaml.bak.1234567890)
[INFO] Applying configuration...
Apply successful. No workloads updated.
[SUCCESS] Configuration applied
```

**Inspect the healed file**:
```bash
# Show healed file
cat config/demo_fail.yaml

# Show backup (original)
cat config/demo_fail.yaml.bak.*

# Confirm it validates now
curl -s -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d "{\"config\": $(jq -Rs . < config/demo_fail.yaml)}" | jq '.overall_status'
# Expected: "PASSED"
```

---

## Supported Auto-Fixes

The remediator can automatically fix:

| Issue | Fix | Example |
|-------|-----|---------|
| Self-dependency | Remove it | `demo: { dependencies: { demo: {} } }` → `demo: { dependencies: {} }` |
| Circular dependency | Break cycle | `A -> B -> A` becomes `A -> B` |
| Missing `runtime` | Add default | `runtime: podman` |
| Missing `agent` | Add default | `agent: agent_A` |
| Missing `runtimeConfig` | Add minimal | `image: alpine:latest` |
| Invalid dependency | Remove it | Workload references non-existent workload → dependency removed |
| Port conflict | Increment port | Port 8080 used twice → second incremented to 8081 |

---

## Commands Reference

### Validate Only (No Apply)
```bash
curl -s -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d "{\"config\": $(jq -Rs . < config/myconfig.yaml)}" | jq
```
Returns: JSON with `overall_status`, test results, and detailed issues.

### Validate + Heal + Apply
```bash
./ank -k apply config/myconfig.yaml
```
Returns: Console logs + final apply result.

### Check Workloads
```bash
./ank -k get workloads
```

### List Backups
```bash
ls -l config/myconfig.yaml*
```

### Restore from Backup
```bash
cp config/myconfig.yaml.bak.1234567890 config/myconfig.yaml
```

### Compare Original vs Healed
```bash
diff -u config/myconfig.yaml.bak.* config/myconfig.yaml
```

---

## Files Changed

| File | What Changed |
|------|--------------|
| `./ank` (root) | Now validates/heals before applying. |
| `app/validators/config_remediator.py` | Added self-dependency & cycle fixes; improved multiline string handling. |
| `app/DashboardAPI.py` | Uses existing public `/api/validate-config` endpoint (no changes needed). |

---

## Safety

- **Backups**: Every healed config creates a timestamped backup (`.bak.<unix_timestamp>`).
- **Re-validation**: Healed config is always re-validated before apply.
- **Rollback**: Simply restore from backup if needed: `cp config/file.bak.* config/file`

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "control characters are not allowed" | Remediator now strips them. If persists, manually clean: `tr -d '\r' < file > file.clean && mv file.clean file` |
| Validator returned 400 | Check JSON encoding: use `jq -Rs .` to safely embed YAML. |
| Dashboard unreachable | Ensure running: `./run_dashboard.sh` or check port 5001. |
| Remediation couldn't fix all issues | Check remediation log; add custom fix rule or manually edit config. |

---

## Full Documentation

For detailed architecture, extending remediation rules, and advanced usage, see:
**`VALIDATION_AND_HEALING_IMPLEMENTATION.md`**
