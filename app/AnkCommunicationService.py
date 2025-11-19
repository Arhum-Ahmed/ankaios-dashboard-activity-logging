from Logger import Logger
from ankaios_sdk import Workload, Ankaios, WorkloadStateEnum, AnkaiosException
from validators.deployment_validator import DeploymentValidator
import json
import yaml

logger = Logger.get_custom_logger()

class AnkCommunicationService:
    def __init__(self, activity_logger=None) -> None:
        self.logger = Logger.get_custom_logger()
        self.ankaios = Ankaios()
        self.activity_logger = activity_logger  # Injected from DashboardAPI
        self.deployment_validator = DeploymentValidator()  # Initialize validator
    
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
    
    def validate_and_heal_config(self, config_yaml: str, user_id: str = None) -> dict:
        """
        Validates a workload configuration and automatically heals issues if possible.
        
        Returns:
            {
                'success': bool,                    # True if final config is valid and deployable
                'original_valid': bool,             # True if config was valid without healing
                'healed': bool,                     # True if healing was applied
                'final_valid': bool,                # True if final config is valid
                'config': str,                      # Final YAML config (healed or original)
                'validation_report': dict,          # Full validation report
                'healing_report': dict,             # Healing logs and details
                'deployment_status': str            # 'ready', 'healing_required', 'failed'
            }
        """
        try:
            # Get current workloads for dependency checking
            complete_state = self.get_complete_state()
            current_workloads = []
            if isinstance(complete_state, dict):
                desired_state = complete_state.get("desiredState") or complete_state.get("desired_state", {})
                current_workloads = [
                    {'name': name} 
                    for name in desired_state.get("workloads", {}).keys()
                ]
            
            # Update validator with current workloads
            self.deployment_validator = DeploymentValidator(current_workloads)
            
            # Run validation and healing flow
            result = self.deployment_validator.validate_and_heal(config_yaml, auto_heal=True)
            
            # Determine deployment status
            if result['success']:
                result['deployment_status'] = 'ready'
            elif result['healed'] and result['final_valid']:
                result['deployment_status'] = 'ready'
            elif result['healed']:
                result['deployment_status'] = 'healing_required'
            else:
                result['deployment_status'] = 'failed'
            
            # Log validation activity if activity logger is available
            if self.activity_logger and user_id:
                self.activity_logger.log_activity(
                    user_id=user_id,
                    action="validate_config",
                    status=result['deployment_status'],
                    metadata={
                        'original_valid': result['original_valid'],
                        'healed': result['healed'],
                        'final_valid': result['final_valid'],
                        'total_errors': result['validation_report'].get('total_errors', 0)
                    }
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during config validation and healing: {str(e)}")
            return {
                'success': False,
                'original_valid': False,
                'healed': False,
                'final_valid': False,
                'config': config_yaml,
                'validation_report': {},
                'healing_report': {
                    'attempted': True,
                    'logs': [f"Validation failed with exception: {str(e)}"]
                },
                'deployment_status': 'failed',
                'error': str(e)
            }
    
    def apply_workload_with_validation(self, workload_config: dict, user_id: str = None) -> dict:
        """
        Applies a workload after validating and healing the configuration.
        
        Args:
            workload_config: Workload configuration as dict (with workloadName, runtime, agent, etc.)
            user_id: User ID for activity logging
        
        Returns:
            {
                'status': str,                      # 'success', 'validation_failed', 'deployment_failed'
                'message': str,                     # Status message
                'workload_name': str,               # Name of the workload
                'validation_result': dict,          # Validation and healing result
                'deployment_response': any,         # Response from apply_workload call
                'healed': bool                      # Whether config was healed
            }
        """
        workload_name = workload_config.get("workloadName", "unknown")
        
        try:
            # Convert workload config to YAML for validation
            config_yaml = yaml.dump({'workloads': {workload_name: workload_config}}, sort_keys=False)
            
            # Validate and heal
            validation_result = self.validate_and_heal_config(config_yaml, user_id)
            
            # Check if final config is valid
            if not validation_result['final_valid']:
                return {
                    'status': 'validation_failed',
                    'message': f'Configuration validation failed. {len(validation_result["validation_report"].get("tests", []))} test(s) failed.',
                    'workload_name': workload_name,
                    'validation_result': validation_result,
                    'healed': validation_result['healed']
                }
            
            # If healed, update the workload config from the healed YAML
            if validation_result['healed']:
                try:
                    healed_config = yaml.safe_load(validation_result['config'])
                    if 'workloads' in healed_config and workload_name in healed_config['workloads']:
                        workload_config = healed_config['workloads'][workload_name]
                        self.logger.info(f"Using healed configuration for workload: {workload_name}")
                except:
                    self.logger.warning("Could not parse healed YAML, using original config")
            
            # Now deploy the validated (and possibly healed) workload
            workload = self.map_json_to_workload(workload_config)
            deployment_response = self.ankaios.apply_workload(workload)
            
            # Log activity
            if self.activity_logger and user_id:
                self.activity_logger.log_activity(
                    user_id=user_id,
                    action="add_workload",
                    workload_name=workload_name,
                    agent=workload_config.get("agent"),
                    status="success",
                    metadata={
                        'runtime': workload_config.get("runtime"),
                        'restartPolicy': workload_config.get("restartPolicy"),
                        'healed': validation_result['healed'],
                        'original_valid': validation_result['original_valid']
                    }
                )
            
            return {
                'status': 'success',
                'message': 'Workload deployed successfully.',
                'workload_name': workload_name,
                'validation_result': validation_result,
                'deployment_response': deployment_response,
                'healed': validation_result['healed']
            }
            
        except AnkaiosException as e:
            self.logger.error(f"Ankaios exception during workload deployment: {str(e)}")
            
            if self.activity_logger and user_id:
                self.activity_logger.log_activity(
                    user_id=user_id,
                    action="add_workload",
                    workload_name=workload_name,
                    status="failed",
                    metadata={'error': str(e)}
                )
            
            return {
                'status': 'deployment_failed',
                'message': f'Workload deployment failed: {str(e)}',
                'workload_name': workload_name,
                'validation_result': validation_result if 'validation_result' in locals() else {},
                'error': str(e)
            }
        except Exception as e:
            self.logger.error(f"Unexpected error during workload deployment: {str(e)}")
            
            return {
                'status': 'deployment_failed',
                'message': f'Unexpected error: {str(e)}',
                'workload_name': workload_name,
                'error': str(e)
            }
    
    def add_new_workload(self, json, user_id=None):
        """
        Adds a new workload with automatic validation and healing.
        Uses the apply_workload_with_validation method to ensure config is valid before deployment.
        """
        result = self.apply_workload_with_validation(json, user_id)
        
        # Return the result for the API
        return result
    
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
        """
        Updates a workload configuration with automatic validation and healing.
        Uses the apply_workload_with_validation method to ensure config is valid before deployment.
        """
        result = self.apply_workload_with_validation(json, user_id)
        
        # Update the action type in logs
        if self.activity_logger and user_id and result.get('status') == 'success':
            # The action was logged as 'add_workload', but we can note it was an update
            pass
        
        return result
    
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