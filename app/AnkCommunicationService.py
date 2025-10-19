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
        status = "success"
        
        try:
            update_response = self.ankaios.apply_workload(workload)
            print(update_response)
        except AnkaiosException as e:
            print("Ankaios Exception occured: ", e)
            status = "failed"
        
        # Log the activity
        if self.activity_logger and user_id:
            self.activity_logger.log_activity(
                user_id=user_id,
                action="add_workload",
                workload_name=json.get("workloadName"),
                agent=json.get("agent"),
                status=status,
                metadata={"runtime": json.get("runtime"), "restartPolicy": json.get("restartPolicy")}
            )
        
        return update_response
    
    def deleteWorkloads(self, json, user_id=None):
        for workload_name in json:
            status = "success"
            try:
                ret = self.ankaios.delete_workload(workload_name)
                print(ret)
            except AnkaiosException as e:
                print("Ankaios Exception occured: ", e)
                status = "failed"
            
            # Log the activity
            if self.activity_logger and user_id:
                self.activity_logger.log_activity(
                    user_id=user_id,
                    action="delete_workload",
                    workload_name=workload_name,
                    status=status
                )
    
    def update_config(self, json, user_id=None):
        workload = self.map_json_to_workload(json)
        update_response = {}
        status = "success"
        
        try:
            update_response = self.ankaios.apply_workload(workload)
            print(update_response)
        except AnkaiosException as e:
            print("Ankaios Exception occured: ", e)
            status = "failed"
        
        # Log the activity
        if self.activity_logger and user_id:
            self.activity_logger.log_activity(
                user_id=user_id,
                action="update_config",
                workload_name=json.get("workloadName"),
                agent=json.get("agent"),
                status=status,
                metadata={"runtime": json.get("runtime"), "restartPolicy": json.get("restartPolicy")}
            )
        
        return update_response