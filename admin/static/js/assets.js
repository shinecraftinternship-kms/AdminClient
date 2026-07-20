let assets = [];
let categories = [];
let departments = [];
let locations = [];
let vendors = [];
let employees = [];
let refreshInterval;
let editAssetId = null;
let assignAssetId = null;
let transferAssetId = null;

const STATUS_BADGES = {
    'Draft': 'bg-secondary', 'Pending Approval': 'bg-warning text-dark', 'Approved': 'bg-info',
    'Purchased': 'bg-primary', 'Available': 'bg-success', 'Assigned': 'bg-info',
    'Maintenance': 'bg-warning text-dark', 'Returned': 'bg-secondary', 'Lost': 'bg-danger',
    'Damaged': 'bg-danger', 'Retired': 'bg-dark', 'Disposed': 'bg-dark', 'Archived': 'bg-dark',
};

function refreshAssets() {
    Promise.all([
        fetch('/api/assets?page_size=500').then(r => r.json()),
        fetch('/api/asset-categories').then(r => r.json()).catch(() => []),
        fetch('/api/departments').then(r => r.json()).catch(() => []),
        fetch('/api/locations').then(r => r.json()).catch(() => []),
        fetch('/api/asset-vendors').then(r => r.json()).catch(() => []),
        fetch('/api/employees?status=Active').then(r => r.json()).catch(() => []),
    ]).then(([data, catData, deptData, locData, venData, empData]) => {
        assets = data.results || data;
        categories = catData;
        departments = deptData;
        locations = locData;
        vendors = venData;
        employees = empData;
        updateDropdowns();
        renderStats();
        renderAssets();
    }).catch(err => showToast('Failed to load assets: ' + err.message, 'danger'));
}

function updateDropdowns() {
    const catFilter = document.getElementById('categoryFilter');
    if (catFilter) {
        const cur = catFilter.value;
        catFilter.innerHTML = '<option value="all">All Categories</option>' +
            categories.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`).join('');
        catFilter.value = cur;
    }
    const deptFilter = document.getElementById('deptFilter');
    if (deptFilter) {
        const cur = deptFilter.value;
        deptFilter.innerHTML = '<option value="all">All Departments</option>' +
            departments.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.name)}</option>`).join('');
        deptFilter.value = cur;
    }
    const locFilter = document.getElementById('locFilter');
    if (locFilter) {
        const cur = locFilter.value;
        locFilter.innerHTML = '<option value="all">All Locations</option>' +
            locations.map(l => `<option value="${escapeHtml(l.id)}">${escapeHtml(l.office_name)}</option>`).join('');
        locFilter.value = cur;
    }

    ['assetCategory', 'assetDepartment', 'assetLocation', 'assetVendor', 'assetParent'].forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const cur = sel.value;
        if (id === 'assetCategory') {
            sel.innerHTML = '<option value="">Select Category</option>' +
                categories.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)}</option>`).join('');
        } else if (id === 'assetDepartment') {
            sel.innerHTML = '<option value="">Select Department</option>' +
                departments.map(d => `<option value="${escapeHtml(d.id)}">${escapeHtml(d.name)}</option>`).join('');
        } else if (id === 'assetLocation') {
            sel.innerHTML = '<option value="">Select Location</option>' +
                locations.map(l => `<option value="${escapeHtml(l.id)}">${escapeHtml(l.office_name)}</option>`).join('');
        } else if (id === 'assetVendor') {
            sel.innerHTML = '<option value="">Select Vendor</option>' +
                vendors.map(v => `<option value="${escapeHtml(v.id)}">${escapeHtml(v.name)}</option>`).join('');
        } else if (id === 'assetParent') {
            sel.innerHTML = '<option value="">None</option>' +
                assets.filter(a => a.id !== editAssetId).map(a => `<option value="${escapeHtml(a.id)}">${escapeHtml(a.asset_tag)} - ${escapeHtml(a.asset_name)}</option>`).join('');
        }
        sel.value = cur;
    });
}

function renderStats() {
    const total = assets.length;
    const assigned = assets.filter(a => a.asset_status === 'Assigned').length;
    const available = assets.filter(a => ['Available', 'Returned'].includes(a.asset_status)).length;
    const maintenance = assets.filter(a => a.asset_status === 'Maintenance').length;
    document.getElementById('totalAssets').textContent = total;
    document.getElementById('assignedAssets').textContent = assigned;
    document.getElementById('availableAssets').textContent = available;
    document.getElementById('maintenanceAssets').textContent = maintenance;
}

function renderAssets() {
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;
    const filtered = getFilteredAssets();
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-center text-secondary py-4"><i class="bi bi-box-seam fs-1 d-block mb-2"></i>No assets found</td></tr>';
        updateFilterCount(0);
        return;
    }
    tbody.innerHTML = filtered.map(a => {
        const badge = STATUS_BADGES[a.asset_status] || 'bg-secondary';
        const value = a.current_value || a.purchase_cost;
        const valueStr = value ? '$' + Number(value).toLocaleString() : '-';
        const warrantyBadge = a.warranty_status === 'Valid' ? 'bg-success' :
            a.warranty_status === 'Expiring Soon' ? 'bg-warning text-dark' :
            a.warranty_status === 'Expired' ? 'bg-danger' : 'bg-secondary';
        return `<tr>
            <td><code class="text-secondary">${escapeHtml(a.asset_id)}</code></td>
            <td><a href="/assets/${a.id}/" class="text-decoration-none fw-semibold">${escapeHtml(a.asset_name)}</a></td>
            <td><code>${escapeHtml(a.asset_tag)}</code></td>
            <td>${escapeHtml(a.category_name || '-')}</td>
            <td><span class="badge ${badge}">${escapeHtml(a.asset_status)}</span></td>
            <td>${escapeHtml(a.department_name || '-')}</td>
            <td>${escapeHtml(a.location_name || '-')}</td>
            <td>${escapeHtml(a.assigned_to_name || '-')}</td>
            <td class="text-end">${valueStr}</td>
            <td><span class="badge ${warrantyBadge}" style="font-size:0.7rem;">${escapeHtml(a.warranty_status || '-')}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <a href="/assets/${a.id}/" class="btn btn-outline-info" title="View"><i class="bi bi-eye"></i></a>
                    <button class="btn btn-outline-primary" onclick="editAsset('${a.id}')" title="Edit"><i class="bi bi-pencil"></i></button>
                    ${a.asset_status === 'Available' || a.asset_status === 'Returned' ?
                        `<button class="btn btn-outline-success" onclick="openAssignModal('${a.id}')" title="Assign"><i class="bi bi-person-plus"></i></button>` : ''}
                    ${a.asset_status === 'Assigned' ?
                        `<button class="btn btn-outline-warning" onclick="returnAsset('${a.id}')" title="Return"><i class="bi bi-arrow-return-left"></i></button>` : ''}
                    ${a.asset_status === 'Assigned' ?
                        `<button class="btn btn-outline-info" onclick="openTransferModal('${a.id}')" title="Transfer"><i class="bi bi-arrow-left-right"></i></button>` : ''}
                </div>
            </td>
        </tr>`;
    }).join('');
    updateFilterCount(filtered.length);
}

function getFilteredAssets() {
    const search = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const catVal = document.getElementById('categoryFilter')?.value || 'all';
    const deptVal = document.getElementById('deptFilter')?.value || 'all';
    const locVal = document.getElementById('locFilter')?.value || 'all';
    const statusVal = document.getElementById('statusFilter')?.value || 'all';
    return assets.filter(a => {
        if (search) {
            const haystack = `${a.asset_name} ${a.asset_id} ${a.asset_tag} ${a.serial_number} ${a.manufacturer} ${a.model_name}`.toLowerCase();
            if (!haystack.includes(search)) return false;
        }
        if (catVal !== 'all' && a.category !== catVal) return false;
        if (deptVal !== 'all' && a.department !== deptVal) return false;
        if (locVal !== 'all' && a.location !== locVal) return false;
        if (statusVal !== 'all' && a.asset_status !== statusVal) return false;
        return true;
    });
}

function updateFilterCount(count) {
    const el = document.getElementById('filterCount');
    if (el) {
        el.textContent = count < assets.length ? `Showing ${count} of ${assets.length}` : `${assets.length} asset${assets.length !== 1 ? 's' : ''}`;
    }
}

function filterAssets() { renderAssets(); }

function openAddAsset() {
    editAssetId = null;
    const form = document.getElementById('assetForm');
    if (form) form.reset();
    document.getElementById('editAssetId').value = '';
    const title = document.getElementById('assetModalTitle');
    if (title) title.innerHTML = '<i class="bi bi-plus-lg me-2"></i>Add Asset';
    document.getElementById('assetStatus').value = 'Draft';
    updateDropdowns();
}

function editAsset(id) {
    const a = assets.find(x => x.id === id);
    if (!a) return showToast('Asset not found', 'danger');
    editAssetId = id;
    document.getElementById('editAssetId').value = id;
    const title = document.getElementById('assetModalTitle');
    if (title) title.innerHTML = '<i class="bi bi-pencil me-2"></i>Edit Asset';

    document.getElementById('assetName').value = a.asset_name || '';
    document.getElementById('assetTag').value = a.asset_tag || '';
    document.getElementById('assetSerial').value = a.serial_number || '';
    document.getElementById('assetManufacturer').value = a.manufacturer || '';
    document.getElementById('assetModel').value = a.model_name || '';
    document.getElementById('assetDescription').value = a.description || '';
    document.getElementById('assetPurchaseDate').value = a.purchase_date || '';
    document.getElementById('assetPurchaseCost').value = a.purchase_cost || '';
    document.getElementById('assetCurrentValue').value = a.current_value || '';
    document.getElementById('assetResidualValue').value = a.residual_value || '';
    document.getElementById('assetDepreciation').value = a.depreciation_pct || '';
    document.getElementById('assetInvoice').value = a.invoice_number || '';
    document.getElementById('assetPO').value = a.purchase_order_number || '';
    document.getElementById('assetWarrantyStart').value = a.warranty_start || '';
    document.getElementById('assetWarrantyEnd').value = a.warranty_end || '';
    document.getElementById('assetWarrantyProvider').value = a.warranty_provider || '';
    document.getElementById('assetStatus').value = a.asset_status || 'Draft';
    document.getElementById('assetAMC').value = a.amc_details || '';
    document.getElementById('assetNotes').value = a.notes || '';
    document.getElementById('assetTags').value = a.tags || '';

    updateDropdowns();
    setTimeout(() => {
        document.getElementById('assetCategory').value = a.category || '';
        document.getElementById('assetDepartment').value = a.department || '';
        document.getElementById('assetLocation').value = a.location || '';
        document.getElementById('assetVendor').value = a.vendor || '';
        document.getElementById('assetParent').value = a.parent || '';
    }, 50);
    new bootstrap.Modal(document.getElementById('assetModal')).show();
}

function saveAsset() {
    const name = document.getElementById('assetName').value.trim();
    const tag = document.getElementById('assetTag').value.trim();
    const serial = document.getElementById('assetSerial').value.trim();
    if (!name || !tag || !serial) {
        showToast('Name, tag, and serial number are required', 'warning');
        return;
    }
    const payload = {
        asset_name: name, asset_tag: tag, serial_number: serial,
        category: document.getElementById('assetCategory').value || null,
        manufacturer: document.getElementById('assetManufacturer').value.trim(),
        model_name: document.getElementById('assetModel').value.trim(),
        description: document.getElementById('assetDescription').value.trim(),
        purchase_date: document.getElementById('assetPurchaseDate').value || null,
        purchase_cost: document.getElementById('assetPurchaseCost').value || null,
        current_value: document.getElementById('assetCurrentValue').value || null,
        residual_value: document.getElementById('assetResidualValue').value || null,
        depreciation_pct: document.getElementById('assetDepreciation').value || 0,
        invoice_number: document.getElementById('assetInvoice').value.trim(),
        purchase_order_number: document.getElementById('assetPO').value.trim(),
        vendor: document.getElementById('assetVendor').value || null,
        department: document.getElementById('assetDepartment').value || null,
        location: document.getElementById('assetLocation').value || null,
        parent: document.getElementById('assetParent').value || null,
        warranty_start: document.getElementById('assetWarrantyStart').value || null,
        warranty_end: document.getElementById('assetWarrantyEnd').value || null,
        warranty_provider: document.getElementById('assetWarrantyProvider').value.trim(),
        amc_details: document.getElementById('assetAMC').value.trim(),
        asset_status: document.getElementById('assetStatus').value,
        notes: document.getElementById('assetNotes').value.trim(),
        tags: document.getElementById('assetTags').value.trim(),
    };
    const url = editAssetId ? `/api/assets/${editAssetId}` : '/api/assets';
    const method = editAssetId ? 'PUT' : 'POST';
    fetch(url, {
        method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message || 'Save failed'); });
        return r.json();
    }).then(res => {
        showToast(editAssetId ? 'Asset updated!' : 'Asset created!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('assetModal'))?.hide();
        editAssetId = null;
        refreshAssets();
    }).catch(err => showToast(err.message, 'danger'));
}

function openAssignModal(id) {
    const a = assets.find(x => x.id === id);
    if (!a) return;
    assignAssetId = id;
    document.getElementById('assignAssetName').textContent = `${a.asset_name} (${a.asset_tag})`;
    document.getElementById('assignReturnDate').value = '';
    document.getElementById('assignNotes').value = '';
    const sel = document.getElementById('assignEmployee');
    sel.innerHTML = '<option value="">Select Employee</option>' +
        employees.map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.full_name)} (${escapeHtml(e.employee_code)})</option>`).join('');
    new bootstrap.Modal(document.getElementById('assignModal')).show();
}

function confirmAssign() {
    const empId = document.getElementById('assignEmployee').value;
    if (!empId) return showToast('Please select an employee', 'warning');
    fetch(`/api/assets/${assignAssetId}/assign`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            employee: empId,
            expected_return_date: document.getElementById('assignReturnDate').value || null,
            notes: document.getElementById('assignNotes').value.trim(),
        })
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message || 'Assign failed'); });
        return r.json();
    }).then(res => {
        showToast('Asset assigned!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('assignModal'))?.hide();
        refreshAssets();
    }).catch(err => showToast(err.message, 'danger'));
}

function returnAsset(id) {
    document.getElementById('confirmMessage').innerHTML = 'Are you sure you want to return this asset?';
    const btn = document.getElementById('confirmBtn');
    btn.className = 'btn btn-warning';
    btn.textContent = 'Return Asset';
    btn.onclick = function () {
        fetch(`/api/assets/${id}/return`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
            .then(r => { if (!r.ok) return r.json().then(e => { throw new Error(e.message); }); return r.json(); })
            .then(res => {
                if (res.status === 'ok') {
                    showToast('Asset returned!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('confirmModal'))?.hide();
                    refreshAssets();
                } else { showToast(res.message || 'Failed', 'danger'); }
            }).catch(err => showToast(err.message, 'danger'));
    };
    new bootstrap.Modal(document.getElementById('confirmModal')).show();
}

function openTransferModal(id) {
    const a = assets.find(x => x.id === id);
    if (!a) return;
    transferAssetId = id;
    document.getElementById('transferAssetName').textContent = `${a.asset_name} (${a.asset_tag})`;
    document.getElementById('transferReason').value = '';
    document.getElementById('transferNotes').value = '';
    const sel = document.getElementById('transferEmployee');
    sel.innerHTML = '<option value="">Select Employee</option>' +
        employees.map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.full_name)} (${escapeHtml(e.employee_code)})</option>`).join('');
    new bootstrap.Modal(document.getElementById('transferModal')).show();
}

function confirmTransfer() {
    const empId = document.getElementById('transferEmployee').value;
    if (!empId) return showToast('Please select an employee', 'warning');
    fetch(`/api/assets/${transferAssetId}/transfer`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            to_employee: empId,
            reason: document.getElementById('transferReason').value.trim(),
            notes: document.getElementById('transferNotes').value.trim(),
        })
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message || 'Transfer failed'); });
        return r.json();
    }).then(res => {
        showToast('Asset transferred!', 'success');
        bootstrap.Modal.getInstance(document.getElementById('transferModal'))?.hide();
        refreshAssets();
    }).catch(err => showToast(err.message, 'danger'));
}

function exportCSV() {
    const params = new URLSearchParams();
    const s = document.getElementById('searchInput')?.value;
    const c = document.getElementById('categoryFilter')?.value;
    const d = document.getElementById('deptFilter')?.value;
    const l = document.getElementById('locFilter')?.value;
    const st = document.getElementById('statusFilter')?.value;
    if (s) params.set('search', s);
    if (c && c !== 'all') params.set('category', c);
    if (d && d !== 'all') params.set('department', d);
    if (l && l !== 'all') params.set('location', l);
    if (st && st !== 'all') params.set('status', st);
    window.open('/api/assets/export?format=csv&' + params.toString(), '_blank');
}

function exportPDF() {
    if (assets.length === 0) return showToast('No assets to export', 'warning');
    const filtered = getFilteredAssets();
    let rows = filtered.map(a => `<tr>
        <td>${escapeHtml(a.asset_id)}</td><td>${escapeHtml(a.asset_name)}</td>
        <td>${escapeHtml(a.asset_tag)}</td><td>${escapeHtml(a.category_name || '-')}</td>
        <td>${escapeHtml(a.asset_status)}</td><td>${escapeHtml(a.department_name || '-')}</td>
        <td>${escapeHtml(a.location_name || '-')}</td><td>${escapeHtml(a.assigned_to_name || '-')}</td>
        <td>${a.current_value ? '$' + Number(a.current_value).toLocaleString() : '-'}</td>
    </tr>`).join('');
    const html = `<!DOCTYPE html><html><head><title>Asset Report</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>@media print{body{padding:0;}}</style></head><body style="padding:20px;">
        <h3>Asset Report</h3><p class="text-muted small">Generated: ${new Date().toLocaleString()}</p>
        <table class="table table-bordered table-sm"><thead><tr>
            <th>ID</th><th>Name</th><th>Tag</th><th>Category</th><th>Status</th><th>Department</th><th>Location</th><th>Assigned To</th><th>Value</th>
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

function importAssets() {
    const fileInput = document.getElementById('importFile');
    if (!fileInput.files || !fileInput.files[0]) return showToast('Please select a file', 'warning');
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('dry_run', document.getElementById('dryRunCheck')?.checked ? 'true' : 'false');
    const results = document.getElementById('importResults');
    results.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm me-1"></div>Importing...</div>';
    fetch('/api/assets/import', { method: 'POST', body: formData }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            let html = `<div class="alert alert-success">${res.success_count} asset(s) ${res.dry_run ? 'validated' : 'imported'} successfully.</div>`;
            if (res.errors && res.errors.length > 0) {
                html += '<div class="mt-2"><strong>Errors:</strong><ul class="mb-0 small">';
                res.errors.forEach(e => { html += `<li class="text-danger">Row ${e.row}: ${escapeHtml(e.message)}</li>`; });
                html += '</ul></div>';
            }
            results.innerHTML = html;
            if (!res.dry_run) { showToast(`${res.success_count} assets imported!`, 'success'); refreshAssets(); }
        } else {
            results.innerHTML = `<div class="alert alert-danger">${escapeHtml(res.message || 'Import failed')}</div>`;
        }
    }).catch(err => { results.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`; });
}

document.addEventListener('DOMContentLoaded', function () {
    refreshAssets();
    refreshInterval = setInterval(refreshAssets, 15000);
});
