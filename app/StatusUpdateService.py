import threading
import time
from Logger import Logger

class StatusUpdateService:
    """Background service to update pending activity log statuses"""
    
    def __init__(self, activity_logger, ank_comm_service, check_interval=10):
        self.activity_logger = activity_logger
        self.ank_comm_service = ank_comm_service
        self.check_interval = check_interval  # seconds
        self.logger = Logger.get_custom_logger()
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the background status update service"""
        if self.running:
            self.logger.warning("Status update service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"Status update service started (checking every {self.check_interval}s)")
    
    def stop(self):
        """Stop the background status update service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Status update service stopped")
    
    def _update_loop(self):
        """Main loop that checks and updates pending logs"""
        while self.running:
            try:
                self._check_and_update_pending_logs()
            except Exception as e:
                self.logger.error(f"Error in status update loop: {e}")
            
            # Sleep for the check interval
            time.sleep(self.check_interval)
    
    def _check_and_update_pending_logs(self):
        """Check pending logs and update their status"""
        pending_logs = self.activity_logger.get_pending_logs(limit=50)
        
        self.logger.info(f"Status update check - found {len(pending_logs)} pending logs")
        
        if not pending_logs:
            return
        
        for log in pending_logs:
            workload_name = log['workload_name']
            log_id = log['id']
            
            self.logger.info(f"Checking status for workload: {workload_name} (log_id: {log_id})")
            
            # Check current status from Ankaios
            current_status = self.ank_comm_service.check_workload_status(workload_name)
            
            self.logger.info(f"Workload {workload_name} status: {current_status}")
            
            # Only update if status has changed from pending
            if current_status != "pending":
                success = self.activity_logger.update_log_status(log_id, current_status)
                if success:
                    self.logger.info(f"✓ Updated log {log_id} ({workload_name}): pending -> {current_status}")
                else:
                    self.logger.error(f"✗ Failed to update log {log_id} ({workload_name})")
            else:
                self.logger.info(f"Workload {workload_name} still pending, will check again later")