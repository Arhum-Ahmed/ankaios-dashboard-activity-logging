# validators/validation_report_formatter.py

import yaml
import json

class ValidationReportFormatter:
    """Utility class to print validation and remediation reports clearly."""

    @staticmethod
    def display_report(report):
        print("\n🔍 === INITIAL VALIDATION REPORT ===")
        print(json.dumps(report, indent=4))

    @staticmethod
    def display_remediation_log(logs):
        print("\n🩺 === REMEDIATION ACTIONS ===")
        if not logs:
            print("No remediation actions taken.")
        else:
            for line in logs:
                print(f"- {line}")

    @staticmethod
    def display_final_result(report):
        print("\n✅ === POST-REMEDIATION VALIDATION REPORT ===")
        print(json.dumps(report, indent=4))

    @staticmethod
    def display_fixed_config(config_yaml):
        print("\n🧾 === REMEDIATED CONFIGURATION ===")
        try:
            parsed = yaml.safe_load(config_yaml)
            print(yaml.dump(parsed, sort_keys=False))
        except Exception:
            print(config_yaml)