<template>
  <q-page class="q-pa-md">
    <q-card>
      <q-card-section>
        <div class="text-h5">Configuration Validator</div>
        <div class="text-caption">Validate workload configurations before deployment</div>
      </q-card-section>

      <q-card-section>
        <q-input
          v-model="configYaml"
          type="textarea"
          label="Paste Configuration YAML"
          rows="15"
          outlined
          hint="Paste your Ankaios workload configuration here"
          :rules="[val => !!val || 'Configuration is required']"
        />

        <div class="q-mt-md">
          <q-btn
            color="primary"
            @click="validateConfig"
            :loading="validating"
            :disable="!configYaml"
          >
            <q-icon name="check_circle" class="q-mr-sm" />
            Validate Configuration
          </q-btn>

          <q-btn
            flat
            color="secondary"
            @click="loadExample"
            class="q-ml-sm"
          >
            Load Example
          </q-btn>
        </div>
      </q-card-section>

      <!-- Validation Results -->
      <q-card-section v-if="validationReport">
        <q-separator class="q-mb-md" />

        <div class="row items-center q-mb-md">
          <div class="text-h6 q-mr-md">Validation Result:</div>
          <q-badge
            :color="validationReport.overall_status === 'PASSED' ? 'green' : 'red'"
            :label="validationReport.overall_status"
            class="text-h6"
          />
        </div>

        <!-- Summary Stats -->
        <div class="row q-col-gutter-sm q-mb-md">
          <div class="col-3">
            <q-card flat bordered>
              <q-card-section class="text-center">
                <div class="text-h4">{{ validationReport.summary.total_tests }}</div>
                <div class="text-caption">Total Tests</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-3">
            <q-card flat bordered>
              <q-card-section class="text-center">
                <div class="text-h4 text-green">{{ validationReport.summary.passed }}</div>
                <div class="text-caption">Passed</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-3">
            <q-card flat bordered>
              <q-card-section class="text-center">
                <div class="text-h4 text-red">{{ validationReport.summary.failed }}</div>
                <div class="text-caption">Failed</div>
              </q-card-section>
            </q-card>
          </div>
          <div class="col-3">
            <q-card flat bordered>
              <q-card-section class="text-center">
                <div class="text-h4">{{ validationReport.summary.total_duration_ms }}ms</div>
                <div class="text-caption">Duration</div>
              </q-card-section>
            </q-card>
          </div>
        </div>

        <!-- Test Results Table -->
        <q-table
          :rows="validationReport.tests"
          :columns="columns"
          row-key="name"
          flat
          bordered
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.row.status)"
                :label="props.row.status"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-issues="props">
            <q-td :props="props">
              <q-badge
                v-if="props.row.issues && props.row.issues.length > 0"
                color="orange"
                :label="props.row.issues.length"
              />
              <span v-else>-</span>
            </q-td>
          </template>
        </q-table>

        <!-- Detailed Issues -->
        <div v-if="allIssues.length > 0" class="q-mt-md">
          <div class="text-h6 q-mb-sm">Issues & Warnings ({{ allIssues.length }})</div>

          <q-list bordered separator>
            <q-item v-for="(issue, index) in allIssues" :key="index">
              <q-item-section avatar>
                <q-icon
                  :name="issue.severity === 'ERROR' ? 'error' : 'warning'"
                  :color="issue.severity === 'ERROR' ? 'red' : 'orange'"
                  size="md"
                />
              </q-item-section>

              <q-item-section>
                <q-item-label>
                  <strong>{{ issue.type }}:</strong> {{ issue.message }}
                </q-item-label>
                <q-item-label caption v-if="issue.workload">
                  Workload: {{ issue.workload }}
                </q-item-label>
                <q-item-label caption v-if="issue.recommendation" class="text-blue">
                  💡 {{ issue.recommendation }}
                </q-item-label>
              </q-item-section>

              <q-item-section side>
                <q-badge
                  :color="issue.severity === 'ERROR' ? 'red' : 'orange'"
                  :label="issue.severity"
                />
              </q-item-section>
            </q-item>
          </q-list>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'ConfigValidatorView',

  setup() {
    const configYaml = ref('')
    const validationReport = ref(null)
    const validating = ref(false)

    const columns = [
      { name: 'name', label: 'Test Name', field: 'name', align: 'left', sortable: true },
      { name: 'description', label: 'Description', field: 'description', align: 'left' },
      { name: 'status', label: 'Status', field: 'status', align: 'center' },
      { name: 'issues', label: 'Issues', field: 'issues', align: 'center' },
      { name: 'duration_ms', label: 'Duration (ms)', field: 'duration_ms', align: 'right' },
    ]

    const allIssues = computed(() => {
      if (!validationReport.value || !validationReport.value.tests) return []

      const issues = []
      validationReport.value.tests.forEach(test => {
        if (test.issues && test.issues.length > 0) {
          issues.push(...test.issues)
        }
      })
      return issues
    })

    const validateConfig = async () => {
      validating.value = true
      validationReport.value = null

      try {
        const response = await fetch('/api/validate-config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            config: configYaml.value
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        validationReport.value = data

      } catch (error) {
        console.error('Validation error:', error)
        // You could add Quasar Notify here to show error to user
        // this.$q.notify({ type: 'negative', message: 'Validation failed' })
      } finally {
        validating.value = false
      }
    }

    const loadExample = () => {
      configYaml.value = `apiVersion: v0.1
workloads:
  nginx:
    runtime: podman
    agent: agent_A
    restartPolicy: ALWAYS
    dependencies: {}
    runtimeConfig: |
      image: docker.io/nginx:latest
      commandOptions: ["-p", "8080:80"]`
    }

    const getStatusColor = (status) => {
      switch(status) {
        case 'PASSED': return 'green'
        case 'FAILED': return 'red'
        case 'SKIPPED': return 'grey'
        default: return 'grey'
      }
    }

    return {
      configYaml,
      validationReport,
      validating,
      columns,
      allIssues,
      validateConfig,
      loadExample,
      getStatusColor
    }
  }
}
</script>
