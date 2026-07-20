let employees = [];
let departments = [];
let locations = [];
let refreshInterval;
let editEmployeeId = null;

function refreshEmployees() {
    Promise.all([
        fetch('/api/employees').then(r => r.json()),
        fetch('/api/departments').then(r => r.json()).catch(() => []),
        fetch('/api/locations').then(r => r.json()).catch(() => []),
    ]).then(([data, deptData, locData]) => {
        employees = data;
        departments = deptData;
        locations = locData;
        updateDropdowns();
        renderStats();
        renderEmployees();
    }).catch(err => showToast('Failed to load employees: ' + err.message, 'danger'));
}

function updateDropdowns() {
    const deptFilter = document.getElementById('deptFilter');
    if (deptFilter) {
        const current = deptFilter.value;
        deptFilter.innerHTML = '<option value="all">All Departments</option>' +
            departments.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.name)}</option>`).join('');
        deptFilter.value = current;
    }
    const locFilter = document.getElementById('locFilter');
    if (locFilter) {
        const current = locFilter.value;
        locFilter.innerHTML = '<option value="all">All Locations</option>' +
            locations.map(l => `<option value="${escapeHtml(l.id)}">${escapeHtml(l.office_name)}</option>`).join('');
        locFilter.value = current;
    }
    const deptSelect = document.getElementById('empDepartment');
    if (deptSelect) {
        const current = deptSelect.value;
        deptSelect.innerHTML = '<option value="">Select Department</option>' +
            departments.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.name)}</option>`).join('');
        if (current) deptSelect.value = current;
    }
    const locSelect = document.getElementById('empLocation');
    if (locSelect) {
        const current = locSelect.value;
        locSelect.innerHTML = '<option value="">Select Location</option>' +
            locations.map(l => `<option value="${escapeHtml(l.id)}">${escapeHtml(l.office_name)}</option>`).join('');
        if (current) locSelect.value = current;
    }
    const reportsTo = document.getElementById('empReportsTo');
    if (reportsTo) {
        const current = reportsTo.value;
        reportsTo.innerHTML = '<option value="">Select Manager</option>' +
            employees.filter(e => e.status === 'Active').map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.full_name)}</option>`).join('');
        if (current) reportsTo.value = current;
    }
}

function renderStats() {
    const total = employees.length;
    const active = employees.filter(e => e.status === 'Active').length;
    const onLeave = employees.filter(e => e.status === 'On Leave').length;
    const assigned = employees.reduce((sum, e) => sum + (e.active_asset_count || 0), 0);
    document.getElementById('totalEmployees').textContent = total;
    document.getElementById('activeEmployees').textContent = active;
    document.getElementById('onLeaveEmployees').textContent = onLeave;
    document.getElementById('assignedAssets').textContent = assigned;
}

function renderEmployees() {
    const tbody = document.getElementById('employeeTableBody');
    if (!tbody) return;
    const filtered = getFilteredEmployees();
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-secondary py-4"><i class="bi bi-people fs-1 d-block mb-2"></i>No employees found</td></tr>';
        updateFilterCount(0);
        return;
    }
    const badgeMap = {
        'Active': 'bg-success', 'Inactive': 'bg-secondary', 'Resigned': 'bg-warning',
        'On Leave': 'bg-info', 'Terminated': 'bg-danger', 'Retired': 'bg-dark'
    };
    tbody.innerHTML = filtered.map(e => {
        const name = escapeHtml(e.full_name || 'Unknown');
        const code = escapeHtml(e.employee_code || '-');
        const dept = escapeHtml(e.department_name || '-');
        const loc = escapeHtml(e.location_name || '-');
        const designation = escapeHtml(e.designation || '-');
        const status = e.status || 'Active';
        const badgeClass = badgeMap[status] || 'bg-secondary';
        const assets = e.active_asset_count || 0;
        const img = e.profile_image
            ? `<img src="${escapeHtml(e.profile_image)}" class="rounded-circle me-2" style="width:28px;height:28px;object-fit:cover;">`
            : `<span class="rounded-circle me-2 d-inline-flex align-items-center justify-content-center bg-secondary text-white" style="width:28px;height:28px;font-size:0.75rem;">${name[0]}</span>`;
        const isActive = status === 'Active' || status === 'On Leave';
        return `<tr>
            <td><code class="text-secondary">${code}</code></td>
            <td>${img}<span class="fw-semibold">${name}</span></td>
            <td>${dept}</td>
            <td>${loc}</td>
            <td class="small">${designation}</td>
            <td><span class="badge ${badgeClass}">${escapeHtml(status)}</span></td>
            <td class="text-center">${assets}</td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-info" onclick="viewProfile('${e.id}')" title="View"><i class="bi bi-eye"></i></button>
                    <button class="btn btn-outline-primary" onclick="editEmployee('${e.id}')" title="Edit"><i class="bi bi-pencil"></i></button>
                    <button class="btn ${isActive ? 'btn-outline-warning' : 'btn-outline-success'}" onclick="toggleEmployeeStatus('${e.id}', '${escapeHtml(status)}')" title="${isActive ? 'Deactivate' : 'Reactivate'}"><i class="bi ${isActive ? 'bi-pause-circle' : 'bi-play-circle'}"></i></button>
                </div>
            </td>
        </tr>`;
    }).join('');
    updateFilterCount(filtered.length);
}

function getFilteredEmployees() {
    const search = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const deptVal = document.getElementById('deptFilter')?.value || 'all';
    const locVal = document.getElementById('locFilter')?.value || 'all';
    const statusVal = document.getElementById('statusFilter')?.value || 'all';
    return employees.filter(e => {
        if (search) {
            const haystack = `${e.full_name} ${e.employee_code} ${e.email} ${e.designation}`.toLowerCase();
            if (!haystack.includes(search)) return false;
        }
        if (deptVal !== 'all' && e.department !== deptVal) return false;
        if (locVal !== 'all' && e.location !== locVal) return false;
        if (statusVal !== 'all' && e.status !== statusVal) return false;
        return true;
    });
}

function updateFilterCount(count) {
    const el = document.getElementById('filterCount');
    if (el) {
        el.textContent = count < employees.length
            ? `Showing ${count} of ${employees.length}`
            : `${employees.length} employee${employees.length !== 1 ? 's' : ''}`;
    }
}

function filterEmployees() {
    renderEmployees();
}

function openAddEmployee() {
    editEmployeeId = null;
    const form = document.getElementById('employeeForm');
    if (form) form.reset();
    document.getElementById('editEmployeeId').value = '';
    const title = document.getElementById('employeeModalTitle');
    if (title) title.innerHTML = '<i class="bi bi-person-plus me-2"></i>Add Employee';
    updateDropdowns();
}

function editEmployee(id) {
    const emp = employees.find(e => e.id === id);
    if (!emp) return showToast('Employee not found', 'danger');
    editEmployeeId = id;
    document.getElementById('editEmployeeId').value = id;
    const title = document.getElementById('employeeModalTitle');
    if (title) title.innerHTML = '<i class="bi bi-pencil me-2"></i>Edit Employee';
    document.getElementById('empCode').value = emp.employee_code || '';
    document.getElementById('empName').value = emp.full_name || '';
    document.getElementById('empEmail').value = emp.email || '';
    document.getElementById('empPhone').value = emp.phone_number || '';
    document.getElementById('empDesignation').value = emp.designation || '';
    document.getElementById('empManager').value = emp.manager_name || '';
    document.getElementById('empJoiningDate').value = emp.joining_date || '';
    document.getElementById('empStatus').value = emp.status || 'Active';
    document.getElementById('empNotes').value = emp.notes || '';
    updateDropdowns();
    setTimeout(() => {
        document.getElementById('empDepartment').value = emp.department || '';
        document.getElementById('empLocation').value = emp.location || '';
        document.getElementById('empReportsTo').value = emp.reports_to || '';
    }, 50);
    new bootstrap.Modal(document.getElementById('employeeModal')).show();
}

function saveEmployee() {
    const code = document.getElementById('empCode').value.trim();
    const name = document.getElementById('empName').value.trim();
    const email = document.getElementById('empEmail').value.trim();
    if (!code || !name || !email) {
        showToast('Code, name, and email are required', 'warning');
        return;
    }
    const payload = {
        employee_code: code,
        full_name: name,
        email: email,
        phone_number: document.getElementById('empPhone').value.trim(),
        department: document.getElementById('empDepartment').value || null,
        designation: document.getElementById('empDesignation').value.trim(),
        manager_name: document.getElementById('empManager').value.trim(),
        reports_to: document.getElementById('empReportsTo').value || null,
        location: document.getElementById('empLocation').value || null,
        joining_date: document.getElementById('empJoiningDate').value || null,
        status: document.getElementById('empStatus').value,
        notes: document.getElementById('empNotes').value.trim(),
    };
    const url = editEmployeeId ? `/api/employees/${editEmployeeId}` : '/api/employees';
    const method = editEmployeeId ? 'PUT' : 'POST';
    fetch(url, {
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message || 'Save failed'); });
        return r.json();
    }).then(res => {
        showToast(editEmployeeId ? 'Employee updated!' : 'Employee created!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('employeeModal'))?.hide();
        editEmployeeId = null;
        refreshEmployees();
    }).catch(err => showToast(err.message, 'danger'));
}

function viewProfile(id) {
    const emp = employees.find(e => e.id === id);
    if (!emp) return;
    const body = document.getElementById('profileContent');
    body.innerHTML = '<div class="text-center py-4 text-secondary"><div class="spinner-border spinner-border-sm me-2"></div>Loading...</div>';
    document.getElementById('profileModalTitle').innerHTML = `<i class="bi bi-person me-2"></i>${escapeHtml(emp.full_name)}`;
    new bootstrap.Modal(document.getElementById('profileModal')).show();
    Promise.all([
        fetch(`/api/employees/${id}/dashboard`).then(r => r.json()).catch(() => ({})),
        fetch(`/api/employees/${id}/assets`).then(r => r.json()).catch(() => []),
    ]).then(([dashboard, assets]) => {
        const badgeMap = { 'Active': 'bg-success', 'Inactive': 'bg-secondary', 'Resigned': 'bg-warning', 'On Leave': 'bg-info', 'Terminated': 'bg-danger', 'Retired': 'bg-dark' };
        const status = emp.status || 'Active';
        const img = emp.profile_image
            ? `<img src="${escapeHtml(emp.profile_image)}" class="employee-avatar-lg mb-3">`
            : `<div class="employee-avatar-lg mb-3 d-inline-flex align-items-center justify-content-center bg-secondary text-white" style="font-size:2rem;">${(emp.full_name || '?')[0].toUpperCase()}</div>`;
        const assetsList = (assets || []).map(a => {
            const aStatus = a.is_active ? 'Active' : 'Returned';
            const aBadge = a.is_active ? 'bg-success' : 'bg-secondary';
            return `<tr>
                <td>${escapeHtml(a.client_hostname || a.client_key || '-')}</td>
                <td><span class="badge ${aBadge}">${aStatus}</span></td>
                <td class="small">${timeAgo(a.assigned_at)}</td>
                <td class="small">${a.returned_at ? timeAgo(a.returned_at) : '-'}</td>
            </tr>`;
        }).join('');
        body.innerHTML = `
            <div class="text-center mb-4">${img}
                <h5 class="mb-1">${escapeHtml(emp.full_name)}</h5>
                <div><code class="text-secondary">${escapeHtml(emp.employee_code)}</code></div>
                <div class="mt-1"><span class="badge ${badgeMap[status] || 'bg-secondary'}">${escapeHtml(status)}</span></div>
            </div>
            <div class="row g-3 mb-4">
                <div class="col-md-4"><div class="profile-stat-card"><div class="stat-value">${dashboard.total_assigned_assets || 0}</div><div class="stat-label">Total Assigned</div></div></div>
                <div class="col-md-4"><div class="profile-stat-card"><div class="stat-value">${dashboard.current_assets || 0}</div><div class="stat-label">Current</div></div></div>
                <div class="col-md-4"><div class="profile-stat-card"><div class="stat-value">$${(dashboard.asset_value || 0).toLocaleString()}</div><div class="stat-label">Asset Value</div></div></div>
            </div>
            <div class="card mb-3"><div class="card-body">
                <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-person-lines-fill me-1"></i>Details</h6>
                <div class="row small">
                    <div class="col-md-6"><strong>Department:</strong> ${escapeHtml(emp.department_name || '-')}</div>
                    <div class="col-md-6"><strong>Location:</strong> ${escapeHtml(emp.location_name || '-')}</div>
                    <div class="col-md-6"><strong>Designation:</strong> ${escapeHtml(emp.designation || '-')}</div>
                    <div class="col-md-6"><strong>Email:</strong> ${escapeHtml(emp.email || '-')}</div>
                    <div class="col-md-6"><strong>Phone:</strong> ${escapeHtml(emp.phone_number || '-')}</div>
                    <div class="col-md-6"><strong>Manager:</strong> ${escapeHtml(emp.manager_name || '-')}</div>
                </div>
            </div></div>
            <h6 class="text-secondary mb-2"><i class="bi bi-pc-display me-1"></i>Asset History</h6>
            ${assetsList.length ? `<div class="table-responsive"><table class="table table-dark table-hover table-sm mb-0"><thead><tr><th>Asset</th><th>Status</th><th>Assigned</th><th>Returned</th></tr></thead><tbody>${assetsList}</tbody></table></div>` : '<div class="text-secondary small">No assets assigned</div>'}
        `;
    });
}

function toggleEmployeeStatus(id, currentStatus) {
    const isActive = currentStatus === 'Active' || currentStatus === 'On Leave';
    const newStatus = isActive ? 'Inactive' : 'Active';
    fetch(`/api/employees/${id}/deactivate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            showToast(`Employee ${isActive ? 'deactivated' : 'reactivated'}`, 'success');
            refreshEmployees();
        } else {
            showToast(res.message || 'Failed', 'danger');
        }
    }).catch(err => showToast(err.message, 'danger'));
}

function deleteEmployee(id, name) {
    document.getElementById('confirmMessage').innerHTML =
        `Are you sure you want to delete <strong>${escapeHtml(name || 'this employee')}</strong>?`;
    const btn = document.getElementById('confirmBtn');
    btn.onclick = function () {
        fetch(`/api/employees/${id}/delete`, { method: 'POST' }).then(r => r.json()).then(res => {
            if (res.status === 'ok') {
                showToast('Employee deleted', 'success');
                bootstrap.Modal.getInstance(document.getElementById('confirmModal'))?.hide();
                refreshEmployees();
            } else {
                showToast(res.message || 'Failed to delete', 'danger');
            }
        }).catch(err => showToast(err.message, 'danger'));
    };
    new bootstrap.Modal(document.getElementById('confirmModal')).show();
}

function exportCSV() {
    window.open('/api/employees/export?format=csv', '_blank');
}

function exportPDF() {
    if (employees.length === 0) return showToast('No employees to export', 'warning');
    let rows = employees.map(e => `<tr>
        <td>${escapeHtml(e.employee_code || '-')}</td>
        <td>${escapeHtml(e.full_name || '-')}</td>
        <td>${escapeHtml(e.department_name || '-')}</td>
        <td>${escapeHtml(e.location_name || '-')}</td>
        <td>${escapeHtml(e.designation || '-')}</td>
        <td>${escapeHtml(e.email || '-')}</td>
        <td>${escapeHtml(e.phone_number || '-')}</td>
        <td>${escapeHtml(e.status || '-')}</td>
    </tr>`).join('');
    const html = `<!DOCTYPE html><html><head><title>Employee Directory</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>@media print{body{padding:0;}}</style></head><body style="padding:20px;">
        <h3>Employee Directory</h3><p class="text-muted small">Generated: ${new Date().toLocaleString()}</p>
        <table class="table table-bordered table-sm"><thead><tr>
            <th>Code</th><th>Name</th><th>Department</th><th>Location</th><th>Designation</th><th>Email</th><th>Phone</th><th>Status</th>
        </tr></thead><tbody>${rows}</tbody></table></body></html>`;
    const win = window.open('', '_blank');
    if (win) { win.document.write(html); win.document.close(); win.print(); }
    else showToast('Pop-up blocked', 'warning');
}

function openImportModal() {
    document.getElementById('importFile').value = '';
    document.getElementById('importResults').innerHTML = '';
    new bootstrap.Modal(document.getElementById('importModal')).show();
}

function importEmployees() {
    const fileInput = document.getElementById('importFile');
    if (!fileInput.files || !fileInput.files[0]) return showToast('Please select a file', 'warning');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('dry_run', document.getElementById('dryRunCheck')?.checked ? 'true' : 'false');
    const results = document.getElementById('importResults');
    results.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm me-1"></div>Importing...</div>';
    fetch('/api/employees/import', { method: 'POST', body: formData }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            let html = `<div class="alert alert-success">${res.success_count} employee(s) imported successfully.</div>`;
            if (res.errors && res.errors.length > 0) {
                html += '<div class="mt-2"><strong>Errors:</strong><ul class="mb-0 small">';
                res.errors.forEach(e => { html += `<li class="text-danger">Row ${e.row}: ${escapeHtml(e.message)}</li>`; });
                html += '</ul></div>';
            }
            results.innerHTML = html;
            if (!res.dry_run) { showToast(`${res.success_count} employees imported!`, 'success'); refreshEmployees(); }
        } else {
            results.innerHTML = `<div class="alert alert-danger">${escapeHtml(res.message || 'Import failed')}</div>`;
        }
    }).catch(err => { results.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`; });
}

document.addEventListener('DOMContentLoaded', function () {
    refreshEmployees();
    refreshInterval = setInterval(refreshEmployees, 10000);
});
