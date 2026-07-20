let departments = [];
let locations = [];
let refreshInterval;
let deptChart = null;

function statusBadge(status) {
    const map = { Active: 'bg-success', Disabled: 'bg-warning', Archived: 'bg-secondary' };
    return `<span class="badge ${map[status] || 'bg-secondary'}">${escapeHtml(status)}</span>`;
}

function formatCurrency(val) {
    return '$' + parseFloat(val || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function refreshDepartments() {
    Promise.all([
        fetch('/api/departments').then(r => r.json()),
        fetch('/api/locations').then(r => r.json()).catch(() => []),
    ]).then(([deptData, locData]) => {
        departments = deptData;
        locations = locData;
        renderStats();
        renderDepartments();
    }).catch(err => showToast('Failed to load departments: ' + err.message, 'danger'));
}

function renderStats() {
    document.getElementById('totalDepts').textContent = departments.length;
    document.getElementById('activeDepts').textContent = departments.filter(d => d.status === 'Active').length;
    document.getElementById('totalEmployees').textContent = departments.reduce((s, d) => s + (d.employee_count || 0), 0);
    document.getElementById('totalAssets').textContent = departments.reduce((s, d) => s + (d.asset_count || 0), 0);
}

function renderDepartments() {
    const tbody = document.getElementById('deptTableBody');
    if (!tbody) return;
    const filtered = getFilteredDepartments();
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-secondary py-4"><i class="bi bi-diagram-3 fs-1 d-block mb-2"></i>No departments found</td></tr>';
        updateFilterCount(0);
        return;
    }
    tbody.innerHTML = filtered.map(d => {
        const name = escapeHtml(d.name || '');
        const code = escapeHtml(d.code || '');
        const head = escapeHtml(d.department_head || '—');
        const loc = escapeHtml(d.location_name || '—');
        const empCount = d.employee_count || 0;
        const assetCount = d.asset_count || 0;
        const budget = d.budget ? formatCurrency(d.budget) : '—';
        const status = d.status || 'Active';
        const isActive = status === 'Active';
        return `<tr>
            <td class="fw-semibold">${name}</td>
            <td><code class="text-secondary">${code}</code></td>
            <td>${head}</td>
            <td>${loc}</td>
            <td class="text-center">${empCount}</td>
            <td class="text-center">${assetCount}</td>
            <td>${budget}</td>
            <td>${statusBadge(status)}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-info" title="Dashboard" onclick="viewDashboard('${d.id}')"><i class="bi bi-pie-chart"></i></button>
                    <button class="btn btn-outline-primary" title="Edit" onclick="editDepartment('${d.id}')"><i class="bi bi-pencil"></i></button>
                    <button class="btn ${isActive ? 'btn-outline-warning' : 'btn-outline-success'}" title="${isActive ? 'Disable' : 'Enable'}" onclick="toggleDeptStatus('${d.id}', '${status}')"><i class="bi ${isActive ? 'bi-x-circle' : 'bi-check-circle'}"></i></button>
                </div>
            </td>
        </tr>`;
    }).join('');
    updateFilterCount(filtered.length);
}

function getFilteredDepartments() {
    const search = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const status = document.getElementById('statusFilter')?.value || 'all';
    return departments.filter(d => {
        if (search) {
            const haystack = `${d.name} ${d.code} ${d.department_head || ''}`.toLowerCase();
            if (!haystack.includes(search)) return false;
        }
        if (status !== 'all' && d.status !== status) return false;
        return true;
    });
}

function updateFilterCount(count) {
    const el = document.getElementById('filterCount');
    if (el) {
        el.textContent = count < departments.length
            ? `Showing ${count} of ${departments.length}`
            : `${departments.length} department${departments.length !== 1 ? 's' : ''}`;
    }
}

function filterDepartments() {
    renderDepartments();
}

function populateLocationsDropdown(selectEl) {
    if (!selectEl) return;
    selectEl.innerHTML = '<option value="">Select location...</option>';
    locations.forEach(loc => {
        selectEl.innerHTML += `<option value="${escapeHtml(loc.id)}">${escapeHtml(loc.office_name)} - ${escapeHtml(loc.city)}</option>`;
    });
}

function openAddDeptModal() {
    document.getElementById('editDeptId').value = '';
    document.getElementById('deptForm').reset();
    document.getElementById('deptModalTitle').innerHTML = '<i class="bi bi-diagram-3 me-2"></i>Add Department';
    populateLocationsDropdown(document.getElementById('deptLocation'));
    new bootstrap.Modal(document.getElementById('deptModal')).show();
}

function openImportModal() {
    document.getElementById('importFile').value = '';
    document.getElementById('importResults').innerHTML = '';
    new bootstrap.Modal(document.getElementById('importModal')).show();
}

function editDepartment(id) {
    const dept = departments.find(d => d.id === id);
    if (!dept) return showToast('Department not found', 'danger');
    document.getElementById('editDeptId').value = dept.id;
    document.getElementById('deptName').value = dept.name || '';
    document.getElementById('deptCode').value = dept.code || '';
    document.getElementById('deptDescription').value = dept.description || '';
    document.getElementById('deptHead').value = dept.department_head || '';
    document.getElementById('deptEmail').value = dept.email || '';
    document.getElementById('deptPhone').value = dept.phone_number || '';
    document.getElementById('deptBudget').value = dept.budget || '';
    document.getElementById('deptStatus').value = dept.status || 'Active';
    document.getElementById('deptNotes').value = dept.notes || '';
    document.getElementById('deptModalTitle').innerHTML = '<i class="bi bi-pencil me-2"></i>Edit Department';
    populateLocationsDropdown(document.getElementById('deptLocation'));
    setTimeout(() => {
        document.getElementById('deptLocation').value = dept.location || '';
    }, 50);
    new bootstrap.Modal(document.getElementById('deptModal')).show();
}

function saveDepartment() {
    const id = document.getElementById('editDeptId').value;
    const name = document.getElementById('deptName').value.trim();
    const code = document.getElementById('deptCode').value.trim();
    if (!name || !code) return showToast('Name and code are required', 'warning');
    const payload = {
        name: name,
        code: code,
        description: document.getElementById('deptDescription').value.trim(),
        department_head: document.getElementById('deptHead').value.trim(),
        email: document.getElementById('deptEmail').value.trim(),
        phone_number: document.getElementById('deptPhone').value.trim(),
        location: document.getElementById('deptLocation').value || null,
        budget: document.getElementById('deptBudget').value ? parseFloat(document.getElementById('deptBudget').value) : null,
        status: document.getElementById('deptStatus').value,
        notes: document.getElementById('deptNotes').value.trim(),
    };
    const url = id ? `/api/departments/${id}` : '/api/departments';
    const method = id ? 'PUT' : 'POST';
    fetch(url, {
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message || 'Save failed'); });
        return r.json();
    }).then(() => {
        showToast(id ? 'Department updated!' : 'Department created!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('deptModal'))?.hide();
        refreshDepartments();
    }).catch(err => showToast(err.message, 'danger'));
}

function toggleDeptStatus(id, currentStatus) {
    const action = currentStatus === 'Active' ? 'disable' : 'enable';
    if (!confirm(`Are you sure you want to ${action} this department?`)) return;
    const url = currentStatus === 'Active' ? `/api/departments/${id}/disable` : `/api/departments/${id}`;
    const body = currentStatus === 'Active' ? '{}' : JSON.stringify({ status: 'Active' });
    fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body })
        .then(r => { if (!r.ok) throw new Error('Failed'); return r.json(); })
        .then(() => { showToast(`Department ${action}d`, 'success'); refreshDepartments(); })
        .catch(err => showToast(err.message, 'danger'));
}

function deleteDepartment(id, name) {
    document.getElementById('confirmMessage').textContent = `Are you sure you want to delete "${name}"?`;
    const btn = document.getElementById('confirmBtn');
    btn.onclick = function () {
        fetch(`/api/departments/${id}/delete`, { method: 'POST' }).then(r => r.json()).then(res => {
            if (res.status === 'ok') {
                showToast('Department deleted', 'success');
                bootstrap.Modal.getInstance(document.getElementById('confirmModal'))?.hide();
                refreshDepartments();
            } else {
                showToast(res.message || 'Failed to delete', 'danger');
            }
        }).catch(err => showToast(err.message, 'danger'));
    };
    new bootstrap.Modal(document.getElementById('confirmModal')).show();
}

function viewDashboard(id) {
    const dept = departments.find(d => d.id === id);
    fetch(`/api/departments/${id}/dashboard`).then(r => r.json()).then(data => {
        document.getElementById('dashTotalAssets').textContent = data.total_assets || 0;
        document.getElementById('dashAssignedAssets').textContent = data.assigned_assets || 0;
        document.getElementById('dashEmployees').textContent = data.employees_count || 0;
        document.getElementById('dashMaintenance').textContent = data.maintenance_count || 0;
        document.getElementById('dashAssetValue').textContent = formatCurrency(data.asset_value);
        document.getElementById('dashOnline').textContent = data.online_devices || 0;
        document.getElementById('dashOffline').textContent = data.offline_devices || 0;
        document.getElementById('dashboardContent').innerHTML = `
            <p><strong>${escapeHtml(dept?.name || 'Department')}</strong></p>
            <p>Status: ${statusBadge(dept?.status || 'Active')}</p>
            ${dept?.budget ? `<p>Budget: ${formatCurrency(dept.budget)}</p>` : ''}
        `;
        const canvas = document.getElementById('deptAssetChart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            if (deptChart) deptChart.destroy();
            deptChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Online', 'Offline', 'Maintenance'],
                    datasets: [{
                        data: [data.online_devices || 0, data.offline_devices || 0, data.maintenance_count || 0],
                        backgroundColor: ['#22c55e', '#ef4444', '#eab308'], borderWidth: 0
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom', labels: { color: '#8888a0', padding: 12 } } }
                }
            });
        }
        new bootstrap.Modal(document.getElementById('dashboardModal')).show();
    }).catch(err => showToast(err.message, 'danger'));
}

function exportCSV() {
    window.open('/api/departments/export?format=csv', '_blank');
}

function exportPDF() {
    if (departments.length === 0) return showToast('No departments to export', 'warning');
    let rows = departments.map(d => `<tr>
        <td>${escapeHtml(d.name)}</td><td>${escapeHtml(d.code || '')}</td>
        <td>${escapeHtml(d.department_head || '—')}</td><td>${escapeHtml(d.location_name || '—')}</td>
        <td>${d.employee_count || 0}</td><td>${d.asset_count || 0}</td>
        <td>${d.budget ? formatCurrency(d.budget) : '—'}</td><td>${escapeHtml(d.status)}</td>
    </tr>`).join('');
    const html = `<!DOCTYPE html><html><head><title>Departments Report</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>@media print{body{padding:0;}}</style></head><body style="padding:20px;">
        <h3>Departments Report</h3><p class="text-muted small">Generated: ${new Date().toLocaleString()}</p>
        <table class="table table-bordered table-sm"><thead><tr>
            <th>Name</th><th>Code</th><th>Head</th><th>Location</th><th>Employees</th><th>Assets</th><th>Budget</th><th>Status</th>
        </tr></thead><tbody>${rows}</tbody></table></body></html>`;
    const win = window.open('', '_blank');
    if (win) { win.document.write(html); win.document.close(); win.print(); }
    else showToast('Pop-up blocked', 'warning');
}

function importDepartments() {
    const fileInput = document.getElementById('importFile');
    if (!fileInput.files || !fileInput.files[0]) return showToast('Please select a file', 'warning');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('dry_run', document.getElementById('dryRun')?.checked ? 'true' : 'false');
    const results = document.getElementById('importResults');
    results.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm me-1"></div>Importing...</div>';
    fetch('/api/departments/import', { method: 'POST', body: formData }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            let html = `<div class="alert alert-success">${res.success_count} department(s) imported.</div>`;
            if (res.errors && res.errors.length > 0) {
                html += '<div class="mt-2 small"><strong>Errors:</strong><ul class="mb-0">';
                res.errors.forEach(e => { html += `<li class="text-danger">Row ${e.row}: ${escapeHtml(e.message)}</li>`; });
                html += '</ul></div>';
            }
            results.innerHTML = html;
            if (!res.dry_run) { showToast(`${res.success_count} departments imported!`, 'success'); refreshDepartments(); }
        } else {
            results.innerHTML = `<div class="alert alert-danger">${escapeHtml(res.message || 'Import failed')}</div>`;
        }
    }).catch(err => { results.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`; });
}

document.addEventListener('DOMContentLoaded', () => {
    refreshDepartments();
    refreshInterval = setInterval(refreshDepartments, 10000);
});
