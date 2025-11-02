#!/bin/bash
# test_api.sh - Comprehensive API testing

echo "=========================================="
echo "Configuration Validator API Test Suite"
echo "=========================================="
echo ""

# Test 1: Valid Configuration
echo "Test 1: Valid Configuration"
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "apiVersion: v0.1\nworkloads:\n  nginx:\n    runtime: podman\n    agent: agent_A\n    runtimeConfig: \"image: nginx:latest\""
  }' | jq '.overall_status'
echo ""

# Test 2: Invalid YAML Syntax
echo "Test 2: Invalid YAML Syntax"
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  nginx:\n    runtime podman"
  }' | jq '.tests[0].status'
echo ""

# Test 3: Missing Required Fields
echo "Test 3: Missing Required Fields"
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  nginx:\n    agent: agent_A"
  }' | jq '.tests[0].issues[0].message'
echo ""

# Test 4: Invalid Runtime
echo "Test 4: Invalid Runtime Value"
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  nginx:\n    runtime: invalid_runtime\n    agent: agent_A"
  }' | jq '.tests[0].issues'
echo ""

# Test 5: Circular Dependencies
echo "Test 5: Circular Dependency Detection"
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  A:\n    runtime: podman\n    agent: agent_A\n    dependencies:\n      B: {}\n  B:\n    runtime: podman\n    agent: agent_A\n    dependencies:\n      C: {}\n  C:\n    runtime: podman\n    agent: agent_A\n    dependencies:\n      A: {}"
  }' | jq '.tests[2].status'
echo ""

# Test 6: Missing Dependencies
echo "Test 6: Missing Dependency Detection"
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  app:\n    runtime: podman\n    agent: agent_A\n    dependencies:\n      database: {}"
  }' | jq '.tests[1].issues[0].type'
echo ""

# Test 7: Port Conflicts
echo "Test 7: Port Conflict Detection"
# First, would need to get current state, simplified for demo
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  nginx:\n    runtime: podman\n    agent: agent_A\n    runtimeConfig: \"commandOptions: [\\\"-p\\\", \\\"8080:80\\\"]\""
  }' | jq '.tests[3].status'
echo ""

# Test 8: Performance - Response Time
echo "Test 8: Response Time Check"
time curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "workloads:\n  nginx:\n    runtime: podman\n    agent: agent_A"
  }' -o /dev/null -s
echo ""

echo "=========================================="
echo "API Tests Complete"
echo "=========================================="