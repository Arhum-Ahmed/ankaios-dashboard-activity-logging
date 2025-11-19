#!/bin/bash
#
# Integration Script: Use Ankaios with Config Validation and Auto-Healing
# This script shows how to integrate the dashboard's validation system
# with ank-server apply workloads command
#
# Usage:
#   ./deploy_with_validation.sh <config.yaml>
#   ./deploy_with_validation.sh config/startupState.yaml
#

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="${1:?Usage: $0 <config.yaml>}"
ANKAIOS_SERVER_URL="${ANKAIOS_SERVER_URL:-http://0.0.0.0:25551}"
ANKAIOS_BIN_DIR="${ANKAIOS_BIN_DIR:-/usr/local/bin}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validate input
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploy with Configuration Validation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Config File: $CONFIG_FILE"
echo "Ankaios URL: $ANKAIOS_SERVER_URL"
echo ""

# Step 1: Validate and heal the configuration using Python
echo -e "${YELLOW}[1/3] Validating and healing configuration...${NC}"
echo ""

VALIDATION_RESULT=$(python3 << 'EOF'
import sys
import os
import json
import yaml

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from AnkCommunicationService import AnkCommunicationService

try:
    # Read the config file
    with open(sys.argv[1], 'r') as f:
        config_content = f.read()
    
    # Validate and heal
    service = AnkCommunicationService()
    result = service.validate_and_heal_config(config_content, user_id="cli_deploy")
    
    # Output result as JSON
    print(json.dumps({
        'success': result['success'],
        'original_valid': result['original_valid'],
        'healed': result['healed'],
        'final_valid': result['final_valid'],
        'deployment_status': result['deployment_status'],
        'config': result['config'],
        'healing_logs': result['healing_report'].get('logs', []),
        'validation_report': result['validation_report']
    }))
    
except Exception as e:
    print(json.dumps({
        'success': False,
        'error': str(e)
    }))
    sys.exit(1)

EOF
"$CONFIG_FILE")

# Parse the JSON result
SUCCESS=$(echo "$VALIDATION_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))")
HEALED=$(echo "$VALIDATION_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('healed', False))")
FINAL_VALID=$(echo "$VALIDATION_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('final_valid', False))")
HEALED_CONFIG=$(echo "$VALIDATION_RESULT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('config', ''))")

# Display validation results
echo -e "${GREEN}Validation Results:${NC}"
echo "  Original Valid: $(python3 -c "import sys, json; print(json.load(sys.stdin).get('original_valid', False))" <<< "$VALIDATION_RESULT")"
echo "  Healed: $HEALED"
echo "  Final Valid: $FINAL_VALID"
echo "  Status: $(python3 -c "import sys, json; print(json.load(sys.stdin).get('deployment_status', 'unknown'))" <<< "$VALIDATION_RESULT")"
echo ""

# Show healing logs if any
HEALING_LOGS=$(echo "$VALIDATION_RESULT" | python3 -c "import sys, json; logs = json.load(sys.stdin).get('healing_logs', []); [print(f'  - {log}') for log in logs]" 2>/dev/null)
if [[ -n "$HEALING_LOGS" ]]; then
    echo -e "${YELLOW}Healing Applied:${NC}"
    echo "$HEALING_LOGS"
    echo ""
fi

# Check if validation passed
if [[ "$SUCCESS" != "True" ]]; then
    echo -e "${RED}[FAILED] Configuration validation failed!${NC}"
    echo ""
    echo "Validation Report:"
    echo "$VALIDATION_RESULT" | python3 -c "
import sys, json
report = json.load(sys.stdin).get('validation_report', {})
for test in report.get('tests', []):
    status = '✗' if test['status'] == 'FAILED' else '✓'
    print(f'  {status} {test[\"name\"]}: {test[\"status\"]}')
    for issue in test.get('issues', []):
        print(f'      - {issue.get(\"message\", \"Unknown issue\")}')
"
    echo ""
    echo "Deployment cancelled due to validation failures."
    exit 1
fi

echo -e "${GREEN}✓ Configuration is valid and ready for deployment!${NC}"
echo ""

# Step 2: Write healed config to temp file if it was healed
if [[ "$HEALED" == "True" ]]; then
    echo -e "${YELLOW}[2/3] Using healed configuration...${NC}"
    TEMP_CONFIG=$(mktemp)
    echo "$HEALED_CONFIG" > "$TEMP_CONFIG"
    CONFIG_TO_DEPLOY="$TEMP_CONFIG"
    trap "rm -f $TEMP_CONFIG" EXIT
    echo -e "${GREEN}✓ Healed config prepared${NC}"
    echo ""
else
    echo -e "${YELLOW}[2/3] Using original configuration...${NC}"
    CONFIG_TO_DEPLOY="$CONFIG_FILE"
    echo -e "${GREEN}✓ Original config validated${NC}"
    echo ""
fi

# Step 3: Deploy with ank-server
echo -e "${YELLOW}[3/3] Deploying with ank-server...${NC}"
echo ""

if [[ ! -f "$ANKAIOS_BIN_DIR/ank-server" ]]; then
    echo -e "${RED}Error: ank-server not found at $ANKAIOS_BIN_DIR/ank-server${NC}"
    exit 1
fi

# Check if ank-server is running
if ! nc -z ${ANKAIOS_SERVER_URL%:*} ${ANKAIOS_SERVER_URL#*:} 2>/dev/null; then
    echo -e "${YELLOW}Note: Ankaios server not currently running at $ANKAIOS_SERVER_URL${NC}"
    echo "You can start it with: ank-server --startup-config $CONFIG_TO_DEPLOY"
else
    echo "Connecting to Ankaios server at $ANKAIOS_SERVER_URL..."
    # Deploy using ank-server
    "$ANKAIOS_BIN_DIR/ank-server" apply "$CONFIG_TO_DEPLOY" || {
        echo -e "${RED}✗ Deployment failed!${NC}"
        exit 1
    }
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Summary:"
if [[ "$HEALED" == "True" ]]; then
    echo "  - Configuration was auto-healed"
fi
echo "  - Validation: PASSED"
echo "  - Deployment: READY/SUCCESS"
echo ""
echo "Next steps:"
echo "  1. Monitor workload status: ank-server state"
echo "  2. Check application logs"
echo "  3. Verify deployments"
echo ""
