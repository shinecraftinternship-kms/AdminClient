let dashboardData = null;
let analyticsData = null;

function loadDashboard() {
    Promise.all([
        fetch('/api/assets/dashboard').then(r => r.json()).catch(() => ({})),
        fetch('/api/assets/analytics').then(r => r.json()).catch(() => ({})),
    ]).then(([dash, analytics]) => {
        dashboardData = dash;
        analyticsData = analytics;
        renderKPIs();
        renderCharts();
        renderRecentAssets();
    }).catch(err => showToast('Failed to load dashboard: ' + err.message, 'danger'));
}

function renderKPIs() {
    const d = dashboardData;
    if (!d) return;
    document.getElementById('kpiTotal').textContent = d.total_assets || 0;
    document.getElementById('kpiAssigned').textContent = d.assigned_assets || 0;
    document.getElementById('kpiAvailable').textContent = d.available_assets || 0;
    document.getElementById('kpiValue').textContent = '$' + (d.total_value || 0).toLocaleString();
    document.getElementById('kpiMaintenance').textContent = d.maintenance_assets || 0;
    document.getElementById('kpiRetired').textContent = d.retired_assets || 0;
    document.getElementById('kpiWarrantyExpiring').textContent = d.warranty_expiring || 0;
    document.getElementById('kpiUtilization').textContent = (analyticsData.utilization_rate || 0) + '%';
}

function renderCharts() {
    const d = dashboardData;
    if (!d) return;

    const chartDefaults = {
        color: '#e0e0e8',
        borderColor: '#2a2d3a',
    };
    Chart.defaults.color = chartDefaults.color;
    Chart.defaults.borderColor = chartDefaults.borderColor;

    // Category chart (doughnut)
    if (d.by_category && d.by_category.length > 0) {
        const ctx = document.getElementById('categoryChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: d.by_category.map(c => c.name || 'Uncategorized'),
                    datasets: [{
                        data: d.by_category.map(c => c.count),
                        backgroundColor: ['#4f8cff', '#22c55e', '#eab308', '#ef4444', '#a855f7', '#f97316', '#06b6d4', '#ec4899', '#14b8a6', '#6366f1'],
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { padding: 12 } } } }
            });
        }
    }

    // Department chart (bar)
    if (d.by_department && d.by_department.length > 0) {
        const ctx = document.getElementById('departmentChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: d.by_department.map(d => d.name || 'None'),
                    datasets: [{ label: 'Assets', data: d.by_department.map(d => d.count), backgroundColor: '#4f8cff', borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });
        }
    }

    // Growth trend (line)
    if (analyticsData && analyticsData.monthly_growth && analyticsData.monthly_growth.length > 0) {
        const ctx = document.getElementById('growthChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: analyticsData.monthly_growth.map(m => m.month),
                    datasets: [{ label: 'New Assets', data: analyticsData.monthly_growth.map(m => m.count), borderColor: '#4f8cff', backgroundColor: 'rgba(79,140,255,0.1)', fill: true, tension: 0.4 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });
        }
    }

    // Lifecycle distribution (pie)
    if (d.by_status && Object.keys(d.by_status).length > 0) {
        const ctx = document.getElementById('lifecycleChart');
        if (ctx) {
            const statusColors = {
                'Draft': '#6b7280', 'Pending Approval': '#eab308', 'Approved': '#06b6d4',
                'Purchased': '#3b82f6', 'Available': '#22c55e', 'Assigned': '#4f8cff',
                'Maintenance': '#f97316', 'Returned': '#6b7280', 'Lost': '#ef4444',
                'Damaged': '#ef4444', 'Retired': '#9ca3af', 'Disposed': '#374151',
            };
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: Object.keys(d.by_status),
                    datasets: [{
                        data: Object.values(d.by_status),
                        backgroundColor: Object.keys(d.by_status).map(s => statusColors[s] || '#6b7280'),
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { padding: 8 } } } }
            });
        }
    }

    // Location chart (bar)
    if (d.by_location && d.by_location.length > 0) {
        const ctx = document.getElementById('locationChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: d.by_location.map(l => l.name || 'None'),
                    datasets: [{ label: 'Assets', data: d.by_location.map(l => l.count), backgroundColor: '#22c55e', borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
            });
        }
    }

    // Value by department (bar)
    if (analyticsData && analyticsData.value_by_department && analyticsData.value_by_department.length > 0) {
        const ctx = document.getElementById('valueChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: analyticsData.value_by_department.map(d => d.name || 'None'),
                    datasets: [{ label: 'Value ($)', data: analyticsData.value_by_department.map(d => d.total_value || 0), backgroundColor: '#eab308', borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });
        }
    }
}

function renderRecentAssets() {
    const tbody = document.getElementById('recentAssetsBody');
    if (!tbody || !dashboardData) return;
    const recent = dashboardData.recent_assets || [];
    if (recent.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary">No recent assets</td></tr>';
        return;
    }
    const STATUS_BADGES = {
        'Draft': 'bg-secondary', 'Pending Approval': 'bg-warning text-dark', 'Approved': 'bg-info',
        'Purchased': 'bg-primary', 'Available': 'bg-success', 'Assigned': 'bg-info',
        'Maintenance': 'bg-warning text-dark', 'Returned': 'bg-secondary', 'Lost': 'bg-danger',
        'Damaged': 'bg-danger', 'Retired': 'bg-dark', 'Disposed': 'bg-dark', 'Archived': 'bg-dark',
    };
    tbody.innerHTML = recent.map(a => {
        const value = a.current_value || a.purchase_cost;
        return `<tr>
            <td><code class="text-secondary">${escapeHtml(a.asset_id)}</code></td>
            <td><a href="/assets/${a.id}/" class="text-decoration-none">${escapeHtml(a.asset_name)}</a></td>
            <td>${escapeHtml(a.category_name || '-')}</td>
            <td><span class="badge ${STATUS_BADGES[a.asset_status] || 'bg-secondary'}">${escapeHtml(a.asset_status)}</span></td>
            <td>${value ? '$' + Number(value).toLocaleString() : '-'}</td>
            <td class="small">${timeAgo(a.created_at)}</td>
        </tr>`;
    }).join('');
}

document.addEventListener('DOMContentLoaded', loadDashboard);
