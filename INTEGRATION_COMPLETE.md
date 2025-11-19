# 🚀 Complete Integration Guide

## What You Have Now

A complete configuration validation and auto-healing system that works with your **exact original command syntax**:

```bash
./ank -k apply config/test.yaml
```

---

## 📋 Quick Setup

### Step 1: The Script Already Works
The `ank` wrapper script is ready to use:

```bash
./ank -k apply config/test.yaml
```

### Step 2: Make It System-Wide (Optional)

Add to your PATH:
```bash
# Option A: Alias
echo "alias ank='/workspaces/ankaios-dashboard/ank'" >> ~/.bashrc

# Option B: Copy to bin
sudo cp /workspaces/ankaios-dashboard/ank /usr/local/bin/ank

# Option C: Add to PATH
export PATH="/workspaces/ankaios-dashboard:$PATH"
```

Then use anywhere:
```bash
ank -k apply config/test.yaml
```

---

## 🎯 What Happens When You Run It

### Example 1: Valid Configuration
```bash
$ ./ank -k apply config/test.yaml
[INFO] Validating configuration: config/test.yaml
[SUCCESS] Configuration validated!
[INFO] Applying configuration...
[SUCCESS] Configuration applied
```

### Example 2: Configuration with Missing Fields (Auto-Healed)
```bash
$ ./ank -k apply config/test.yaml
[INFO] Validating configuration: config/test.yaml
[SUCCESS] Configuration validated and auto-healed!
[INFO] Applying configuration...
[SUCCESS] Configuration applied
```

### Example 3: Invalid Configuration (Rejected)
```bash
$ ./ank -k apply config/test.yaml
[INFO] Validating configuration: config/test.yaml
[ERROR] Validation failed - deployment cancelled
```

---

## 📊 Components Overview

### The `ank` Wrapper Script
- **Location**: `/workspaces/ankaios-dashboard/ank`
- **Size**: ~60 lines of bash
- **Purpose**: Intercepts your commands and adds validation

### Validation Endpoints Used
- `POST /api/validate-and-heal` - Dashboard API for validation
- Default URL: `http://localhost:5001`

### Your Original Commands Still Work
- ✅ `./ank -k apply config/test.yaml` 
- ✅ `./ank get workloads`
- ✅ `./ank state`
- ✅ All other ank-server commands

---

## 🔧 Configuration Options

### Default Behavior
```bash
./ank -k apply config/test.yaml
# Validates, heals if needed, then applies
```

### Skip Validation (if needed)
```bash
SKIP_VALIDATION=1 ./ank -k apply config/test.yaml
# Applies without validation (like before)
```

### Custom Dashboard URL
```bash
DASHBOARD_URL=http://other-host:5001 ./ank -k apply config/test.yaml
```

### Combine Options
```bash
DASHBOARD_URL=http://other:5001 SKIP_VALIDATION=1 ./ank -k apply config/test.yaml
```

---

## 📁 Files Overview

### Wrapper Script
- `ank` - Main wrapper (~60 lines)

### Documentation
- `ANK_WRAPPER_USAGE.md` - Usage guide
- `INTEGRATION_COMPLETE.md` - This file

### Core System (Already Set Up)
- `app/validators/deployment_validator.py` - Validation logic
- `app/AnkCommunicationService.py` - Enhanced with validation
- `app/DashboardAPI.py` - Added validation endpoints

### Examples & Tests
- `test_validation_integration.py` - Test suite
- `examples_validation_healing.py` - Usage examples
- `deploy_with_validation.sh` - Alternative bash integration

---

## ✨ Key Features

Your wrapper provides:

✅ **Automatic Validation**
- YAML syntax check
- Schema validation
- Dependency checking
- Conflict detection

✅ **Automatic Healing**
- Adds missing required fields
- Fixes invalid values
- Removes bad dependencies
- Resolves port conflicts

✅ **Backward Compatible**
- Your exact command still works
- No learning curve
- All standard ank commands pass through

✅ **Activity Logging**
- All validations logged
- Audit trail maintained
- Easy troubleshooting

---

## 🚀 Usage Examples

### Deploy with Your Original Command
```bash
./ank -k apply config/test.yaml
```

### Deploy Alternative Configs
```bash
./ank -k apply config/startupState.yaml
./ank -k apply config/databroker.yaml
./ank -k apply config/speed-consumer.yaml
```

### Standard Ankaios Commands
```bash
# Get status
./ank get

# Get workloads
./ank get workloads

# Get complete state
./ank state

# Delete workload
./ank delete workloads my-workload
```

### From Scripts
```bash
#!/bin/bash
./ank -k apply config/test.yaml || {
    echo "Deployment failed!"
    exit 1
}
echo "Deployment successful!"
```

### In Docker
```dockerfile
RUN cp /app/ank /usr/local/bin/ank
CMD ank -k apply /config/test.yaml
```

---

## 🔄 Workflow

### Traditional Flow (Before)
```
ank-server apply config.yaml
        ↓
  (no validation)
        ↓
  Deployment (might fail due to bad config)
```

### New Flow (After)
```
./ank -k apply config.yaml
        ↓
  Validate configuration
        ↓
  Auto-heal if needed
        ↓
  Re-validate
        ↓
  Apply (only if valid)
        ↓
  Show status
```

---

## ✅ Verification

### Test the Wrapper
```bash
# Show version/help
./ank --help 2>&1 | head -5

# Should show ank-server help (wrapper passes through)
```

### Test With a Real Config
```bash
# Validate without applying
./ank -k apply config/test.yaml
```

### Check Status
```bash
./ank get workloads
```

---

## 🎓 Command Reference

### Your Command Format
| Command | What It Does |
|---------|-------------|
| `./ank -k apply config.yaml` | Apply with validation ✅ |
| `SKIP_VALIDATION=1 ./ank -k apply config.yaml` | Apply without validation |
| `./ank get workloads` | Get workloads (standard ank) |
| `./ank state` | Get state (standard ank) |

---

## 📞 Troubleshooting

### Dashboard Not Available
```
Warning: Dashboard not available
Config will still apply (validation skipped)
```
**Solution**: Start dashboard with `./run_dashboard.sh`

### curl or jq Not Available
```
Error: curl/jq not found
```
**Solution**: Install with `sudo apt-get install curl jq`

### Permission Denied
```
bash: ./ank: Permission denied
```
**Solution**: Make executable with `chmod +x ank`

### Command Not Found
```
ank: command not found
```
**Solution**: Use `./ank` or add to PATH

---

## 🎉 You're Done!

Your system is now set up with:

✅ Your original command syntax (`./ank -k apply config/test.yaml`)
✅ Automatic validation on every deployment
✅ Auto-healing of common issues
✅ Full activity logging
✅ 100% backward compatible

**Start using it immediately**:
```bash
./ank -k apply config/test.yaml
```

---

## 📚 Additional Resources

- **Usage Guide**: `ANK_WRAPPER_USAGE.md`
- **Validation Guide**: `VALIDATION_AND_HEALING_GUIDE.md`
- **API Reference**: `QUICK_REFERENCE.md`
- **Full Index**: `INDEX.md`

---

**Ready to deploy!** 🚀
