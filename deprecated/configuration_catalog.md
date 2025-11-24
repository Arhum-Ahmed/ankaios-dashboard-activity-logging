# Configuration YAML Catalog

This document lists all YAML configuration files under `config/` in this workspace, with brief descriptions, the file contents (snippets), and remediation/testing notes you can use while demonstrating the auto-healing feature.

---

Notes:
- Use the dashboard validator endpoint `POST /api/validate-config` to get validation reports.
- The wrapper `./ank -k apply config/<file>.yaml` will attempt auto-healing, persist backups (`.bak.<ts>`), and re-run validation prior to apply.

---

Files included in this catalog (sorted):

- `bad_self_dependency.yaml`
- `bad_circular_dependency.yaml`
- `databroker.yaml`
- `demo_fail.yaml`
- `duplicate_workload_names.yaml`
- `healed_config_yaml.yaml` (empty)
- `invalid_dependency.yaml`
- `malformed_yaml.yaml`
- `missing_agent.yaml`
- `missing_runtime.yaml`
- `missing_runtimeConfig.yaml`
- `multiline_quoted_runtimeConfig.yaml`
- `port_conflict.yaml`
- `test.yaml`
- `testhealing.yaml`
- `x.yaml` (user-created wrong file)
- `speed-provider.yaml`
- `speed-consumer.yaml`
- `startupState.yaml`

(There are also similar example configs under `ankaios-dashboard-activity-logging/config/` — not duplicated here.)

---

## `bad_self_dependency.yaml`

Description: Workload declares a dependency on itself (self-dependency). This should be flagged as an error and remediator should remove or ignore the self-dependency.

Contents:

```yaml
apiVersion: v0.1
workloads:
  demo:
    runtime: podman
    agent: agent_A
    dependencies:
      demo: {}
    runtimeConfig: |
      image: alpine:latest
      command: ["/bin/sh", "-c", "echo hi"]
```

Remediation notes:
- Expected validation error: `SELF_DEPENDENCY` (or similar).
- Remediator action: remove `demo` from `dependencies` for workload `demo`.
- After healing: re-validate should PASS for dependency checks.

---

## `bad_circular_dependency.yaml`

Description: Two workloads (`A` and `B`) depend on each other, forming a direct circular dependency. The remediator should detect and break the cycle.

Contents:

```yaml
apiVersion: v0.1
workloads:
  A:
    runtime: podman
    agent: agent_A
    dependencies:
      B: {}
    runtimeConfig: |
      image: alpine:latest
  B:
    runtime: podman
    agent: agent_B
    dependencies:
      A: {}
    runtimeConfig: |
      image: alpine:latest
```

Remediation notes:
- Expected validation error: `CIRCULAR_DEPENDENCY` with cycle `[A, B]`.
- Remediator action: break the cycle by removing one edge (e.g., remove `A` from `B`'s dependencies or vice versa) and report which removal.
- After healing: circular check should pass.

---

## `databroker.yaml`

Description: Example workload that runs the databroker image. Appears syntactically correct.

Contents:

```yaml
apiVersion: v0.1
workloads:
  databroker:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: ghcr.io/eclipse/kuksa.val/databroker:0.4.1
      commandArgs: ["--insecure"]
      commandOptions: ["--net=host"]
```

Remediation notes:
- Expected: PASSED.
- Use as a control example for successful validation.

---

## `demo_fail.yaml`

Description: A previously used test fixture that was set up to fail initially; currently shows a small workload entry. Keep as a demo.

Contents:

```yaml
apiVersion: v0.1
workloads:
  demo:
    runtime: podman
    agent: agent_A
    dependencies: {}
    runtimeConfig: |-
      image: alpine:latest
      commandArgs: ["--help"]
```

Remediation notes:
- Expected: Likely PASSED by default.
- Use to test apply flow when no errors exist.

---

## `duplicate_workload_names.yaml`

Description: Intentionally has duplicate `app` keys under `workloads` (invalid YAML mapping because keys must be unique). This tests parser handling of duplicated keys.

Contents:

```yaml
apiVersion: v0.1
workloads:
  app:
    runtime: podman
    agent: agent_A
    dependencies: {}
    runtimeConfig: |
      image: ghcr.io/example/app:1.0
  app:
    runtime: podman
    agent: agent_B
    dependencies: {}
    runtimeConfig: |
      image: ghcr.io/example/app:1.1
```

Remediation notes:
- YAML parser may reject the document before validation runs; some YAML libraries take the last duplicate key and silently overwrite previous ones.
- Expected: Schema/parse error or duplicated-key warning.
- Remediator behavior: may not be able to auto-fix; manual intervention recommended (rename one workload).

---

## `healed_config_yaml.yaml`

Description: File currently empty — placeholder for demonstration of healed output.

Contents: (empty)

Remediation notes:
- Not used directly; used as a demonstration or to store output.

---

## `invalid_dependency.yaml`

Description: A workload references a `backend` dependency which is not present in the file.

Contents:

```yaml
apiVersion: v0.1
workloads:
  frontend:
    runtime: podman
    agent: agent_A
    dependencies:
      backend: {}
    runtimeConfig: |
      image: ghcr.io/example/frontend:latest
```

Remediation notes:
- Expected validation error: `MISSING_DEPENDENCY` (backend not found).
- Remediator action: remove `backend` from `frontend` dependencies or add a stub `backend` workload (policy-based).
- After healing: dependency test should pass.

---

## `malformed_yaml.yaml`

Description: Intentionally malformed YAML (missing closing bracket) to test parser error handling.

Contents:

```yaml
apiVersion: v0.1
workloads:
  broken:
    runtime: podman
    agent: agent_A
    dependencies: {}
    runtimeConfig: |
      image: alpine:latest
      command: ["/bin/sh", "-c", "echo hi"
```

Remediation notes:
- Expected: YAML parse error reported by schema validator.
- Remediator cannot reliably fix arbitrary syntax errors — manual edit required.

---

## `missing_agent.yaml`

Description: Workload `redis` is missing the `agent` field.

Contents:

```yaml
apiVersion: v0.1
workloads:
  redis:
    runtime: podman
    # agent missing
    dependencies: {}
    runtimeConfig: |
      image: redis:7
      command: ["redis-server", "--save", "" ]
```

Remediation notes:
- Expected validation error: `MISSING_AGENT`.
- Remediator action: add a default agent (e.g., `agent_A`) or prompt user policy; auto-heal will add `agent: agent_A` if policy permits.

---

## `missing_runtime.yaml`

Description: Workload `nginx` is missing the `runtime` field.

Contents:

```yaml
apiVersion: v0.1
workloads:
  nginx:
    # runtime is missing and should be added by remediator
    agent: agent_A
    dependencies: {}
    runtimeConfig: |
      image: nginx:latest
      ports:
        - 80
```

Remediation notes:
- Expected validation error: `MISSING_RUNTIME`.
- Remediator action: add `runtime: podman` as default.

---

## `missing_runtimeConfig.yaml`

Description: Workload `incomplete` lacks `runtimeConfig` entirely.

Contents:

```yaml
apiVersion: v0.1
workloads:
  incomplete:
    runtime: podman
    agent: agent_A
    dependencies: {}
    # runtimeConfig missing (should be added with minimal defaults)
```

Remediation notes:
- Expected validation error: `MISSING_RUNTIMECONFIG`.
- Remediator action: add a minimal `runtimeConfig` block (e.g., `image: alpine:latest`).

---

## `multiline_quoted_runtimeConfig.yaml`

Description: `runtimeConfig` is provided as a quoted string that includes newlines; validator expects a block scalar. This tests normalization of multiline fields.

Contents:

```yaml
apiVersion: v0.1
workloads:
  weird:
    runtime: podman
    agent: agent_A
    dependencies: {}
    # runtimeConfig incorrectly provided as a plain quoted string instead of block
    runtimeConfig: "image: alpine:latest\ncommand: ['sh','-c','echo hi']"
```

Remediation notes:
- Expected: Schema may parse the field as a string; subsequent validators may fail (runtimeConfig expected to parse as YAML/structured mapping).
- Remediator action: convert the quoted string into a block scalar and parse it as YAML to attach structured runtimeConfig.

---

## `port_conflict.yaml`

Description: Two workloads expose the same port (8080), causing a resource conflict.

Contents:

```yaml
apiVersion: v0.1
workloads:
  service1:
    runtime: podman
    agent: agent_A
    dependencies: {}
    runtimeConfig: |
      image: ghcr.io/example/svc:1.0
      ports:
        - 8080
  service2:
    runtime: podman
    agent: agent_B
    dependencies: {}
    runtimeConfig: |
      image: ghcr.io/example/svc:1.0
      ports:
        - 8080
```

Remediation notes:
- Expected validation error: `PORT_CONFLICT`.
- Remediator action (policy): increment port for second service (8081) or flag for manual resolution.

---

## `test.yaml`

Description: Example that contains a `runtimeConfig` supplied as a quoted string including blank lines — used to demonstrate parsing issues with quoted multiline blocks.

Contents:

```yaml
apiVersion: v0.1
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    dependencies: {}
    runtimeConfig: 'image: ghcr.io/eclipse/kuksa.val/databroker:0.4.1

      commandArgs: ["--insecure"]

      commandOptions: ["--net=host"]'
```

Remediation notes:
- Expected: Parser may treat runtimeConfig as string; remediator can normalize to block scalar and parse inner YAML.

---

## `testhealing.yaml`

Description: A multi-workload test file used previously for healing tests.

Contents:

```yaml
apiVersion: v0.1
workloads:
  redis:
    runtime: podman
    agent: agent_A
    dependencies:
    runtimeConfig: |
      image: redis:7
  backend:
    runtime: podman
    agent: agent_B
    dependencies:
    runtimeConfig: |
      image: alpine:latest
  my_nginx:
    runtime: podman
    agent: agent_A
    dependencies:
      redis: ADD_COND_FAILED
    runtimeConfig: |
      image: ghcr.io/eclipse/kuksa.val/databroker:0.4.1
```

Remediation notes:
- Use to exercise dependency rules and ADD_COND conditions; expected mostly PASSED.

---

## `x.yaml`

Description: File you mentioned as "wrong" — currently contains a `demo` workload that depends on itself. Good for demonstrating auto-healing.

Contents:

```yaml
apiVersion: v0.1
workloads:
  demo:
    runtime: podman
    agent: agent_A
    dependencies:
      demo: {}
    runtimeConfig: |
      image: alpine:latest
```

Remediation notes:
- Same as `bad_self_dependency.yaml` — remediator should remove the self-dependency.

---

## `speed-provider.yaml` and `speed-consumer.yaml`

Description: Example workloads for speed provider/consumer. They are valid examples for runtime and commandOptions.

Contents (provider):

```yaml
apiVersion: v0.1
workloads:
  speed-provider:
    runtime: podman
    agent: agent_A
    runtimeConfig: |
      image: ghcr.io/eclipse-ankaios/speed-provider:0.1.1
      commandOptions:
        - "--net=host"
```

Contents (consumer):

```yaml
apiVersion: v0.1
workloads:
  speed-consumer:
    runtime: podman
    runtimeConfig: |
      image: ghcr.io/eclipse-ankaios/speed-consumer:0.1.2
      commandOptions:
        - "--net=host"
        - "-e"
        - "KUKSA_DATA_BROKER_ADDR=127.0.0.1"
```

Remediation notes:
- Expected: PASSED.

---

## `startupState.yaml`

Description: Dashboard startupState — includes `Ankaios_Dashboard` workload and many commented examples for other workloads. Used by `run_dashboard.sh` to start the demo server and initial workloads.

Contents: (excerpt)

```yaml
apiVersion: v0.1
workloads:
  Ankaios_Dashboard:
    runtime: podman
    agent: agent_A
    restart: true
    updateStrategy: AT_LEAST_ONCE
    accessRights:
      allow: []
      deny: []
    restartPolicy: NEVER 
    dependencies:
    runtimeConfig: |
       image: dashboard:0.0
       commandOptions: ["--network", "host"]
    controlInterfaceAccess:
        allowRules:
          - type: StateRule
            operation: ReadWrite
            filterMask:
              - "desiredState"
              - "workloadStates"
```

Remediation notes:
- This file is used to start the demo server and should be treated as canonical for the example environment.

---

## How to Save & Use This Catalog

- File saved at: `configuration_catalog.md` (this file).
- Use the `curl` commands listed earlier to validate files or run the wrapper `./ank -k apply config/<file>.yaml` to execute the full validate→heal→apply flow.

---

## Quick batch validation command

Run this from the repository root to get a validator report for each file:

```bash
for f in config/*.yaml; do
  echo "== $f =="
  curl -sS -X POST http://127.0.0.1:5001/api/validate-config \
    -H "Content-Type: application/json" \
    -d "{\"config\": $(jq -Rs . < "$f")}" | jq '.' || echo "Validation failed for $f"
  echo
  sleep 0.2
done
```

---

If you want, I can now:
- A) Run the batch validation and paste full reports here, or
- B) Run the wrapper `./ank -k apply` for one chosen file and show before/after diffs.

Tell me which you'd like next.  

---

*End of catalog.*
