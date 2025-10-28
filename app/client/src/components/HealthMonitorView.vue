<template>
  <q-page padding>
    <q-card class="q-pa-md shadow-2">
      <q-card-section>
        <div class="text-h5 text-primary">Workload Health Monitor</div>
        <div class="text-caption text-grey">Real-time workload health and alerts</div>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-table
          title="Active Workloads"
          :rows="workloads"
          :columns="columns"
          row-key="run_id"
          flat
          bordered
        >
          <template v-slot:body-cell-alert="props">
            <q-td :props="props">
              <q-badge
                :color="props.row.alert === 'critical' ? 'negative' : 'orange'"
                align="top"
              >
                {{ props.row.alert || 'Normal' }}
              </q-badge>
            </q-td>
          </template>
        </q-table>
      </q-card-section>

      <q-separator />

      <q-card-section>
        <div class="text-h6 q-mb-sm">System Resource Trends</div>
        <LineChart :data="chartData" />
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LineChart from './LineChart.vue'

const workloads = ref([])
const chartData = ref({})

const columns = [
  { name: 'workload_name', label: 'Workload', field: 'workload_name', align: 'left' },
  { name: 'cpu', label: 'CPU (%)', field: 'cpu' },
  { name: 'memory', label: 'Memory (MB)', field: 'memory' },
  { name: 'threads', label: 'Threads', field: 'threads' },
  { name: 'alert', label: 'Alert', field: 'alert', align: 'center' }
]

onMounted(async () => {
  const res = await fetch('/api/workload/health')
  if (res.ok) {
    const data = await res.json()
    workloads.value = data.active_runs
    chartData.value = data.metrics_summary
  }
})
</script>
