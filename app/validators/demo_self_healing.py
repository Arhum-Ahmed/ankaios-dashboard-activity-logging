import os
from app.validators.test_executor import SelfHealingPreDeploymentTester
from app.validators.validation_report_formatter import ValidationReportFormatter


if __name__ == "__main__":
    # Get the path to the config file relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "../../config/testhealing.yaml")

    with open(config_path) as f:# <-- point to new test file
        config_yaml = f.read()

    tester = SelfHealingPreDeploymentTester(current_workloads=[])
    results = tester.run_with_remediation(config_yaml)

    # Handle both cases: issues or no issues
    initial_report = results.get("initial_report") or results.get("report")
    post_report = results.get("post_remediation_report") or results.get("report")
    remediation_log = results.get("remediation_log", [])
    fixed_config = results.get("remediated_config", config_yaml)

    ValidationReportFormatter.display_report(initial_report)
    ValidationReportFormatter.display_remediation_log(remediation_log)
    ValidationReportFormatter.display_final_result(post_report)
    ValidationReportFormatter.display_fixed_config(fixed_config)