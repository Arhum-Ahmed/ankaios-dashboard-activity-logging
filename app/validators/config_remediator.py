"""
Configuration Remediate - Auto-fixes common configuration issues
"""

import yaml
from typing import List, Tuple


class ConfigurationRemediator:
    """Attempts to auto-fix common configuration issues detected by validators."""

    def __init__(self):
        # You can add custom fix patterns here later
        self.default_agent = "agent_A"
        self.valid_runtimes = ["podman", "podman-kube"]

    def auto_fix(self, config_yaml: str, issues: List[dict]) -> Tuple[str, List[str]]:
        """
        Applies automated fixes to the configuration YAML.
        Args:
            config_yaml: original YAML text
            issues: list of issues from validators
        Returns:
            (remediated_yaml_text, remediation_log)
        """
        remediation_log = []
        try:
            config = yaml.safe_load(config_yaml)
        except Exception as e:
            return config_yaml, [f"Failed to parse YAML during remediation: {str(e)}"]

        if not isinstance(config, dict) or "workloads" not in config:
            return config_yaml, ["Invalid configuration structure — no workloads found."]

        workloads = config["workloads"]

        # Loop through all issues found in validation
        for issue in issues:
            workload_name = issue.get("workload")
            msg = issue.get("message", "")

            if workload_name not in workloads:
                continue
            w = workloads[workload_name]

            # ---- FIX 1: Missing runtime ----
            if "Field \"runtime\" is required" in msg:
                w["runtime"] = self.valid_runtimes[0]
                remediation_log.append(
                    f'Added missing "runtime" to {workload_name}: set to "{w["runtime"]}".'
                )

            # ---- FIX 2: Invalid runtime ----
            elif "Invalid runtime" in msg:
                w["runtime"] = self.valid_runtimes[0]
                remediation_log.append(
                    f'Corrected invalid runtime for {workload_name} → "{w["runtime"]}".'
                )

            # ---- FIX 3: Missing agent ----
            elif "Field \"agent\" is required" in msg:
                w["agent"] = self.default_agent
                remediation_log.append(
                    f'Added missing "agent" to {workload_name}: set to "{w["agent"]}".'
                )

            # ---- FIX 4: Naming issues ----
            elif "contains spaces" in msg or "should be lowercase" in msg:
                new_name = workload_name.replace(" ", "_").lower()
                workloads[new_name] = workloads.pop(workload_name)
                remediation_log.append(
                    f'Renamed workload "{workload_name}" → "{new_name}".'
                )

            # ---- FIX 5: Missing runtimeConfig ----
            elif "No runtimeConfig specified" in msg:
                w["runtimeConfig"] = "image: alpine:latest"
                remediation_log.append(
                    f'Inserted minimal runtimeConfig for {workload_name} ("image: alpine:latest").'
                )

            # ---- FIX 6: Missing dependency ----
            elif "depends on" in msg and "doesn't exist" in msg:
                dep_name = issue.get("dependency", "unknown")
                if "dependencies" in w:
                    w["dependencies"].pop(dep_name, None)
                remediation_log.append(
                    f'Removed invalid dependency "{dep_name}" from "{workload_name}".'
                )

            # ---- FIX 7: Port conflicts ----
            elif "Port" in msg and "already used" in msg:
                port = issue.get("port")
                if "runtimeConfig" in w and port:
                    w["runtimeConfig"] = w["runtimeConfig"].replace(str(port), str(port + 1))
                    remediation_log.append(
                        f'Adjusted port conflict for {workload_name}: {port} → {port + 1}.'
                    )

        # ✅ Return the updated YAML and summary log
        fixed_yaml = yaml.dump(config, sort_keys=False)
        if not remediation_log:
            remediation_log.append("No auto-fixes applied — configuration already valid.")
        return fixed_yaml, remediation_log
