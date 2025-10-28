import psutil
import threading
import time
import uuid
from datetime import datetime
from Logger import Logger
from ActivityLogger import ActivityLogger

class WorkloadHealthMonitor:
    def __init__(self, db_path='activity_logs.db', interval=5, cpu_thresh=90, mem_thresh=500_000_000):
        self.interval = interval
        self.cpu_thresh = cpu_thresh
        self.mem_thresh = mem_thresh
        self.logger = Logger.get_custom_logger()
        self.activity = ActivityLogger(db_path)
        self.active_runs = {}  # run_id → pid

    def start_monitoring(self, workload_name, user_id, agent, pid):
        """Start monitoring a specific workload process"""
        run_id = str(uuid.uuid4())
        start_ts = datetime.utcnow().isoformat()
        self.activity.insert_workload_run(run_id, workload_name, user_id, agent, start_ts, "running")
        self.active_runs[run_id] = pid
        t = threading.Thread(target=self._monitor_loop, args=(run_id, workload_name, user_id, pid))
        t.daemon = True
        t.start()
        self.logger.info(f"Started monitoring workload {workload_name} ({run_id})")
        return run_id

    def _monitor_loop(self, run_id, workload_name, user_id, pid):
        proc = psutil.Process(pid)
        try:
            while proc.is_running():
                cpu = proc.cpu_percent(interval=None)
                mem = proc.memory_info()
                io = proc.io_counters()
                ts = datetime.utcnow().isoformat()
                self.activity.insert_metric_snapshot(
                    run_id, ts, cpu, mem.rss, mem.vms, proc.num_threads(), io.read_bytes, io.write_bytes
                )

                # Alert conditions
                if cpu > self.cpu_thresh:
                    self.activity.log_alert(user_id, workload_name, f"High CPU usage detected: {cpu}%", "critical")
                if mem.rss > self.mem_thresh:
                    self.activity.log_alert(user_id, workload_name, f"High memory usage detected: {mem.rss/1e6:.2f} MB", "warning")

                time.sleep(self.interval)
        except psutil.NoSuchProcess:
            self.logger.warning(f"Process {pid} ended.")
        finally:
            end_ts = datetime.utcnow().isoformat()
            self.activity.update_workload_run_end(run_id, end_ts, status="completed")
            self.logger.info(f"Stopped monitoring {workload_name} ({run_id})")
            del self.active_runs[run_id]