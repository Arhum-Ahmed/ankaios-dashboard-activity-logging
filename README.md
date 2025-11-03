# Ankaios Dashboard Extensions

**Course:** ENGR 5550G - Software Testing and Quality Assurance  
**Team:** Bug Hunters  
**Instructor:** Prof. Mohamed El-Darieby

---

## Overview

This project extends the Eclipse Ankaios Dashboard with two major features:

1. **Activity Logger** - Tracks all workload operations with SQLite persistence
2. **Configuration Validator** - Pre-deployment validation using graph algorithms (DFS-based cycle detection)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- jq (for CLI integration)

### Start Dashboard
```bash
./run_dashboard.sh
```

### Stop Dashboard
```bash
./stop_dashboard
```

### Access Dashboard
```
http://localhost:5001
```

---

## Features

### Phase 1: Activity Logger
- Automatic logging of workload operations (add/delete/update)
- User tracking and execution status monitoring
- Filter logs by action, workload, user, date
- Export logs as CSV

### Phase 2: Configuration Validator
- **Schema Validation** - Validates YAML against Ankaios specification
- **Dependency Graph Analysis** - Graph-based dependency validation
- **Circular Dependency Detection** - DFS algorithm with O(V+E) complexity
- **Resource Conflict Detection** - Port and name conflict checking
- **REST API** - `/api/validate-config` endpoint for programmatic access
- **CLI Integration** - Pre-deployment validation gate

---

## CLI Integration

### Automatic Pre-Deployment Validation

Add this to your `~/.bashrc` or `~/.zshrc`:
```bash
# Save actual ank binary path
ANK_BIN=$(which ank)

# Override ank with validation
ank() {
    if [[ " $* " =~ " apply " ]]; then
        local config_file="${@: -1}"
        
        echo "🔍 Validating configuration before deployment..."
        
        local config_content=$(cat "$config_file" 2>/dev/null)
        if [ $? -ne 0 ]; then
            echo "❌ Error: Cannot read file '$config_file'"
            return 1
        fi
        
        local response=$(curl -s -X POST http://localhost:5001/api/validate-config \
            -H "Content-Type: application/json" \
            -d "{\"config\": $(jq -Rs . <<< "$config_content")}")
        
        local status=$(echo "$response" | jq -r '.overall_status')
        
        if [ "$status" == "PASSED" ]; then
            echo "✅ Validation passed. Deploying..."
            "$ANK_BIN" "$@"
        else
            echo "❌ Validation FAILED:"
            echo "$response" | jq -r '.tests[] | select(.status == "FAILED") | .issues[] | "  - \(.message)"'
            return 1
        fi
    else
        "$ANK_BIN" "$@"
    fi
}
```

**Activate:**
```bash
source ~/.bashrc
```

**Usage:**
```bash
# Your normal command - validation happens automatically!
ank -k apply config/test.yaml
```

---

## API Endpoints

### Activity Logger
- `GET /activityLogs` - Retrieve activity logs with optional filters
- `GET /exportLogs` - Export logs as CSV

### Configuration Validator
- `POST /api/validate-config` - Validate workload configuration

**Example Request:**
```bash
curl -X POST http://localhost:5001/api/validate-config \
  -H "Content-Type: application/json" \
  -d '{
    "config": "apiVersion: v0.1\nworkloads:\n  nginx:\n    runtime: podman\n    agent: agent_A"
  }' | jq
```

---

## Testing

### Run Functional Tests
```bash
cd tests/pytests
pytest test_uat_system.py -v
```

### Run Performance Benchmarks
```bash
cd tests/pytests
pytest perf_benchmark.py -v --benchmark-only
```

### Run Load Tests (Locust)
```bash
cd tests/locust
locust -f locustfile.py \
  --host=http://localhost:5001 \
  --headless \
  --users 10 \
  --spawn-rate 2 \
  --run-time 60s \
  --html report_locust.html \
  --csv report_locust
```

### Test Results
- **Total Tests:** 34 (18 functional, 16 non-functional)
- **Pass Rate:** 100%
- **Performance:** Average 50ms response time (< 500ms target)
- **Load Test:** 0% error rate with 50 concurrent users
- **Algorithm Complexity:** O(V+E) verified empirically

---

## Project Structure
```
app/
├── ActivityLogger.py                  # Activity logging module
├── validators/                        # Configuration validation
│   ├── schema_validator.py
│   ├── dependency_validator.py       # DFS cycle detection
│   ├── conflict_detector.py
│   └── test_executor.py
├── AnkCommunicationService.py         # Modified for logging
└── DashboardAPI.py                    # REST endpoints

tests/
├── pytests/
│   ├── test_uat_system.py            # Functional & UAT tests
│   └── perf_benchmark.py             # Performance benchmarks
└── locust/
    └── locustfile.py                 # Load testing
```

---

## Algorithm Details

**Circular Dependency Detection:**
- **Algorithm:** Depth-First Search (DFS) with color marking
- **Time Complexity:** O(V + E) where V = workloads, E = dependencies
- **Space Complexity:** O(V) for color and parent tracking
- **Verification:** Linear scaling confirmed through empirical testing

---

## Contributors

**Bug Hunters Team:**
- Arhum Ahmed (100947799)
- Maliha Bilal (100985340)
- Parnia Azam Sadeghi (100989023)
- Revathi Sekar (100948672)
- Shivam Patel (101003473)

---