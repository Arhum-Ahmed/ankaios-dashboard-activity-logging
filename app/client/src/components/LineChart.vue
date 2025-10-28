<template>
  <div>
    <canvas ref="chart"></canvas>
  </div>
</template>

<script>
import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale } from 'chart.js'

// Register Chart.js components
Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale)

export default {
  name: 'LineChart',
  props: {
    data: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      chart: null
    }
  },
  mounted() {
    this.renderChart()
  },
  watch: {
    data: {
      handler() {
        if (this.chart) {
          this.chart.destroy()
        }
        this.renderChart()
      },
      deep: true
    }
  },
  methods: {
    renderChart() {
      const ctx = this.$refs.chart.getContext('2d')
      const labels = Object.keys(this.data || {})
      const cpuValues = labels.map(id => this.data[id]?.cpu || 0)
      const memValues = labels.map(id => this.data[id]?.memory || 0)

      this.chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [
            {
              label: 'CPU (%)',
              data: cpuValues,
              borderColor: '#42A5F5',
              fill: false,
              tension: 0.3
            },
            {
              label: 'Memory (MB)',
              data: memValues,
              borderColor: '#66BB6A',
              fill: false,
              tension: 0.3
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' },
            title: { display: true, text: 'Workload Resource Trends' }
          },
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      })
    }
  }
}
</script>

<style scoped>
canvas {
  width: 100%;
  height: 400px;
}
</style>
