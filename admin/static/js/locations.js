let locations = [];
let refreshInterval;
let locChart = null;

function formatCurrency(val) {
    return '$' + parseFloat(val || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function statusBadge(status) {
    const s = (status || 'active').toLowerCase();
    const color = s === 'active' ? 'success' : s === 'archived' ? 'secondary' : s === 'closed' ? 'danger' : 'secondary';
    return `<span class="badge bg-${color}">${escapeHtml(s)}</span>`;
}

function refreshLocations() {
    const search = document.getElementById('searchInput')?.value || '';
    const city = document.getElementById('cityFilter')?.value || '';
    const status = document.getElementById('statusFilter')?.value || '';
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (city && city !== 'all') params.set('city', city);
    if (status && status !== 'all') params.set('status', status);

    fetch('/api/locations' + (params.toString() ? '?' + params.toString() : ''))
        .then(r => r.json())
        .then(data => {
            locations = Array.isArray(data) ? data : (data.locations || []);
            renderStats();
            populateCityFilter();
            renderLocations();
        })
        .catch(err => showToast('Failed to load locations: ' + err.message, 'danger'));
}

function renderStats() {
    const total = locations.length;
    const active = locations.filter(l => (l.status || '').toLowerCase() === 'active').length;
    const onlineDevices = locations.reduce((sum, l) => sum + (l.online_devices || 0), 0);
    const totalAssetValue = locations.reduce((sum, l) => sum + parseFloat(l.asset_value || l.total_asset_value || 0), 0);

    const elTotal = document.getElementById('totalLocations');
    const elActive = document.getElementById('activeLocations');
    const elOnline = document.getElementById('onlineDevices');
    const elValue = document.getElementById('totalAssetValue');
    if (elTotal) elTotal.textContent = total;
    if (elActive) elActive.textContent = active;
    if (elOnline) elOnline.textContent = onlineDevices;
    if (elValue) elValue.textContent = formatCurrency(totalAssetValue);
}

function populateCityFilter() {
    const sel = document.getElementById('cityFilter');
    if (!sel) return;
    const current = sel.value || 'all';
    const cities = [...new Set(locations.map(l => l.city).filter(Boolean))].sort();
    sel.innerHTML = '<option value="all">All Cities</option>' + cities.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    sel.value = current;
}

function renderLocations() {
    const tbody = document.getElementById('locTableBody');
    if (!tbody) return;

    const searchTerm = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const cityFilter = document.getElementById('cityFilter')?.value || 'all';
    const statusFilter = document.getElementById('statusFilter')?.value || 'all';

    const filtered = locations.filter(l => {
        if (searchTerm) {
            const haystack = [l.office_name, l.building_name, l.city, l.country, l.address].join(' ').toLowerCase();
            if (!haystack.includes(searchTerm)) return false;
        }
        if (cityFilter !== 'all' && l.city !== cityFilter) return false;
        if (statusFilter !== 'all' && (l.status || '').toLowerCase() !== statusFilter) return false;
        return true;
    });

    const filterCount = document.getElementById('filterCount');
    if (filterCount) {
        filterCount.textContent = filtered.length < locations.length
            ? `Showing ${filtered.length} of ${locations.length}`
            : `${locations.length} location${locations.length !== 1 ? 's' : ''}`;
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-secondary py-4"><i class="bi bi-geo-alt fs-1 d-block mb-2"></i>No locations found</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(l => `<tr>
        <td class="fw-semibold">${escapeHtml(l.office_name || '')}</td>
        <td>${escapeHtml(l.building_name || '-')}</td>
        <td>${escapeHtml(l.floor || '-')}</td>
        <td>${escapeHtml(l.city || '-')}</td>
        <td>${escapeHtml(l.country || '-')}</td>
        <td>${l.employee_count ?? l.employees ?? 0}</td>
        <td>${l.asset_count ?? l.assets ?? 0}</td>
        <td>${statusBadge(l.status)}</td>
        <td class="text-end text-nowrap">
            <button class="btn btn-sm btn-outline-info me-1" onclick="viewDashboard('${l.id}')" title="Dashboard">
                <i class="bi bi-speedometer2"></i>
            </button>
            <button class="btn btn-sm btn-outline-primary me-1" onclick="editLocation('${l.id}')" title="Edit">
                <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" onclick="archiveLocation('${l.id}', '${escapeHtml(l.office_name || '')}')" title="Archive">
                <i class="bi bi-archive"></i>
            </button>
        </td>
    </tr>`).join('');
}

function filterLocations() {
    renderLocations();
}

function openAddLocationModal() {
    document.getElementById('locModalTitle').innerHTML = '<i class="bi bi-geo-alt me-2"></i>Add Location';
    document.getElementById('editLocId').value = '';
    document.getElementById('locForm').reset();
    document.getElementById('locStatus').value = 'active';
    document.getElementById('locTimezone').value = 'UTC';
    new bootstrap.Modal(document.getElementById('locModal')).show();
}

function editLocation(id) {
    const loc = locations.find(l => l.id === id);
    if (!loc) {
        showToast('Location not found', 'danger');
        return;
    }

    document.getElementById('locModalTitle').innerHTML = '<i class="bi bi-geo-alt me-2"></i>Edit Location';
    document.getElementById('editLocId').value = loc.id;
    document.getElementById('locOfficeName').value = loc.office_name || '';
    document.getElementById('locBuildingName').value = loc.building_name || '';
    document.getElementById('locFloor').value = loc.floor || '';
    document.getElementById('locRoom').value = loc.room_number || loc.room || '';
    document.getElementById('locPostalCode').value = loc.postal_code || '';
    document.getElementById('locAddress').value = loc.address || '';
    document.getElementById('locCity').value = loc.city || '';
    document.getElementById('locState').value = loc.state || '';
    document.getElementById('locCountry').value = loc.country || '';
    document.getElementById('locContact').value = loc.contact_number || loc.contact || '';
    document.getElementById('locManager').value = loc.office_manager || loc.manager || '';
    document.getElementById('locTimezone').value = loc.timezone || 'UTC';
    document.getElementById('locStatus').value = (loc.status || 'active').toLowerCase();
    document.getElementById('locNotes').value = loc.notes || '';

    new bootstrap.Modal(document.getElementById('locModal')).show();
}

function saveLocation() {
    const id = document.getElementById('editLocId').value;
    const payload = {
        office_name: document.getElementById('locOfficeName').value.trim(),
        building_name: document.getElementById('locBuildingName').value.trim(),
        floor: document.getElementById('locFloor').value.trim(),
        room_number: document.getElementById('locRoom').value.trim(),
        postal_code: document.getElementById('locPostalCode').value.trim(),
        address: document.getElementById('locAddress').value.trim(),
        city: document.getElementById('locCity').value.trim(),
        state: document.getElementById('locState').value.trim(),
        country: document.getElementById('locCountry').value.trim(),
        contact_number: document.getElementById('locContact').value.trim(),
        office_manager: document.getElementById('locManager').value.trim(),
        timezone: document.getElementById('locTimezone').value,
        status: document.getElementById('locStatus').value,
        notes: document.getElementById('locNotes').value.trim(),
    };

    if (!payload.office_name) {
        showToast('Office name is required', 'warning');
        return;
    }

    const url = id ? `/api/locations/${id}` : '/api/locations';
    const method = id ? 'PUT' : 'POST';

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(res => {
            if (res.error) {
                showToast(res.error, 'danger');
                return;
            }
            bootstrap.Modal.getInstance(document.getElementById('locModal')).hide();
            showToast(id ? 'Location updated!' : 'Location created!', 'success');
            refreshLocations();
        })
        .catch(err => showToast('Save failed: ' + err.message, 'danger'));
}

function viewDashboard(id) {
    const modal = new bootstrap.Modal(document.getElementById('dashboardModal'));
    document.getElementById('dashTotalAssets').textContent = '...';
    document.getElementById('dashOnlineDevices').textContent = '...';
    document.getElementById('dashOfflineDevices').textContent = '...';
    document.getElementById('dashActiveEmployees').textContent = '...';
    document.getElementById('dashAssetValue').textContent = '...';
    document.getElementById('recentActivities').innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Loading...</div>';
    modal.show();

    fetch(`/api/locations/${id}/dashboard`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('dashTotalAssets').textContent = data.total_assets ?? 0;
            document.getElementById('dashOnlineDevices').textContent = data.online_devices ?? 0;
            document.getElementById('dashOfflineDevices').textContent = data.offline_devices ?? 0;
            document.getElementById('dashActiveEmployees').textContent = data.active_employees ?? 0;
            document.getElementById('dashAssetValue').textContent = formatCurrency(data.asset_value);

            const online = data.online_devices || 0;
            const offline = data.offline_devices || 0;
            const chartCanvas = document.getElementById('locAssetChart');

            if (locChart) {
                locChart.data.datasets[0].data = [online, offline];
                locChart.update();
            } else if (chartCanvas) {
                locChart = new Chart(chartCanvas.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Online', 'Offline'],
                        datasets: [{
                            data: [online, offline],
                            backgroundColor: ['#22c55e', '#ef4444'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: { color: '#8888a0', padding: 12 }
                            }
                        }
                    }
                });
            }

            const activities = data.recent_activities || [];
            const actContainer = document.getElementById('recentActivities');
            if (activities.length === 0) {
                actContainer.innerHTML = '<div class="text-center py-3">No recent activities</div>';
            } else {
                actContainer.innerHTML = activities.map(a => `<div class="d-flex justify-content-between align-items-start p-2 mb-1 rounded" style="background:rgba(255,255,255,0.05);">
                    <div>
                        <span class="badge bg-${a.action === 'create' ? 'success' : a.action === 'update' ? 'info' : a.action === 'delete' ? 'danger' : a.action === 'archive' ? 'secondary' : 'primary'} me-1">${escapeHtml(a.action || '')}</span>
                        <span>${escapeHtml(a.details || '')}</span>
                    </div>
                    <small class="text-secondary ms-2 text-nowrap">${timeAgo(a.timestamp || a.created_at)}</small>
                </div>`).join('');
            }
        })
        .catch(err => {
            document.getElementById('recentActivities').innerHTML = '<div class="text-center py-3 text-danger">Failed to load dashboard data</div>';
            showToast('Dashboard load failed: ' + err.message, 'danger');
        });
}

function archiveLocation(id, name) {
    const msg = document.getElementById('confirmMessage');
    const btn = document.getElementById('confirmBtn');
    msg.textContent = `Are you sure you want to archive "${name}"?`;
    btn.className = 'btn btn-secondary';
    btn.textContent = 'Archive';

    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    confirmModal.show();

    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
    newBtn.addEventListener('click', function () {
        fetch(`/api/locations/${id}/archive`, { method: 'POST' })
            .then(r => r.json())
            .then(res => {
                if (res.error) {
                    showToast(res.error, 'danger');
                    return;
                }
                confirmModal.hide();
                showToast('Location archived!', 'success');
                refreshLocations();
            })
            .catch(err => showToast('Archive failed: ' + err.message, 'danger'));
    });
}

function deleteLocation(id, name) {
    const msg = document.getElementById('confirmMessage');
    const btn = document.getElementById('confirmBtn');
    msg.textContent = `Are you sure you want to delete "${name}"? This action cannot be undone.`;
    btn.className = 'btn btn-danger';
    btn.textContent = 'Delete';

    const confirmModal = new bootstrap.Modal(document.getElementById('confirmModal'));
    confirmModal.show();

    const newBtn = btn.cloneNode(true);
    btn.parentNode.replaceChild(newBtn, btn);
    newBtn.addEventListener('click', function () {
        fetch(`/api/locations/${id}/delete`, { method: 'POST' })
            .then(r => r.json())
            .then(res => {
                if (res.error) {
                    showToast(res.error, 'danger');
                    return;
                }
                confirmModal.hide();
                showToast('Location deleted!', 'success');
                refreshLocations();
            })
            .catch(err => showToast('Delete failed: ' + err.message, 'danger'));
    });
}

function exportLocationsCSV() {
    window.open('/api/locations/export?format=csv', '_blank');
    showToast('CSV export started!', 'success');
}

function exportLocationsPDF() {
    let printContent = '<!DOCTYPE html><html><head><title>Locations Report</title>';
    printContent += '<style>body{font-family:Arial,sans-serif;padding:20px;}table{width:100%;border-collapse:collapse;margin-top:10px;}th,td{border:1px solid #ddd;padding:8px;text-align:left;font-size:12px;}th{background:#f0f0f0;}h1{font-size:18px;}h2{font-size:14px;color:#555;}</style>';
    printContent += '</head><body>';
    printContent += '<h1>Office Locations Report</h1>';
    printContent += '<h2>Generated: ' + new Date().toLocaleString() + '</h2>';
    printContent += '<p>Total Locations: ' + locations.length + ' | Active: ' + locations.filter(l => (l.status || '').toLowerCase() === 'active').length + '</p>';
    printContent += '<table><thead><tr><th>Office</th><th>Building</th><th>Floor</th><th>City</th><th>Country</th><th>Employees</th><th>Assets</th><th>Status</th></tr></thead><tbody>';
    locations.forEach(l => {
        printContent += `<tr><td>${escapeHtml(l.office_name || '')}</td><td>${escapeHtml(l.building_name || '')}</td><td>${escapeHtml(l.floor || '')}</td><td>${escapeHtml(l.city || '')}</td><td>${escapeHtml(l.country || '')}</td><td>${l.employee_count ?? l.employees ?? 0}</td><td>${l.asset_count ?? l.assets ?? 0}</td><td>${escapeHtml(l.status || 'active')}</td></tr>`;
    });
    printContent += '</tbody></table></body></html>';

    const win = window.open('', '_blank');
    win.document.write(printContent);
    win.document.close();
    win.print();
}

function importLocations() {
    const fileInput = document.getElementById('importFile');
    const dryRun = document.getElementById('dryRun').checked;
    const resultsDiv = document.getElementById('importResults');

    if (!fileInput.files || !fileInput.files[0]) {
        showToast('Please select a file', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('dry_run', dryRun);

    resultsDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Importing...</div>';

    fetch('/api/locations/import', {
        method: 'POST',
        body: formData
    })
        .then(r => r.json())
        .then(res => {
            if (res.error) {
                resultsDiv.innerHTML = `<div class="alert alert-danger">${escapeHtml(res.error)}</div>`;
                return;
            }
            let html = '<div class="alert alert-info">';
            if (res.imported !== undefined || res.created !== undefined) {
                html += `<div>Imported: <strong>${res.imported ?? res.created ?? 0}</strong></div>`;
            }
            if (res.updated !== undefined) {
                html += `<div>Updated: <strong>${res.updated}</strong></div>`;
            }
            if (res.skipped !== undefined) {
                html += `<div>Skipped: <strong>${res.skipped}</strong></div>`;
            }
            if (res.errors && res.errors.length > 0) {
                html += '<div class="mt-2 text-danger"><strong>Errors:</strong><ul class="mb-0">';
                res.errors.forEach(e => {
                    html += `<li class="small">${escapeHtml(String(e))}</li>`;
                });
                html += '</ul></div>';
            }
            if (res.message) {
                html += `<div class="mt-1">${escapeHtml(res.message)}</div>`;
            }
            html += '</div>';
            if (dryRun) {
                html += '<div class="text-warning small mb-2">This was a dry run. Uncheck "Dry run" to apply changes.</div>';
            }
            resultsDiv.innerHTML = html;

            if (!dryRun) {
                showToast('Import completed!', 'success');
                refreshLocations();
            }
        })
        .catch(err => {
            resultsDiv.innerHTML = `<div class="alert alert-danger">Import failed: ${escapeHtml(err.message)}</div>`;
            showToast('Import failed: ' + err.message, 'danger');
        });
}

document.addEventListener('DOMContentLoaded', function () {
    refreshLocations();
    refreshInterval = setInterval(refreshLocations, 10000);
});
