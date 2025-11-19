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
                    # If dependencies is now empty, remove the field entirely
                    if not w["dependencies"]:
                        w.pop("dependencies", None)

            # ---- FIX 6b: Self-dependency ----
            elif issue.get('type') == 'SELF_DEPENDENCY' or "cannot depend on itself" in msg:
                # remove self-dependency if present
                if "dependencies" in w and workload_name in w["dependencies"]:
                    w["dependencies"].pop(workload_name, None)
                    remediation_log.append(
                        f'Removed self-dependency from "{workload_name}".'
                    )
                    # If dependencies is now empty, remove the field entirely
                    if not w["dependencies"]:
                        w.pop("dependencies", None)

            # ---- FIX 6c: Circular dependency (simple breaker) ----
            elif issue.get('type') == 'CIRCULAR_DEPENDENCY' and isinstance(issue.get('cycle'), list):
                cycle = issue.get('cycle')
                # attempt to break cycle by removing the edge from cycle[0] -> cycle[1]
                if len(cycle) >= 2:
                    src = cycle[0]
                    dst = cycle[1]
                    if src in workloads and 'dependencies' in workloads[src] and dst in workloads[src]['dependencies']:
                        workloads[src]['dependencies'].pop(dst, None)
                        remediation_log.append(
                            f'Removed dependency "{dst}" from "{src}" to break circular dependency.'
                        )
                        # If dependencies is now empty, remove the field entirely
                        if not workloads[src]["dependencies"]:
                            workloads[src].pop("dependencies", None)

            # ---- FIX 7: Port conflicts ----
            elif "Port" in msg and "already used" in msg:
                port = issue.get("port")
                if "runtimeConfig" in w and port:
                    w["runtimeConfig"] = w["runtimeConfig"].replace(str(port), str(port + 1))
                    remediation_log.append(
                        f'Adjusted port conflict for {workload_name}: {port} → {port + 1}.'
                    )

        # ✅ Return the updated YAML and summary log
        # Auto-qualify short image names to docker.io/library/* (fixes podman short-name resolution)
        # Also replace placeholder/non-existent images (ghcr.io/example/*) with real ones
        for wname, w in workloads.items():
            if isinstance(w, dict) and 'runtimeConfig' in w and isinstance(w['runtimeConfig'], str):
                val = w['runtimeConfig']
                # Match image: <name> lines and qualify short names or replace fake images
                import re
                # Pattern: image: <spaces> <name-with-optional-tag>
                def fix_image(match):
                    prefix = match.group(1)  # 'image: '
                    image_name = match.group(2)  # e.g. 'nginx:latest' or 'ghcr.io/example/svc:1.0'
                    
                    # Replace placeholder images from ghcr.io/example/* with real alpine image
                    if 'ghcr.io/example' in image_name or '/example/' in image_name:
                        replacement = "docker.io/library/alpine:latest"
                        remediation_log.append(f'Replaced placeholder image in {wname}: "{image_name}" → "{replacement}" (non-existent registry).')
                        return f"{prefix}{replacement}"
                    
                    # If already has registry (contains /) and is not a short name, return as-is
                    if '/' in image_name:
                        return match.group(0)
                    
                    # Qualify short name (no registry specified)
                    qualified = f"docker.io/library/{image_name}"
                    remediation_log.append(f'Qualified image in {wname}: "{image_name}" → "{qualified}".')
                    return f"{prefix}{qualified}"
                
                # Apply the pattern
                val = re.sub(r'(image:\s*)([a-zA-Z0-9\-\.]+(?:[/:][a-zA-Z0-9\-\./]*)*(?::[a-zA-Z0-9\-\.]+)?)', fix_image, val)
                w['runtimeConfig'] = val

        # Normalize runtimeConfig multi-line strings and remove control chars
        for wname, w in workloads.items():
            if isinstance(w, dict) and 'runtimeConfig' in w and isinstance(w['runtimeConfig'], str):
                val = w['runtimeConfig']
                # remove carriage returns and NULs
                val = val.replace('\r', '')
                val = val.replace('\x00', '')
                # split into lines and strip leading/trailing blank lines
                lines = val.splitlines()
                # strip leading/trailing empty lines
                while lines and lines[0].strip() == '':
                    lines.pop(0)
                while lines and lines[-1].strip() == '':
                    lines.pop()
                # remove common indentation
                if lines:
                    # compute minimal indent among non-empty lines
                    indents = [len(l) - len(l.lstrip(' ')) for l in lines if l.strip()]
                    min_indent = min(indents) if indents else 0
                    cleaned = '\n'.join([l[min_indent:] for l in lines])
                else:
                    cleaned = ''
                w['runtimeConfig'] = cleaned

        # Cleanup: remove empty or invalid `dependencies` entries across workloads
        for wname, w in list(workloads.items()):
            if not isinstance(w, dict):
                continue
            if 'dependencies' in w:
                deps = w['dependencies']
                # If dependencies is not a dict, remove it
                if not isinstance(deps, dict):
                    w.pop('dependencies', None)
                    remediation_log.append(f'Removed invalid dependencies field from "{wname}" (not a mapping).')
                    continue

                # Sanitize keys and values; keep only string->mapping or string->value entries
                sanitized = {}
                for k, v in deps.items():
                    if not isinstance(k, str):
                        continue
                    # Accept maps or empty dicts; otherwise coerce to empty dict
                    if isinstance(v, dict):
                        sanitized[k] = v
                    else:
                        sanitized[k] = {}

                if not sanitized:
                    # Remove empty dependencies entirely
                    w.pop('dependencies', None)
                    remediation_log.append(f'Removed empty dependencies from "{wname}".')
                else:
                    # Replace with sanitized mapping
                    w['dependencies'] = sanitized

        # Cleanup: Remove empty dependencies dicts from all workloads (Ankaios parser expects valid structure)
        for wname, w in workloads.items():
            if isinstance(w, dict) and 'dependencies' in w:
                # If dependencies is an empty dict {}, remove it
                if not w['dependencies']:
                    w.pop('dependencies', None)
                    if wname in [issue.get('workload') for issue in issues if 'workload' in issue]:
                        # Only log if we actually removed it due to an issue
                        pass
                    else:
                        # Log cleanup if not already logged as a fix
                        if f'Removed' not in str(remediation_log):
                            remediation_log.append(f'Cleaned up empty dependencies dict in {wname}.')

        # Ensure multi-line strings are emitted as block literals (|) so runtimes accept them
        try:
            def _str_presenter(dumper, data):
                if "\n" in data:
                    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
                return dumper.represent_scalar('tag:yaml.org,2002:str', data)

            try:
                yaml.SafeDumper.add_representer(str, _str_presenter)
            except Exception:
                yaml.add_representer(str, _str_presenter)
        except Exception:
            pass

        # Use safe_dump to ensure SafeDumper (where we registered the representer) is used
        fixed_yaml = yaml.safe_dump(config, sort_keys=False, default_flow_style=False)
        if not remediation_log:
            remediation_log.append("No auto-fixes applied — configuration already valid.")
        return fixed_yaml, remediation_log