# Using the `ank` Wrapper Script

Your original command syntax is now fully supported with automatic validation and healing!

## Quick Start

### Use Your Original Command (Exactly as Before)
```bash
./ank -k apply config/test.yaml
```

This will:
1. ✅ Validate the configuration
2. ✅ Auto-heal any fixable issues
3. ✅ Apply the workloads
4. ✅ Show validation and healing status

### Standard Ankaios Commands Still Work
```bash
./ank get workloads
./ank delete workloads <name>
# Any ank-server command works normally
```

## How It Works

### When You Run: `./ank -k apply config/test.yaml`

```
1. Configuration is validated
   ✓ YAML syntax
   ✓ Schema
   ✓ Dependencies
   ✓ Conflicts
   
2. Auto-healing applied (if needed)
   ✓ Adds missing fields
   ✓ Fixes invalid values
   
3. Configuration applied
   ✓ Workloads deployed
```

### Output Example

```bash
$ ./ank -k apply config/test.yaml
[INFO] Validating configuration: config/test.yaml
[SUCCESS] Configuration validated and auto-healed!
[INFO] Applying configuration...
[SUCCESS] Configuration applied
```

## Setup

### Add to PATH (Optional)

If you want to use just `ank` instead of `./ank`:

```bash
# Copy to /usr/local/bin
sudo cp /workspaces/ankaios-dashboard/ank /usr/local/bin/ank

# Now use it anywhere
ank -k apply config/test.yaml
```

Or add to your .bashrc:
```bash
alias ank="/workspaces/ankaios-dashboard/ank"
```

## Configuration

### Skip Validation (Optional)

If you need to skip validation for any reason:

```bash
SKIP_VALIDATION=1 ./ank -k apply config/test.yaml
```

### Custom Dashboard URL

If your dashboard is on a different URL:

```bash
DASHBOARD_URL=http://myhost:8000 ./ank -k apply config/test.yaml
```

## Requirements

The wrapper script works best with:
- `curl` - for API calls to dashboard
- `jq` - for JSON parsing

If these aren't available:
- Validation is skipped (but config still applies)
- You get a warning message

To install:
```bash
# Ubuntu/Debian
sudo apt-get install curl jq

# Alpine
apk add curl jq

# macOS
brew install curl jq
```

## Examples

### Basic Apply
```bash
./ank -k apply config/test.yaml
```

### Apply Different Config
```bash
./ank -k apply config/startupState.yaml
```

### Get Workloads Status
```bash
./ank get workloads
```

### Delete a Workload
```bash
./ank delete workloads my-app
```

### Check Server State
```bash
./ank get
```

## Troubleshooting

### "Dashboard not available" warning
- Dashboard is not running on `http://localhost:5001`
- Config will still apply normally (validation skipped)
- Start dashboard with: `./run_dashboard.sh`

### Validation failed
- Check error message for what's wrong
- The script shows which fields need fixing
- Manually fix config or let auto-healing fix it

### jq not installed
- Install with: `sudo apt-get install jq` (or brew on macOS)
- Without jq, validation info won't be pretty-printed

## Comparison: Before vs After

### Before (Your Original Way)
```bash
ank-server apply config/test.yaml
# ❌ No validation
# ❌ No auto-healing
# ❌ No error detection
```

### After (With This Wrapper)
```bash
./ank -k apply config/test.yaml
# ✅ Automatic validation
# ✅ Auto-healing of common issues
# ✅ Clear error messages
# ✅ Same familiar command syntax!
```

## Is My Original Command Still Supported?

**YES!** 100% backward compatible.

```bash
# All of these work exactly as before
./ank -k apply config/test.yaml
./ank get workloads
./ank get
./ank state
./ank delete workloads myapp
```

The only difference is you now get validation + healing bonus features!

## Next Steps

1. Try the command: `./ank -k apply config/test.yaml`
2. Check the validation output
3. See if any configurations were auto-healed
4. Review the validation logs in activity log

That's it! You're all set! 🚀
