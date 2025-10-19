import sqlite3
import json
from datetime import datetime
from Logger import Logger

class ActivityLogger:
    def __init__(self, db_path='activity_logs.db'):
        self.db_path = db_path
        self.logger = Logger.get_custom_logger()
        self._init_db()
    
    def _init_db(self):
        """Initialize the activity logs database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    workload_name TEXT,
                    agent TEXT,
                    status TEXT,
                    metadata TEXT
                )
            ''')
            conn.commit()
            conn.close()
            self.logger.info("Activity logs database initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
    
    def log_activity(self, user_id, action, workload_name=None, agent=None, status="success", metadata=None):
        """Log a workload activity"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.utcnow().isoformat()
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute('''
                INSERT INTO activity_logs (timestamp, user_id, action, workload_name, agent, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, user_id, action, workload_name, agent, status, metadata_json))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Activity logged: {action} by {user_id} on {workload_name}")
        except Exception as e:
            self.logger.error(f"Failed to log activity: {e}")
    
    def get_logs(self, limit=100, offset=0, action_filter=None, workload_filter=None, 
                 user_filter=None, start_date=None, end_date=None):
        """Retrieve activity logs with optional filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM activity_logs WHERE 1=1"
            params = []
            
            if action_filter:
                query += " AND action = ?"
                params.append(action_filter)
            
            if workload_filter:
                query += " AND workload_name LIKE ?"
                params.append(f"%{workload_filter}%")
            
            if user_filter:
                query += " AND user_id LIKE ?"
                params.append(f"%{user_filter}%")
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                log_entry = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'user_id': row['user_id'],
                    'action': row['action'],
                    'workload_name': row['workload_name'],
                    'agent': row['agent'],
                    'status': row['status'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                }
                logs.append(log_entry)
            
            conn.close()
            return logs
        except Exception as e:
            self.logger.error(f"Failed to retrieve logs: {e}")
            return []
    
    def get_total_count(self, action_filter=None, workload_filter=None, 
                        user_filter=None, start_date=None, end_date=None):
        """Get total count of logs matching filters"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM activity_logs WHERE 1=1"
            params = []
            
            if action_filter:
                query += " AND action = ?"
                params.append(action_filter)
            
            if workload_filter:
                query += " AND workload_name LIKE ?"
                params.append(f"%{workload_filter}%")
            
            if user_filter:
                query += " AND user_id LIKE ?"
                params.append(f"%{user_filter}%")
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            cursor.execute(query, params)
            count = cursor.fetchone()[0]
            
            conn.close()
            return count
        except Exception as e:
            self.logger.error(f"Failed to get log count: {e}")
            return 0
    
    def update_log_status(self, log_id, new_status):
        """Update the status of a specific log entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE activity_logs 
                SET status = ? 
                WHERE id = ?
            ''', (new_status, log_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Updated log {log_id} status to {new_status}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update log status: {e}")
            return False
    
    def get_pending_logs(self, limit=50):
        """Get logs with pending status for status update"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM activity_logs 
                WHERE status = 'pending' 
                AND action IN ('add_workload', 'update_config')
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            
            logs = []
            for row in rows:
                log_entry = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'user_id': row['user_id'],
                    'action': row['action'],
                    'workload_name': row['workload_name'],
                    'agent': row['agent'],
                    'status': row['status'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else None
                }
                logs.append(log_entry)
            
            conn.close()
            return logs
        except Exception as e:
            self.logger.error(f"Failed to retrieve pending logs: {e}")
            return []