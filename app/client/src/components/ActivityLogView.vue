<template>
    <q-page class="q-pa-md">
        <div class="text-h4 q-mb-md">Activity Logs</div>

        <!-- Filters Section -->
        <q-card class="q-mb-md">
            <q-card-section>
                <div class="text-h6 q-mb-md">Filters</div>
                <div class="row q-col-gutter-md">
                    <div class="col-12 col-md-3">
                        <q-select
                            filled
                            v-model="filters.action"
                            :options="actionOptions"
                            label="Action"
                            clearable
                            @update:model-value="fetchLogs"
                        />
                    </div>
                    <div class="col-12 col-md-3">
                        <q-input
                            filled
                            v-model="filters.workload"
                            label="Workload Name"
                            clearable
                            @update:model-value="fetchLogs"
                        />
                    </div>
                    <div class="col-12 col-md-3">
                        <q-input
                            filled
                            v-model="filters.user"
                            label="User ID"
                            clearable
                            @update:model-value="fetchLogs"
                        />
                    </div>
                    <div class="col-12 col-md-3">
                        <q-btn
                            color="primary"
                            label="Export CSV"
                            icon="download"
                            @click="exportLogs"
                            class="full-width"
                        />
                    </div>
                </div>
            </q-card-section>
        </q-card>

        <!-- Logs Table -->
        <q-card>
            <q-card-section>
                <q-table
                    :rows="logs"
                    :columns="columns"
                    row-key="id"
                    :loading="loading"
                    :pagination="pagination"
                    @request="onRequest"
                    binary-state-sort
                    flat
                >
                    <template v-slot:body-cell-timestamp="props">
                        <q-td :props="props">
                            {{ formatDate(props.row.timestamp) }}
                        </q-td>
                    </template>

                    <template v-slot:body-cell-status="props">
                        <q-td :props="props">
                            <q-badge
                                :color="getStatusColor(props.row.status)"
                                :label="props.row.status"
                            />
                        </q-td>
                    </template>

                    <template v-slot:body-cell-action="props">
                        <q-td :props="props">
                            <q-chip
                                :color="getActionColor(props.row.action)"
                                text-color="white"
                                size="sm"
                            >
                                {{ props.row.action }}
                            </q-chip>
                        </q-td>
                    </template>
                </q-table>
            </q-card-section>
        </q-card>
    </q-page>
</template>

<script>
export default {
    data() {
        return {
            logs: [],
            loading: false,
            filters: {
                action: null,
                workload: '',
                user: ''
            },
            actionOptions: [
                'add_workload',
                'delete_workload',
                'update_config'
            ],
            pagination: {
                sortBy: 'timestamp',
                descending: true,
                page: 1,
                rowsPerPage: 25,
                rowsNumber: 0
            },
            columns: [
                {
                    name: 'id',
                    label: 'ID',
                    field: 'id',
                    align: 'left',
                    sortable: true
                },
                {
                    name: 'timestamp',
                    label: 'Timestamp',
                    field: 'timestamp',
                    align: 'left',
                    sortable: true
                },
                {
                    name: 'user_id',
                    label: 'User',
                    field: 'user_id',
                    align: 'left',
                    sortable: true
                },
                {
                    name: 'action',
                    label: 'Action',
                    field: 'action',
                    align: 'left',
                    sortable: true
                },
                {
                    name: 'workload_name',
                    label: 'Workload',
                    field: 'workload_name',
                    align: 'left',
                    sortable: true
                },
                {
                    name: 'agent',
                    label: 'Agent',
                    field: 'agent',
                    align: 'left',
                    sortable: true
                },
                {
                    name: 'status',
                    label: 'Status',
                    field: 'status',
                    align: 'left',
                    sortable: true
                }
            ]
        };
    },
    mounted() {
        this.fetchLogs();
    },
    methods: {
        async fetchLogs() {
            this.loading = true;

            const offset = (this.pagination.page - 1) * this.pagination.rowsPerPage;
            const limit = this.pagination.rowsPerPage;

            let url = `/activityLogs?limit=${limit}&offset=${offset}`;

            if (this.filters.action) {
                url += `&action=${this.filters.action}`;
            }
            if (this.filters.workload) {
                url += `&workload=${this.filters.workload}`;
            }
            if (this.filters.user) {
                url += `&user=${this.filters.user}`;
            }

            try {
                const response = await fetch(url);
                const data = await response.json();

                this.logs = data.logs;
                this.pagination.rowsNumber = data.total;
            } catch (error) {
                console.error('Error fetching logs:', error);
                this.$q.notify({
                    type: 'negative',
                    message: 'Failed to fetch activity logs'
                });
            } finally {
                this.loading = false;
            }
        },

        onRequest(props) {
            const { page, rowsPerPage } = props.pagination;
            this.pagination.page = page;
            this.pagination.rowsPerPage = rowsPerPage;
            this.fetchLogs();
        },

        async exportLogs() {
            let url = '/exportLogs?';

            if (this.filters.action) {
                url += `&action=${this.filters.action}`;
            }
            if (this.filters.workload) {
                url += `&workload=${this.filters.workload}`;
            }
            if (this.filters.user) {
                url += `&user=${this.filters.user}`;
            }

            try {
                window.open(url, '_blank');
                this.$q.notify({
                    type: 'positive',
                    message: 'Exporting activity logs...'
                });
            } catch (error) {
                console.error('Error exporting logs:', error);
                this.$q.notify({
                    type: 'negative',
                    message: 'Failed to export logs'
                });
            }
        },

        formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleString();
        },

        getActionColor(action) {
            const colors = {
                'add_workload': 'positive',
                'delete_workload': 'negative',
                'update_config': 'warning'
            };
            return colors[action] || 'grey';
        },

        getStatusColor(status) {
            const colors = {
                'success': 'positive',
                'failed': 'negative',
                'pending': 'warning',
                'unknown': 'grey'
            };
            return colors[status] || 'grey';
        }
    }
}
</script>

<script setup>
defineOptions({
    name: "ActivityLogView",
});
</script>

<style scoped>
.q-table {
    font-size: 14px;
}
</style>
