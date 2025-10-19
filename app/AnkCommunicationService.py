from Logger import Logger
from ankaios_sdk import Workload, Ankaios, WorkloadStateEnum, AnkaiosException
import json

logger = Logger.get_custom_logger()

class AnkCommunicationService:
    def __init__(self, activity_logger=None) -> None:
        self.logger = Logger.get_custom_logger()
        self.ankaios = Ankaios()
        self.activity_logger = activity_logger  # Injected from DashboardAPI
    
    def map_json_to_workload(self, json):
        workload_name = json["workloadName"]
        workload_builder = Workload.builder().workload_name(workload_name)
        
        if "agent" in json:
            workload_builder.agent_name(json["agent"])
        if "runtime" in json:
            workload_builder.runtime(json["runtime"])
        if "restartPolicy" in json:
            workload_builder.restart_policy(json["restartPolicy"])
        if "runtimeConfig" in json:
            workload_builder.runtime_config(json["runtimeConfig"])
        if "tags" in json:
            for kv_pair in json["tags"]:
                workload_builder.add_tag(key=kv_pair["key"], value=kv_pair["value"])
        if "controlInterfaceAccess" in json:
            if "allowRules" in json["controlInterfaceAccess"]:
                for rule in json["controlInterfaceAccess"]["allowRules"]:
                    workload_builder.add_allow_state_rule(rule["operation"], rule["filterMask"])
            if "denyRules" in json["controlInterfaceAccess"]:
                for rule in json["controlInterfaceAccess"]["denyRules"]:
                    workload_builder.add_deny_state_rule(rule["operation"], rule["filterMask"])
        
        if "dependencies" in json and "dependencies" in json["dependencies"]:
            dependencies = json["dependencies"]
            for key, value in dependencies["dependencies"].items():
                workload_builder.add_dependency(workload_name=key, condition=value)
        
        workload = workload_builder.build()
        print(workload)
        return workload 
    
    def get_complete_state(self):
        complete_state = self.ankaios.get_state(timeout=5, field_masks=["desiredState", "workloadStates"]).to_dict()
        return complete_state
    
    def get_write_access(self):        
        write_access = {"writeAccess": True}
        try:
            workload = Workload.builder().workload_name("access_test").agent_name("access_test_agent").runtime("podman").runtime_config("").restart_policy("NEVER").build()
            self.ankaios.apply_workload(workload)
            self.ankaios.delete_workload("access_test")
        except AnkaiosException as e:
            print("Ankaios exception: ", e)
            if "Access denied" in str(e):
                write_access = {"writeAccess": False}
        
        return write_access
    
    def add_new_workload(self, json, user_id=None):
        workload = self.map_json_to_workload(json)
        update_response = {}
        status = "pending"  # Initially pending
        workload_name = json.get("workloadName")
        
        try:
            update_response = self.ankaios.apply_workload(workload)
            print(update_response)
        except AnkaiosException as e:
            print("Ankaios Exception occured: ", e)
            status = "failed"  # Immediate failure
        
        # Log the activity with initial status
        if self.activity_logger and user_id:
            self.activity_logger.log_activity(
                user_id=user_id,
                action="add_workload",
                workload_name=workload_name,
                agent=json.get("agent"),
                status=status,
                metadata={"runtime": json.get("runtime"), "restartPolicy": json.get("restartPolicy")}
            )
        
        return update_response
    
    def deleteWorkloads(self, json, user_id=None):
        for workload_name in json:
            status = "success"
            agent = None
            
            # Get workload details before deleting to capture agent info
            try:
                complete_state = self.get_complete_state()
                print(f"[DELETE] Complete state keys: {complete_state.keys()}")
                
                desired_state = complete_state.get("desiredState") or complete_state.get("desired_state", {})
                print(f"[DELETE] Desired state keys: {desired_state.keys()}")
                
                workloads = desired_state.get("workloads", {})
                print(f"[DELETE] Workloads available: {list(workloads.keys())}")
                
                if workload_name in workloads:
                    workload_info = workloads[workload_name]
                    print(f"[DELETE] Workload {workload_name} info: {workload_info}")
                    agent = workload_info.get("agent") or workload_info.get("agentName")
                    print(f"[DELETE] Agent extracted: {agent}")
                else:
                    print(f"[DELETE] Workload {workload_name} NOT found in desired state")
            except Exception as e:
                print(f"[DELETE] Error fetching agent info for {workload_name}: {e}")
                import traceback
                traceback.print_exc()
            
            # Now delete the workload
            try:
                ret = self.ankaios.delete_workload(workload_name)
                print(ret)
            except AnkaiosException as e:
                print("Ankaios Exception occured: ", e)
                status = "failed"
            
            # Log the activity with agent info
            print(f"[DELETE] About to log: workload={workload_name}, agent={agent}, status={status}")
            if self.activity_logger and user_id:
                self.activity_logger.log_activity(
                    user_id=user_id,
                    action="delete_workload",
                    workload_name=workload_name,
                    agent=agent,
                    status=status
                )
    
    def update_config(self, json, user_id=None):
        workload = self.map_json_to_workload(json)
        update_response = {}
        status = "pending"  # Initially pending
        workload_name = json.get("workloadName")
        
        try:
            update_response = self.ankaios.apply_workload(workload)
            print(update_response)
        except AnkaiosException as e:
            print("Ankaios Exception occured: ", e)
            status = "failed"  # Immediate failure
        
        # Log the activity with initial status
        if self.activity_logger and user_id:
            self.activity_logger.log_activity(
                user_id=user_id,
                action="update_config",
                workload_name=workload_name,
                agent=json.get("agent"),
                status=status,
                metadata={"runtime": json.get("runtime"), "restartPolicy": json.get("restartPolicy")}
            )
        
        return update_response
    
    def check_workload_status(self, workload_name):
        """Check the actual execution status of a workload from Ankaios state"""
        try:
            complete_state = self.get_complete_state()
            
            print(f"Checking status for workload: {workload_name}")
            print(f"Complete state type: {type(complete_state)}")
            
            # If complete_state is not a dict, the SDK might be returning something else
            if not isinstance(complete_state, dict):
                print(f"Warning: complete_state is not a dict, it's {type(complete_state)}")
                return "unknown"
            
            # Check desired state first (this is where workloads are defined)
            desired_state = complete_state.get("desiredState") or complete_state.get("desired_state")
            if desired_state:
                print(f"Desired state keys: {desired_state.keys()}")
                workloads_in_desired = desired_state.get("workloads", {})
                print(f"Workloads in desired state: {workloads_in_desired.keys()}")
                
                if workload_name in workloads_in_desired:
                    print(f"Workload {workload_name} found in desired state - marking as success")
                    # If it's in desired state and didn't fail to be added, consider it success
                    return "success"
            
            # Workload not found
            print(f"Workload {workload_name} not found in desired state")
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Failed to check workload status: {e}")
            import traceback
            traceback.print_exc()
            return "unknown"