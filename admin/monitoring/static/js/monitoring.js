let monitoringData = null;
let devices = [];
let alerts = [];
let statusChart = null;
let healthChart = null;
let platformChart = null;
let usageTrendChart = null;
let healthTrendChart = null;

function initWebSocket() {
    if (typeof DashboardWS === 'undefined') return;

    DashboardWS.onStatusChange((status) => {
        const dot = document.getElementById('wsStatus');
        if (dot) {
            dot.className = status === 'connected'
                ? 'badge bg-success'
                : 'badge bg-danger';
            dot.textContent = status === 'connected' ? 'Live' : 'Disconnected';
        }
    });

    DashboardWS.on('device_update', (msg) => {
        const data = msg.data || msg;
        const deviceId = data.device_id || data.client_key;
        const idx = devices.findIndex(d => d.id === deviceId || d.registration_key === deviceId);
        if (idx >= 0) {
            Object.assign(devices[idx], data);
        }
        renderDeviceTable();
    });

    DashboardWS.on('alert_created', (msg) => {
        const alert = msg.data || msg;
        alerts.unshift(alert);
        if (alerts.length > 100) alerts.length = 100;
        renderAlerts();
        showToast(`New alert: ${alert.title || alert.message}`, alert.severity === 'critical' ? 'danger' : 'warning');
    });

    DashboardWS.on('health_level_changed', (msg) => {
        const data = msg.data || msg;
        if (data.client_key) {
            const dev = devices.find(d => d.registration_key === data.client_key);
            if (dev) {
                dev.health_level = data.new_level || data.health_level;
                dev.health_score = data.new_score || data.health_score;
                renderDeviceTable();
            }
        }
    });

    DashboardWS.on('hw_component_added', handleHWChange);
    DashboardWS.on('hw_component_removed', handleHWChange);
    DashboardWS.on('hw_component_modified', handleHWChange);
    DashboardWS.on('sw_unauthorized', handleSWChange);
    DashboardWS.on('sw_antivirus_removed', handleSWChange);

    DashboardWS.connect();
}

function handleHWChange(msg) {
    const data = msg.data || msg;
    showToast(`Hardware change: ${msg.description || msg.title}`, msg.severity === 'critical' ? 'danger' : 'info');
}

function handleSWChange(msg) {
    const data = msg.data || msg;
    showToast(`Software change: ${msg.description || msg.title}`, msg.severity === 'critical' ? 'danger' : 'warning');
}

function showToast(message, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `alert alert-${type || 'info'} alert-dismissible fade show position-relative`;
    toast.style.cssText = 'min-width:300px;margin-bottom:8px;';
    toast.innerHTML = `${escapeHtml(message)}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 8000);
}

function loadDashboard() {
    Promise.all([
        fetch('/api/monitoring/dashboard').then(r => r.json()).catch(() => ({})),
        fetch('/api/monitoring/devices').then(r => r.json()).catch(() => []),
        fetch('/api/monitoring/alerts').then(r => r.json()).catch(() => []),
    ]).then(([data, devs, alertsData]) => {
        monitoringData = data;
        devices = devs;
        alerts = alertsData;
        renderKPIs();
        renderCharts();
        renderPlatformFilter();
        renderDeviceTable();
        renderAlerts();
    }).catch(err => showToast('Failed to load monitoring data: ' + err.message, 'danger'));
}

function renderKPIs() {
    if (!monitoringData) return;
    const d = monitoringData;
    setText('kpiTotal', d.total_devices || 0);
    setText('kpiOnline', d.online_count || 0);
    setText('kpiOffline', d.offline_count || 0);
    setText('kpiHealth', (d.avg_health_score || 0).toFixed(1));
    setText('kpiPending', d.pending_count || 0);
    setText('kpiAlertsCritical', d.alerts_critical || 0);
    setText('kpiAlertsWarning', d.alerts_warning || 0);
    setText('kpiBlocked', d.blocked_count || 0);
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function renderCharts() {
    if (!monitoringData) return;

    // Status Doughnut
    const sd = monitoringData.status_distribution || {};
    const sLabels = Object.keys(sd);
    const sData = Object.values(sd);
    const sColors = ['#22c55e', '#ef4444', '#eab308', '#a855f7', '#6b7280', '#3b82f6', '#f97316', '#06b6d4', '#ec4899'];

    if (!statusChart) {
        statusChart = new Chart(document.getElementById('statusChart').getContext('2d'), {
            type: 'doughnut',
            data: { labels: sLabels, datasets: [{ data: sData, backgroundColor: sColors.slice(0, sLabels.length), borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 10, font: { size: 11 } } } } }
        });
    } else {
        statusChart.data.labels = sLabels;
        statusChart.data.datasets[0].data = sData;
        statusChart.update();
    }

    // Health Distribution Doughnut
    const hd = monitoringData.health_distribution || {};
    const hLabels = Object.keys(hd);
    const hData = Object.values(hd);
    const hColors = { healthy: '#22c55e', warning: '#eab308', critical: '#ef4444', unknown: '#6b7280' };

    if (!healthChart) {
        healthChart = new Chart(document.getElementById('healthChart').getContext('2d'), {
            type: 'doughnut',
            data: { labels: hLabels, datasets: [{ data: hData, backgroundColor: hLabels.map(l => hColors[l] || '#6b7280'), borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 10, font: { size: 11 } } } } }
        });
    } else {
        healthChart.data.labels = hLabels;
        healthChart.data.datasets[0].data = hData;
        healthChart.update();
    }

    // Platform Distribution Doughnut
    const pd = monitoringData.platform_distribution || [];
    const pLabels = pd.map(p => p.name || 'Unknown');
    const pData = pd.map(p => p.count);
    const pColors = ['#4f8cff', '#a78bfa', '#f472b6', '#34d399', '#fbbf24', '#f97316', '#8888a0'];

    if (!platformChart) {
        platformChart = new Chart(document.getElementById('platformChart').getContext('2d'), {
            type: 'doughnut',
            data: { labels: pLabels, datasets: [{ data: pData, backgroundColor: pColors.slice(0, pLabels.length), borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 10, font: { size: 11 } } } } }
        });
    } else {
        platformChart.data.labels = pLabels;
        platformChart.data.datasets[0].data = pData;
        platformChart.update();
    }

    // CPU/RAM/Disk Usage Trend (24h)
    const cpuTrend = monitoringData.cpu_trend || [];
    const ramTrend = monitoringData.ram_trend || [];
    const diskTrend = monitoringData.disk_trend || [];
    const tLabels = cpuTrend.map(t => {
        const d = new Date(t.timestamp);
        return d.getHours() + ':00';
    });

    if (!usageTrendChart) {
        usageTrendChart = new Chart(document.getElementById('usageTrendChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: tLabels,
                datasets: [
                    { label: 'CPU %', data: cpuTrend.map(t => t.avg), borderColor: '#4f8cff', backgroundColor: 'rgba(79,140,255,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                    { label: 'RAM %', data: ramTrend.map(t => t.avg), borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                    { label: 'Disk %', data: diskTrend.map(t => t.avg), borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.1)', fill: true, tension: 0.4, pointRadius: 0 },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 10, font: { size: 11 } } } },
                scales: {
                    x: { ticks: { color: '#8888a0', maxRotation: 45, maxTicksLimit: 12 }, grid: { display: false } },
                    y: { beginAtZero: true, max: 100, ticks: { color: '#8888a0' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                },
            },
        });
    } else {
        usageTrendChart.data.labels = tLabels;
        usageTrendChart.data.datasets[0].data = cpuTrend.map(t => t.avg);
        usageTrendChart.data.datasets[1].data = ramTrend.map(t => t.avg);
        usageTrendChart.data.datasets[2].data = diskTrend.map(t => t.avg);
        usageTrendChart.update();
    }

    // Health Score Trend (7d)
    const hTrend = monitoringData.health_trend || [];
    const htLabels = hTrend.map(t => t.date);

    if (!healthTrendChart) {
        healthTrendChart = new Chart(document.getElementById('healthTrendChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: htLabels,
                datasets: [{
                    label: 'Avg Health Score', data: hTrend.map(t => t.avg),
                    borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.15)', fill: true, tension: 0.4, pointRadius: 3,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 10, font: { size: 11 } } } },
                scales: {
                    x: { ticks: { color: '#8888a0', maxRotation: 45 }, grid: { display: false } },
                    y: { beginAtZero: true, max: 100, ticks: { color: '#8888a0' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                },
            },
        });
    } else {
        healthTrendChart.data.labels = htLabels;
        healthTrendChart.data.datasets[0].data = hTrend.map(t => t.avg);
        healthTrendChart.update();
    }
}

function renderPlatformFilter() {
    const sel = document.getElementById('platformFilter');
    if (!sel) return;
    const platforms = new Set(devices.map(d => d.platform).filter(Boolean));
    sel.innerHTML = '<option value="">All Platforms</option>' + Array.from(platforms).sort().map(p => `<option value="${escapeHtml(p)}">${escapeHtml(p)}</option>`).join('');
}

function filterDevices() {
    renderDeviceTable();
}

function renderDeviceTable() {
    const searchTerm = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const statusF = document.getElementById('statusFilter')?.value || '';
    const healthF = document.getElementById('healthFilter')?.value || '';
    const platformF = document.getElementById('platformFilter')?.value || '';

    const filtered = devices.filter(d => {
        if (searchTerm) {
            const hay = [d.hostname, d.registration_key, d.ip_address, d.current_user, d.department, d.location_name].join(' ').toLowerCase();
            if (!hay.includes(searchTerm)) return false;
        }
        if (statusF && d.monitoring_status !== statusF) return false;
        if (healthF && d.health_level !== healthF) return false;
        if (platformF && d.platform !== platformF) return false;
        return true;
    });

    const countEl = document.getElementById('filterCount');
    if (countEl) countEl.textContent = filtered.length < devices.length ? `Showing ${filtered.length} of ${devices.length}` : `${devices.length} device${devices.length !== 1 ? 's' : ''}`;

    const tbody = document.getElementById('deviceTableBody');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-secondary py-4"><i class="bi bi-pc-display-horizontal fs-1 d-block mb-2"></i>No devices found</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(d => {
        const statusBadge = getStatusBadge(d.monitoring_status);
        const healthBadge = getHealthBadge(d.health_level, d.health_score);
        const cpu = d.latest_cpu || 0;
        const ram = d.latest_ram || 0;
        const disk = d.latest_disk || 0;

        return `<tr style="cursor:pointer;" onclick="showDeviceDetail('${d.id}')">
            <td>
                <div class="fw-semibold">${escapeHtml(d.hostname || 'Unknown')}</div>
                <div class="small text-secondary" style="font-family:monospace;font-size:0.7rem;">${d.registration_key || ''}</div>
            </td>
            <td>${statusBadge}</td>
            <td>${healthBadge}</td>
            <td>${renderMiniBar(cpu, '#4f8cff')}</td>
            <td>${renderMiniBar(ram, '#a78bfa')}</td>
            <td>${renderMiniBar(disk, '#f472b6')}</td>
            <td class="small">${escapeHtml(d.platform || '')}</td>
            <td class="small text-secondary">${d.last_seen ? timeAgo(d.last_seen) : 'Never'}</td>
            <td onclick="event.stopPropagation()">
                <div class="d-flex gap-1">
                    ${d.monitoring_status === 'pending' ? `<button class="btn btn-sm btn-outline-success" onclick="approveDevice('${d.id}')" title="Approve"><i class="bi bi-check-lg"></i></button>` : ''}
                    ${d.monitoring_status !== 'blocked' ? `<button class="btn btn-sm btn-outline-danger" onclick="blockDevice('${d.id}')" title="Block"><i class="bi bi-shield-x"></i></button>` : ''}
                    <button class="btn btn-sm btn-outline-info" onclick="showDeviceDetail('${d.id}')" title="Details"><i class="bi bi-info-circle"></i></button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function renderMiniBar(pct, color) {
    const val = Math.min(100, Math.max(0, pct));
    const barColor = val > 90 ? '#ef4444' : val > 75 ? '#eab308' : color;
    return `<div class="d-flex align-items-center gap-2">
        <div style="width:60px;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;overflow:hidden;">
            <div style="width:${val}%;height:100%;background:${barColor};border-radius:3px;"></div>
        </div>
        <span class="small" style="min-width:32px;">${val.toFixed(0)}%</span>
    </div>`;
}

function getStatusBadge(status) {
    const map = {
        online: 'success', offline: 'danger', pending: 'warning',
        blocked: 'secondary', maintenance: 'info', inactive: 'dark',
        rejected: 'danger', unknown: 'secondary', approved: 'primary',
    };
    return `<span class="badge bg-${map[status] || 'secondary'}">${status}</span>`;
}

function getHealthBadge(level, score) {
    const map = { healthy: 'success', warning: 'warning', critical: 'danger', unknown: 'secondary' };
    return `<span class="badge bg-${map[level] || 'secondary'}">${score}</span>`;
}

function renderAlerts() {
    const tbody = document.getElementById('alertsBody');
    if (!alerts || alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-secondary">No alerts</td></tr>';
        return;
    }
    const sevColors = { critical: 'danger', warning: 'warning', info: 'info' };
    tbody.innerHTML = alerts.slice(0, 20).map(a => `<tr>
        <td><span class="badge bg-${sevColors[a.severity] || 'secondary'}">${a.severity}</span></td>
        <td class="small">${escapeHtml(a.hostname || a.registration_key || '')}</td>
        <td class="small">${escapeHtml(a.alert_type)}</td>
        <td class="small">${escapeHtml(a.message || a.title)}</td>
        <td class="small text-secondary">${timeAgo(a.created_at)}</td>
        <td><span class="badge bg-${a.status === 'active' ? 'danger' : 'secondary'}">${a.status}</span></td>
        <td onclick="event.stopPropagation()">
            ${a.status === 'active' ? `
                <button class="btn btn-sm btn-outline-warning" onclick="ackAlert('${a.id}')" title="Acknowledge"><i class="bi bi-check2"></i></button>
                <button class="btn btn-sm btn-outline-success" onclick="resolveAlertAction('${a.id}')" title="Resolve"><i class="bi bi-check-all"></i></button>
            ` : ''}
        </td>
    </tr>`).join('');
}

function approveDevice(deviceKey) {
    fetch(`/api/monitoring/devices/${deviceKey}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
        .then(r => r.json()).then(() => { showToast('Device approved', 'success'); loadDashboard(); });
}

function blockDevice(deviceKey) {
    if (!confirm('Block this device?')) return;
    fetch(`/api/monitoring/devices/${deviceKey}/block`, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
        .then(r => r.json()).then(() => { showToast('Device blocked', 'warning'); loadDashboard(); });
}

function ackAlert(alertKey) {
    fetch(`/api/monitoring/alerts/${alertKey}/action`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'acknowledge' }),
    }).then(r => r.json()).then(() => { showToast('Alert acknowledged', 'info'); loadDashboard(); });
}

function resolveAlertAction(alertKey) {
    fetch(`/api/monitoring/alerts/${alertKey}/action`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'resolve' }),
    }).then(r => r.json()).then(() => { showToast('Alert resolved', 'success'); loadDashboard(); });
}

function showDeviceDetail(deviceId) {
    const modal = new bootstrap.Modal(document.getElementById('deviceDetailModal'));
    document.getElementById('deviceDetailTitle').textContent = 'Device Details';
    document.getElementById('deviceDetailBody').innerHTML = '<div class="text-center py-4 text-secondary">Loading...</div>';
    modal.show();

    fetch(`/api/monitoring/devices/${deviceId}`).then(r => r.json()).then(d => {
        const hb = d.latest_heartbeat || {};
        const cpu = hb.cpu_usage_pct || 0;
        const ram = hb.ram_usage_pct || 0;
        const disk = hb.disk_usage_pct || 0;

        let html = `
        <div class="row mb-3">
            <div class="col-md-6">
                <h6 class="text-secondary">Device Information</h6>
                <table class="table table-sm table-borderless text-white mb-0">
                    <tr><td class="text-secondary">Hostname</td><td>${escapeHtml(d.hostname || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Registration Key</td><td style="font-family:monospace;">${d.registration_key || 'N/A'}</td></tr>
                    <tr><td class="text-secondary">Platform</td><td>${escapeHtml(d.platform || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">IP Address</td><td>${escapeHtml(d.ip_address || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">MAC Address</td><td>${escapeHtml(d.mac_address || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">OS</td><td>${escapeHtml(d.os_name || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Agent Version</td><td>${escapeHtml(d.agent_version || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Device Type</td><td>${escapeHtml(d.device_type || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Department</td><td>${escapeHtml(d.department || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Location</td><td>${escapeHtml(d.location_name || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Current User</td><td>${escapeHtml(d.current_user || 'N/A')}</td></tr>
                    <tr><td class="text-secondary">Status</td><td>${getStatusBadge(d.monitoring_status)}</td></tr>
                    <tr><td class="text-secondary">Last Heartbeat</td><td>${d.last_heartbeat ? timeAgo(d.last_heartbeat) : 'Never'}</td></tr>
                    <tr><td class="text-secondary">Heartbeats</td><td>${d.heartbeat_count || 0}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6 class="text-secondary">Current Health</h6>
                <div class="text-center mb-3">
                    <div style="font-size:3rem;font-weight:bold;color:${d.health_level === 'healthy' ? '#22c55e' : d.health_level === 'warning' ? '#eab308' : d.health_level === 'critical' ? '#ef4444' : '#6b7280'}">${d.health_score || 0}</div>
                    <div class="badge bg-${d.health_level === 'healthy' ? 'success' : d.health_level === 'warning' ? 'warning' : d.health_level === 'critical' ? 'danger' : 'secondary'}">${d.health_level || 'unknown'}</div>
                </div>
                <div class="mb-2">
                    <div class="d-flex justify-content-between small"><span>CPU</span><span>${cpu.toFixed(1)}%</span></div>
                    <div class="progress" style="height:8px;background:rgba(255,255,255,0.1);">
                        <div class="progress-bar" style="width:${cpu}%;background:${cpu > 90 ? '#ef4444' : cpu > 70 ? '#eab308' : '#4f8cff'}"></div>
                    </div>
                </div>
                <div class="mb-2">
                    <div class="d-flex justify-content-between small"><span>RAM</span><span>${ram.toFixed(1)}%</span></div>
                    <div class="progress" style="height:8px;background:rgba(255,255,255,0.1);">
                        <div class="progress-bar" style="width:${ram}%;background:${ram > 90 ? '#ef4444' : ram > 70 ? '#eab308' : '#a78bfa'}"></div>
                    </div>
                </div>
                <div class="mb-2">
                    <div class="d-flex justify-content-between small"><span>Disk</span><span>${disk.toFixed(1)}%</span></div>
                    <div class="progress" style="height:8px;background:rgba(255,255,255,0.1);">
                        <div class="progress-bar" style="width:${disk}%;background:${disk > 95 ? '#ef4444' : disk > 80 ? '#eab308' : '#f472b6'}"></div>
                    </div>
                </div>
            </div>
        </div>`;

        if (d.hardware && d.hardware.length > 0) {
            html += `<h6 class="text-secondary mt-3">Hardware Inventory</h6>
            <div class="table-responsive"><table class="table table-sm table-dark table-hover mb-0">
                <thead><tr><th>Type</th><th>Details</th><th>Fingerprint</th><th>Time</th></tr></thead>
                <tbody>${d.hardware.map(h => `<tr>
                    <td><span class="badge bg-secondary">${h.component_type}</span></td>
                    <td class="small">${escapeHtml(JSON.stringify(h.component_data).substring(0, 120))}</td>
                    <td class="small" style="font-family:monospace;">${h.fingerprint || ''}</td>
                    <td class="small text-secondary">${timeAgo(h.created_at)}</td>
                </tr>`).join('')}</tbody>
            </table></div>`;
        }

        if (d.software && d.software.length > 0) {
            html += `<h6 class="text-secondary mt-3">Software Inventory (${d.software.length} items)</h6>
            <div class="table-responsive" style="max-height:300px;overflow:auto;"><table class="table table-sm table-dark table-hover mb-0">
                <thead><tr><th>Name</th><th>Version</th><th>Publisher</th></tr></thead>
                <tbody>${d.software.map(s => `<tr>
                    <td class="small">${escapeHtml(s.name)}</td>
                    <td class="small">${escapeHtml(s.version)}</td>
                    <td class="small text-secondary">${escapeHtml(s.publisher)}</td>
                </tr>`).join('')}</tbody>
            </table></div>`;
        }

        if (d.recent_alerts && d.recent_alerts.length > 0) {
            const sevColors = { critical: 'danger', warning: 'warning', info: 'info' };
            html += `<h6 class="text-secondary mt-3">Recent Alerts</h6>
            <div class="table-responsive"><table class="table table-sm table-dark table-hover mb-0">
                <thead><tr><th>Severity</th><th>Type</th><th>Message</th><th>Time</th></tr></thead>
                <tbody>${d.recent_alerts.map(a => `<tr>
                    <td><span class="badge bg-${sevColors[a.severity] || 'secondary'}">${a.severity}</span></td>
                    <td class="small">${escapeHtml(a.alert_type)}</td>
                    <td class="small">${escapeHtml(a.message || a.title)}</td>
                    <td class="small text-secondary">${timeAgo(a.created_at)}</td>
                </tr>`).join('')}</tbody>
            </table></div>`;
        }

        if (d.recent_history && d.recent_history.length > 0) {
            html += `<h6 class="text-secondary mt-3">Recent History</h6>
            <div class="table-responsive"><table class="table table-sm table-dark table-hover mb-0">
                <thead><tr><th>Category</th><th>Event</th><th>Description</th><th>Severity</th><th>Time</th></tr></thead>
                <tbody>${d.recent_history.map(h => `<tr>
                    <td class="small">${escapeHtml(h.category)}</td>
                    <td class="small">${escapeHtml(h.event_type)}</td>
                    <td class="small">${escapeHtml(h.description)}</td>
                    <td><span class="badge bg-${h.severity === 'critical' ? 'danger' : h.severity === 'warning' ? 'warning' : 'secondary'}">${h.severity}</span></td>
                    <td class="small text-secondary">${timeAgo(h.timestamp)}</td>
                </tr>`).join('')}</tbody>
            </table></div>`;
        }

        document.getElementById('deviceDetailBody').innerHTML = html;
    }).catch(err => {
        document.getElementById('deviceDetailBody').innerHTML = `<div class="text-danger">Error: ${err.message}</div>`;
    });
}

loadDashboard();
setInterval(loadDashboard, 30000);
setTimeout(initWebSocket, 500);
