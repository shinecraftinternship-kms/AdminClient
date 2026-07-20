let clients = [];
let groups = [];
let refreshInterval;
let statusChart = null;
let osChart = null;
let activityChart = null;
let adminClientKey = null;
let selectedClients = new Set();

function refreshClients() {
    Promise.all([
        fetch('/api/clients').then(r => r.json()),
        fetch('/api/admin-client').then(r => r.json()).catch(() => ({})),
        fetch('/api/groups').then(r => r.json()).catch(() => []),
    ]).then(([data, adminData, groupsData]) => {
        clients = data;
        groups = groupsData;
        if (adminData.registered) adminClientKey = adminData.registration_key;
        renderStats();
        renderCharts();
        renderGroupFilter();
        renderClients();
    }).catch(err => showToast('Failed to load data: ' + err.message, 'danger'));
}

function renderStats() {
    const total = clients.length;
    const online = clients.filter(c => !c.deleted && !c.is_stale && c.status === 'online').length;
    const pending = clients.filter(c => !c.deleted && !c.is_stale && c.status === 'pending').length;
    const deleted = clients.filter(c => c.deleted).length;
    const offline = total - online - pending;
    document.getElementById('totalClients').textContent = total;
    document.getElementById('onlineClients').textContent = online;
    document.getElementById('offlineClients').textContent = offline;
    document.getElementById('pendingClients').textContent = pending;
}

function renderCharts() {
    const online = clients.filter(c => !c.deleted && !c.is_stale && c.status === 'online').length;
    const pending = clients.filter(c => !c.deleted && !c.is_stale && c.status === 'pending').length;
    const offline = clients.length - online - pending;

    if (!statusChart) {
        statusChart = new Chart(document.getElementById('statusChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Offline', 'Pending'],
                datasets: [{ data: [online, offline, pending], backgroundColor: ['#22c55e', '#ef4444', '#eab308'], borderWidth: 0 }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 12 } } }
            }
        });
    } else {
        statusChart.data.datasets[0].data = [online, offline, pending];
        statusChart.update();
    }

    const osCounts = {};
    clients.forEach(c => { const os = c.platform || 'Unknown'; osCounts[os] = (osCounts[os] || 0) + 1; });
    const osLabels = Object.keys(osCounts);
    const osData = Object.values(osCounts);
    const osColors = ['#4f8cff', '#a78bfa', '#f472b6', '#34d399', '#fbbf24', '#f97316', '#8888a0'];

    if (!osChart) {
        osChart = new Chart(document.getElementById('osChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: osLabels,
                datasets: [{ data: osData, backgroundColor: osColors.slice(0, osLabels.length), borderWidth: 0 }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 12 } } }
            }
        });
    } else {
        osChart.data.labels = osLabels;
        osChart.data.datasets[0].data = osData;
        osChart.data.datasets[0].backgroundColor = osColors.slice(0, osLabels.length);
        osChart.update();
    }

    const now = new Date();
    const dayLabels = [];
    const dayCounts = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date(now);
        d.setDate(d.getDate() - i);
        dayLabels.push(d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }));
        const dayStart = new Date(d); dayStart.setHours(0, 0, 0, 0);
        const dayEnd = new Date(d); dayEnd.setHours(23, 59, 59, 999);
        dayCounts.push(clients.filter(c => c.last_seen && new Date(c.last_seen) >= dayStart && new Date(c.last_seen) <= dayEnd).length);
    }

    if (!activityChart) {
        activityChart = new Chart(document.getElementById('activityChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: dayLabels,
                datasets: [{ label: 'Active Clients', data: dayCounts, backgroundColor: '#4f8cff', borderRadius: 4 }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#8888a0', maxRotation: 45 }, grid: { display: false } },
                    y: { beginAtZero: true, ticks: { color: '#8888a0', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' } }
                }
            }
        });
    } else {
        activityChart.data.labels = dayLabels;
        activityChart.data.datasets[0].data = dayCounts;
        activityChart.update();
    }
}

function renderGroupFilter() {
    const sel = document.getElementById('groupFilter');
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="all">All Groups</option>' + groups.map(g => `<option value="${g.id}">${escapeHtml(g.name)}</option>`).join('');
    sel.value = current;
}

function renderClients() {
    const grid = document.getElementById('clientGrid');
    if (clients.length === 0) {
        grid.innerHTML = `<div class="col-12 text-center py-5">
            <i class="bi bi-laptops fs-1 text-secondary"></i>
            <p class="text-secondary mt-3">No clients registered yet.<br>
            <small>Run the client app on any machine to register it.</small></p>
        </div>`;
        return;
    }

    const searchTerm = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const statusFilter = document.getElementById('statusFilter')?.value || 'all';
    const groupFilter = document.getElementById('groupFilter')?.value || 'all';

    const filtered = clients.filter(c => {
        if (searchTerm && !c.hostname?.toLowerCase().includes(searchTerm) && !c.registration_key?.toLowerCase().includes(searchTerm) && !c.platform?.toLowerCase().includes(searchTerm) && !(c.tags_list || []).some(t => t.toLowerCase().includes(searchTerm))) return false;
        if (statusFilter === 'online' && (c.deleted || c.is_stale || c.status !== 'online')) return false;
        if (statusFilter === 'offline' && !c.deleted && !c.is_stale && c.status !== 'offline') return false;
        if (statusFilter === 'stale' && (c.deleted || !c.is_stale)) return false;
        if (statusFilter === 'pending' && (c.deleted || c.is_stale || c.status !== 'pending')) return false;
        if (statusFilter === 'deleted' && !c.deleted) return false;
        if (groupFilter !== 'all' && c.group !== parseInt(groupFilter)) return false;
        return true;
    });

    const filterCount = document.getElementById('filterCount');
    if (filterCount) filterCount.textContent = filtered.length < clients.length ? `Showing ${filtered.length} of ${clients.length}` : `${clients.length} client${clients.length !== 1 ? 's' : ''}`;

    grid.innerHTML = filtered.map(c => {
        const isAdmin = c.registration_key === adminClientKey;
        const isSelected = selectedClients.has(c.registration_key);
        const tagsHtml = (c.tags_list || []).map(t => `<span class="badge bg-secondary me-1" style="font-size:0.65rem;">${escapeHtml(t)}</span>`).join('');
        const groupBadge = c.group_name ? `<span class="badge bg-info ms-1" style="font-size:0.65rem;">${escapeHtml(c.group_name)}</span>` : '';
        const deletedBadge = c.deleted ? `<span class="badge bg-danger ms-1" style="font-size:0.65rem;">Deleted</span>` : '';
        const dotClass = c.deleted ? 'offline' : (c.is_stale ? 'offline' : c.status === 'online' ? 'online' : c.status === 'pending' ? 'pending' : 'offline');

        return `<div class="col-xl-3 col-lg-4 col-md-6 mb-3 client-card-wrapper">
            <div class="client-card p-3 ${isAdmin ? 'border-primary' : ''} ${isSelected ? 'border-success' : ''} ${c.deleted ? 'opacity-50' : ''}" style="cursor:pointer;">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div class="flex-grow-1" onclick="window.location='/client/${c.registration_key}'">
                        <div>
                            <span class="fw-semibold">${escapeHtml(c.hostname || 'Unknown')}</span>
                            <span class="badge bg-dark ms-1" style="font-family:monospace;font-size:0.7rem;">${c.registration_key}</span>
                            ${isAdmin ? '<span class="badge bg-primary ms-1">Admin</span>' : ''}
                            ${groupBadge}
                            ${deletedBadge}
                        </div>
                        ${tagsHtml ? '<div class="mt-1">' + tagsHtml + '</div>' : ''}
                    </div>
                    <div class="d-flex align-items-center gap-2 ms-2">
                        ${c.approved && !isAdmin && !c.deleted ? `<button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation();scanClient('${c.registration_key}')" title="Request scan"><i class="bi bi-play-fill"></i></button>` : ''}
                        ${!c.approved && !c.deleted ? `<button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation();approveClient('${c.registration_key}')" title="Approve"><i class="bi bi-check-lg"></i></button>` : ''}
                        ${!c.deleted ? `<input type="checkbox" class="form-check-input" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation();toggleSelection('${c.registration_key}')">` : ''}
                        <span class="status-dot ${dotClass}"></span>
                    </div>
                </div>
                <div class="small text-secondary">
                    <div>${c.platform || 'Unknown'}${c.cpu_model ? ' | ' + escapeHtml(c.cpu_model) : ''}</div>
                    ${c.last_ip ? '<div><i class="bi bi-globe me-1"></i>' + escapeHtml(c.last_ip) + '</div>' : ''}
                    <div>Last seen: ${timeAgo(c.last_seen)}${c.is_stale && !c.deleted ? ' (stale)' : ''}</div>
                    ${c.purchase_cost ? '<div>Cost: $' + parseFloat(c.purchase_cost).toFixed(2) + '</div>' : ''}
                </div>
            </div>
        </div>`;
    }).join('');

    updateBulkBar();
}

function toggleSelection(key) {
    if (selectedClients.has(key)) selectedClients.delete(key);
    else selectedClients.add(key);
    renderClients();
}

function clearSelection() {
    selectedClients.clear();
    renderClients();
}

function updateBulkBar() {
    const bar = document.getElementById('bulkActionsBar');
    const count = document.getElementById('selectedCount');
    if (selectedClients.size > 0) {
        bar.style.display = 'block';
        count.textContent = selectedClients.size + ' selected';
    } else {
        bar.style.display = 'none';
    }
}

function bulkApprove() {
    const keys = Array.from(selectedClients);
    if (keys.length === 0) return;
    fetch('/api/approve-multiple', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ registration_keys: keys })
    }).then(r => r.json()).then(() => {
        showToast(`${keys.length} client(s) approved`, 'success');
        clearSelection();
        refreshClients();
    });
}

function bulkScan() {
    const keys = Array.from(selectedClients);
    if (keys.length === 0) return;
    let done = 0;
    keys.forEach(key => {
        fetch(`/api/clients/${key}/scan-now`, { method: 'POST' })
            .then(() => done++)
            .catch(() => {});
    });
    showToast(`Scan requested for ${keys.length} client(s)`, 'info');
    setTimeout(() => { clearSelection(); refreshClients(); }, 3000);
}

function bulkDelete() {
    const keys = Array.from(selectedClients);
    if (keys.length === 0) return;
    if (!confirm(`Delete ${keys.length} client(s)?`)) return;
    fetch('/api/clients/delete-multiple', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ registration_keys: keys })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            showToast(`${keys.length} client(s) deleted`, 'success');
            clearSelection();
            refreshClients();
        } else {
            showToast('Delete failed: ' + (res.message || 'Unknown error'), 'danger');
        }
    }).catch(err => showToast('Delete failed: ' + err.message, 'danger'));
}

function registerClient() {
    const key = document.getElementById('regKeyInput').value.trim().toUpperCase();
    if (!key || key.length < 4) {
        showToast('Enter a valid registration key (4-8 characters)', 'warning');
        return;
    }
    fetch('/api/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ registration_key: key, hostname: 'Manual', platform: 'Unknown' })
    }).then(r => r.json()).then(() => {
        return fetch('/api/approve', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ registration_key: key })
        });
    }).then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            showToast('Client registered and approved!', 'success');
            document.getElementById('regKeyInput').value = '';
            bootstrap.Modal.getInstance(document.getElementById('registerModal')).hide();
            refreshClients();
        } else {
            showToast('Error: ' + (data.message || 'Unknown'), 'danger');
        }
    }).catch(err => showToast('Error: ' + err.message, 'danger'));
}

function approveClient(key) {
    fetch('/api/approve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ registration_key: key })
    }).then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            showToast('Client approved!', 'success');
            refreshClients();
        }
    });
}

function filterClients() { renderClients(); }

function scanClient(key) {
    const client = clients.find(c => c.registration_key === key);
    const name = client ? (client.hostname || key) : key;
    showToast(`Scan requested for ${name} — waiting for client...`, 'info');
    fetch(`/api/clients/${key}/scan-now`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                let attempts = 0;
                const poll = setInterval(() => {
                    attempts++;
                    if (attempts > 40) { clearInterval(poll); refreshClients(); return; }
                    fetch('/api/clients').then(r => r.json()).then(clientsData => {
                        clients = clientsData;
                        renderStats(); renderCharts(); renderClients();
                        const updated = clients.find(c => c.registration_key === key);
                        if (updated && !updated.scan_requested) { clearInterval(poll); showToast(`Scan completed for ${name}!`, 'success'); }
                    }).catch(() => {});
                }, 3000);
            }
        });
}

function scanAll() {
    const approved = clients.filter(c => c.approved && !c.deleted);
    if (approved.length === 0) { showToast('No approved clients', 'warning'); return; }
    showToast(`Scan queued for ${approved.length} client(s)`, 'info');
    fetch('/api/scan/all', { method: 'POST' }).then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            let attempts = 0;
            const poll = setInterval(() => {
                attempts++;
                if (attempts > 60) { clearInterval(poll); refreshClients(); return; }
                fetch('/api/clients').then(r => r.json()).then(clientsData => {
                    clients = clientsData;
                    renderStats(); renderCharts(); renderClients();
                    if (clients.filter(c => c.approved).every(c => !c.scan_requested)) { clearInterval(poll); showToast('All clients reported back!', 'success'); }
                }).catch(() => {});
            }, 3000);
        }
    });
}

function scanAdminServer() {
    showToast('Scanning local server...', 'info');
    fetch('/api/scan/local', { method: 'POST' }).then(r => r.json()).then(data => {
        if (data.status === 'ok') {
            showToast('Server scan started!', 'success');
            setTimeout(refreshClients, 3000);
        }
    }).catch(err => showToast('Error: ' + err.message, 'danger'));
}

function exportCSV() {
    if (clients.length === 0) { showToast('No clients to export', 'warning'); return; }
    const headers = ['Hostname', 'Key', 'Platform', 'Group', 'Tags', 'Status', 'Last IP', 'Last Seen', 'Cost', 'Vendor', 'Notes'];
    const rows = clients.map(c => [
        c.hostname || '', c.registration_key, c.platform || '', c.group_name || '', (c.tags_list || []).join('; '),
        c.deleted ? 'deleted' : (c.status || ''), c.last_ip || '', c.last_seen || '', c.purchase_cost || '', c.vendor_name || '', (c.notes || '').replace(/"/g, '""')
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.map(v => '"' + v + '"').join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'clients_export.csv'; a.click();
    URL.revokeObjectURL(url);
    showToast('CSV exported!', 'success');
}

function loadActivityLog() {
    fetch('/api/activity-log?limit=50').then(r => r.json()).then(logs => {
        const tbody = document.getElementById('activityLogBody');
        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary">No activity</td></tr>';
        } else {
            tbody.innerHTML = logs.map(l => `<tr>
                <td class="small text-secondary">${timeAgo(l.created_at)}</td>
                <td><span class="badge bg-${l.action === 'scan' ? 'success' : l.action === 'approve' ? 'info' : l.action === 'delete' ? 'danger' : l.action === 'login' ? 'warning' : 'secondary'}">${l.action}</span></td>
                <td>${escapeHtml(l.client_hostname || '-')}</td>
                <td class="small">${escapeHtml(l.details)}</td>
            </tr>`).join('');
        }
        new bootstrap.Modal(document.getElementById('activityModal')).show();
    });
}

refreshClients();
refreshInterval = setInterval(refreshClients, 10000);
