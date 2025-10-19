# Ankaios Activity Logger Extension

## Overview
The Activity Logger Extension adds comprehensive activity tracking to the Ankaios Dashboard, automatically logging all workload-related operations with detailed metadata including user, timestamp, workload details, and execution status.

## Features
- **Automatic Logging**: Captures add, delete, and update operations on workloads
- **User Tracking**: Records which user performed each action
- **Execution Status**: Monitors actual workload execution state (success/failed/pending)
- **Filtering**: Filter logs by action type, workload name, user, and date range
- **Export**: Download activity logs as CSV for external analysis
- **Real-time UI**: Browse and search logs through an intuitive web interface

## Architecture

### Components Added/Modified
1. **ActivityLogger.py** - Core logging module with SQLite persistence
2. **Modified AnkCommunicationService.py** - Integrated logging into workload operations
3. **Modified DashboardAPI.py** - Added REST endpoints for log retrieval and export
4. **ActivityLogView.vue** - Frontend UI component for viewing and filtering logs

### Database Schema
```sql
CREATE TABLE activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    workload_name TEXT,
    agent TEXT,
    status TEXT,
    metadata TEXT
);
```

### API Endpoints
- `GET /activityLogs` - Retrieve logs with optional filters (action, workload, user, date range)
- `GET /exportLogs` - Export filtered logs as CSV

## Installation

### Files Added/Modified
```
app/
├── ActivityLogger.py (NEW)
├── AnkCommunicationService.py (MODIFIED)
├── DashboardAPI.py (MODIFIED)
└── client/src/components/
    ├── ActivityLogView.vue (NEW)
    └── DrawerItems.vue (MODIFIED)

client/src/router/routes.js (MODIFIED)
```

### Setup Steps
1. Clone the repo
2. Build the Docker image:
   ```bash 
   ./run_dashboard.sh
   ```
3. Access the Activity Logs via the dashboard menu

## Usage

### Viewing Activity Logs
1. Navigate to **Activity Logs** in the dashboard drawer menu
2. View all logged activities in a paginated table
3. Use filters to narrow down results:
   - **Action**: Filter by add_workload, delete_workload, or update_config
   - **Workload Name**: Search by workload name
   - **User ID**: Filter by specific user

### Exporting Logs
1. Apply desired filters (optional)
2. Click **Export CSV** button
3. Download includes all filtered results

### Logged Actions
- **add_workload**: When a new workload is created
- **delete_workload**: When a workload is removed
- **update_config**: When workload configuration is modified

### Status Values
- **success**: Workload operation completed successfully
- **failed**: Workload operation or execution failed
- **pending**: Workload submitted but execution state unclear
- **unknown**: Unable to determine execution state

## Integration with Ankaios

The Activity Logger integrates at the API layer, capturing all operations performed through the dashboard:

```
User Action → Dashboard UI → Flask API → AnkCommunicationService → Ankaios Server
                                 ↓
                          ActivityLogger
                                 ↓
                          SQLite Database
```

## Testing

### Test Scenarios
1. **Add Workload**: Create a workload via dashboard → Verify log entry with "add_workload" action
2. **Delete Workload**: Remove a workload → Verify log entry with "delete_workload" action
3. **Update Config**: Modify workload settings → Verify log entry with "update_config" action
4. **Filter Logs**: Apply filters and verify results match criteria
5. **Export**: Download CSV and verify data integrity


## Contributors
Group:Bug Hunters - Software Testing & QA Course Project