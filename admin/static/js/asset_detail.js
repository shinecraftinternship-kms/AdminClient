let asset = null;
let assetHistory = [];
let assetAssignments = [];
let assetTransfers = [];

const STATUS_BADGES = {
    'Draft': 'bg-secondary', 'Pending Approval': 'bg-warning text-dark', 'Approved': 'bg-info',
    'Purchased': 'bg-primary', 'Available': 'bg-success', 'Assigned': 'bg-info',
    'Maintenance': 'bg-warning text-dark', 'Returned': 'bg-secondary', 'Lost': 'bg-danger',
    'Damaged': 'bg-danger', 'Retired': 'bg-dark', 'Disposed': 'bg-dark', 'Archived': 'bg-dark',
};

function loadAsset() {
    fetch(`/api/assets/${ASSET_KEY}`).then(r => {
        if (!r.ok) throw new Error('Asset not found');
        return r.json();
    }).then(data => {
        asset = data;
        document.getElementById('assetTitle').textContent = `${data.asset_name} (${data.asset_tag})`;
        document.title = `${data.asset_name} - ITAMS`;
        renderActionButtons();
        renderOverview();
        renderFinancial();
        renderSidebar();
        loadHistory();
        loadAssignments();
        loadTransfers();
        renderChildren();
        loadQRCode();
    }).catch(err => {
        document.getElementById('assetTitle').textContent = 'Asset Not Found';
        showToast('Failed to load asset: ' + err.message, 'danger');
    });
}

function renderActionButtons() {
    const btns = document.getElementById('actionButtons');
    if (!btns || !asset) return;
    let html = '';
    if (['Available', 'Returned'].includes(asset.asset_status)) {
        html += `<button class="btn btn-success btn-sm" onclick="showAssignDialog()"><i class="bi bi-person-plus"></i> Assign</button>`;
    }
    if (asset.asset_status === 'Assigned') {
        html += `<button class="btn btn-warning btn-sm" onclick="showReturnDialog()"><i class="bi bi-arrow-return-left"></i> Return</button>`;
        html += `<button class="btn btn-info btn-sm" onclick="showTransferDialog()"><i class="bi bi-arrow-left-right"></i> Transfer</button>`;
    }
    const transitions = {
        'Draft': ['Pending Approval'], 'Pending Approval': ['Approved'], 'Approved': ['Purchased'],
        'Purchased': ['Available'], 'Available': ['Maintenance', 'Retired', 'Lost', 'Damaged'],
        'Assigned': ['Maintenance', 'Lost', 'Damaged'], 'Maintenance': ['Available', 'Retired', 'Damaged'],
    };
    if (transitions[asset.asset_status]) {
        html += `<div class="dropdown">
            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown">Status</button>
            <ul class="dropdown-menu dropdown-menu-end">
                ${transitions[asset.asset_status].map(s => `<li><a class="dropdown-item" href="#" onclick="changeStatus('${s}')">${s}</a></li>`).join('')}
            </ul>
        </div>`;
    }
    btns.innerHTML = html;
}

function renderOverview() {
    const el = document.getElementById('overviewContent');
    if (!el || !asset) return;
    const imgHtml = asset.image ?
        `<img src="${escapeHtml(asset.image)}" class="rounded mb-3" style="max-width:200px;max-height:150px;object-fit:cover;">` : '';
    el.innerHTML = `${imgHtml}
        <div class="row small">
            <div class="col-md-6 mb-2"><strong>Asset ID:</strong> <code>${escapeHtml(asset.asset_id)}</code></div>
            <div class="col-md-6 mb-2"><strong>Asset Tag:</strong> <code>${escapeHtml(asset.asset_tag)}</code></div>
            <div class="col-md-6 mb-2"><strong>Serial Number:</strong> <code>${escapeHtml(asset.serial_number)}</code></div>
            <div class="col-md-6 mb-2"><strong>Category:</strong> ${escapeHtml(asset.category_name || '-')}</div>
            <div class="col-md-6 mb-2"><strong>Manufacturer:</strong> ${escapeHtml(asset.manufacturer || '-')}</div>
            <div class="col-md-6 mb-2"><strong>Model:</strong> ${escapeHtml(asset.model_name || '-')}</div>
            <div class="col-md-6 mb-2"><strong>Created:</strong> ${new Date(asset.created_at).toLocaleDateString()}</div>
            <div class="col-md-6 mb-2"><strong>Created By:</strong> ${escapeHtml(asset.created_by || '-')}</div>
            ${asset.age_days !== null ? `<div class="col-md-6 mb-2"><strong>Age:</strong> ${asset.age_days} days</div>` : ''}
            ${asset.parent_name ? `<div class="col-md-6 mb-2"><strong>Parent:</strong> ${escapeHtml(asset.parent_name)}</div>` : ''}
        </div>
        ${asset.description ? `<div class="mt-2"><strong>Description:</strong><br><span class="text-secondary">${escapeHtml(asset.description)}</span></div>` : ''}
        ${asset.tags ? `<div class="mt-2"><strong>Tags:</strong> ${asset.tag_list.map(t => `<span class="badge bg-secondary me-1">${escapeHtml(t)}</span>`).join('')}</div>` : ''}
        ${asset.notes ? `<div class="mt-2"><strong>Notes:</strong><br><span class="text-secondary">${escapeHtml(asset.notes)}</span></div>` : ''}`;
}

function renderFinancial() {
    const el = document.getElementById('financialContent');
    if (!el || !asset) return;
    const fmt = v => v ? '$' + Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 }) : '-';
    el.innerHTML = `<div class="row small">
        <div class="col-md-6 mb-3"><strong>Purchase Date:</strong> ${asset.purchase_date || '-'}</div>
        <div class="col-md-6 mb-3"><strong>Purchase Cost:</strong> ${fmt(asset.purchase_cost)}</div>
        <div class="col-md-6 mb-3"><strong>Current Value:</strong> ${fmt(asset.current_value)}</div>
        <div class="col-md-6 mb-3"><strong>Residual Value:</strong> ${fmt(asset.residual_value)}</div>
        <div class="col-md-6 mb-3"><strong>Depreciation:</strong> ${asset.depreciation_pct || 0}%</div>
        <div class="col-md-6 mb-3"><strong>Vendor:</strong> ${escapeHtml(asset.vendor_name || '-')}</div>
        <div class="col-md-6 mb-3"><strong>Invoice #:</strong> ${escapeHtml(asset.invoice_number || '-')}</div>
        <div class="col-md-6 mb-3"><strong>PO #:</strong> ${escapeHtml(asset.purchase_order_number || '-')}</div>
    </div>`;
}

function renderSidebar() {
    if (!asset) return;

    const statusEl = document.getElementById('statusCard');
    if (statusEl) {
        const badge = STATUS_BADGES[asset.asset_status] || 'bg-secondary';
        statusEl.innerHTML = `<div class="text-center">
            <div class="stat-label mb-2">Current Status</div>
            <span class="badge ${badge} fs-6 px-3 py-2">${escapeHtml(asset.asset_status)}</span>
        </div>`;
    }

    const ownerEl = document.getElementById('ownershipCard');
    if (ownerEl) {
        ownerEl.innerHTML = `<h6 class="text-secondary mb-3"><i class="bi bi-building me-1"></i>Ownership</h6>
            <div class="small">
                <div class="mb-1"><strong>Department:</strong> ${escapeHtml(asset.department_name || '-')}</div>
                <div class="mb-1"><strong>Location:</strong> ${escapeHtml(asset.location_name || '-')}</div>
                <div class="mb-1"><strong>Assigned To:</strong> ${escapeHtml(asset.assigned_to_name || 'Unassigned')}</div>
                ${asset.client_hostname ? `<div class="mb-1"><strong>Linked Client:</strong> ${escapeHtml(asset.client_hostname)}</div>` : ''}
            </div>`;
    }

    const warrantyEl = document.getElementById('warrantyCard');
    if (warrantyEl) {
        const wBadge = asset.warranty_status === 'Valid' ? 'bg-success' :
            asset.warranty_status === 'Expiring Soon' ? 'bg-warning text-dark' :
            asset.warranty_status === 'Expired' ? 'bg-danger' : 'bg-secondary';
        warrantyEl.innerHTML = `<h6 class="text-secondary mb-3"><i class="bi bi-shield-check me-1"></i>Warranty</h6>
            <div class="small">
                <div class="mb-1"><strong>Status:</strong> <span class="badge ${wBadge}">${escapeHtml(asset.warranty_status)}</span></div>
                <div class="mb-1"><strong>Start:</strong> ${asset.warranty_start || '-'}</div>
                <div class="mb-1"><strong>End:</strong> ${asset.warranty_end || '-'}</div>
                <div class="mb-1"><strong>Provider:</strong> ${escapeHtml(asset.warranty_provider || '-')}</div>
                ${asset.amc_details ? `<div class="mb-1"><strong>AMC:</strong> ${escapeHtml(asset.amc_details)}</div>` : ''}
            </div>`;
    }
}

function loadQRCode() {
    const el = document.getElementById('qrCard');
    if (!el || !asset) return;
    el.innerHTML = `<h6 class="text-secondary mb-3"><i class="bi bi-qr-code me-1"></i>QR & Barcode</h6>
        <div class="text-center text-secondary"><div class="spinner-border spinner-border-sm"></div></div>`;
    fetch(`/api/assets/${asset.id}/qr`).then(r => r.json()).then(data => {
        el.innerHTML = `<h6 class="text-secondary mb-3"><i class="bi bi-qr-code me-1"></i>QR & Barcode</h6>
            <div class="text-center mb-2">${data.qr_code ? `<img src="${data.qr_code}" style="max-width:150px;" alt="QR Code">` : `<code class="small">${escapeHtml(data.qr_value)}</code>`}</div>
            <div class="text-center mb-2">${data.barcode ? `<img src="${data.barcode}" style="max-width:200px;" alt="Barcode">` : `<code class="small">${escapeHtml(data.barcode_value)}</code>`}</div>
            <div class="text-center"><small class="text-secondary">Scan to view asset details</small></div>`;
    }).catch(() => {
        el.innerHTML = `<h6 class="text-secondary mb-3"><i class="bi bi-qr-code me-1"></i>QR & Barcode</h6>
            <div class="small"><strong>QR:</strong> <code>${escapeHtml(String(asset.qr_code))}</code><br>
            <strong>Barcode:</strong> <code>${escapeHtml(String(asset.barcode))}</code></div>`;
    });
}

function loadHistory() {
    const el = document.getElementById('historyContent');
    if (!el) return;
    el.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm"></div></div>';
    fetch(`/api/assets/${ASSET_KEY}/history?limit=100`).then(r => r.json()).then(data => {
        assetHistory = data.entries || [];
        if (assetHistory.length === 0) {
            el.innerHTML = '<div class="text-secondary text-center py-3">No history records</div>';
            return;
        }
        el.innerHTML = assetHistory.map(h => {
            const date = new Date(h.timestamp).toLocaleString();
            const iconMap = {
                'created': 'bi-plus-circle text-success', 'updated': 'bi-pencil text-info',
                'status_changed': 'bi-arrow-repeat text-warning', 'assigned': 'bi-person-plus text-primary',
                'returned': 'bi-arrow-return-left text-secondary', 'transferred': 'bi-arrow-left-right text-info',
                'maintenance_started': 'bi-tools text-warning', 'maintenance_completed': 'bi-check-circle text-success',
                'retired': 'bi-archive text-secondary', 'disposed': 'bi-trash text-danger',
            };
            const icon = iconMap[h.action] || 'bi-circle text-secondary';
            return `<div class="d-flex mb-3">
                <div class="me-3"><i class="bi ${icon} fs-5"></i></div>
                <div class="flex-grow-1">
                    <div class="fw-semibold">${escapeHtml(h.action.replace(/_/g, ' '))}</div>
                    <div class="small text-secondary">${date} by ${escapeHtml(h.performed_by || 'system')}</div>
                    ${h.notes ? `<div class="small">${escapeHtml(h.notes)}</div>` : ''}
                    ${h.previous_value && Object.keys(h.previous_value).length > 0 ? `<div class="small text-secondary mt-1"><code>From: ${escapeHtml(JSON.stringify(h.previous_value))}</code></div>` : ''}
                    ${h.new_value && Object.keys(h.new_value).length > 0 ? `<div class="small text-secondary"><code>To: ${escapeHtml(JSON.stringify(h.new_value))}</code></div>` : ''}
                </div>
            </div>`;
        }).join('');
    }).catch(() => { el.innerHTML = '<div class="text-danger">Failed to load history</div>'; });
}

function loadAssignments() {
    const el = document.getElementById('assignmentsContent');
    if (!el) return;
    el.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm"></div></div>';
    fetch(`/api/asset-assignments?asset=${ASSET_KEY}`).then(r => r.json()).then(data => {
        assetAssignments = data || [];
        if (assetAssignments.length === 0) {
            el.innerHTML = '<div class="text-secondary text-center py-3">No assignment history</div>';
            return;
        }
        el.innerHTML = `<div class="table-responsive"><table class="table table-dark table-hover table-sm mb-0">
            <thead><tr><th>Employee</th><th>Department</th><th>Assigned</th><th>Returned</th><th>Status</th></tr></thead>
            <tbody>${assetAssignments.map(a => `<tr>
                <td>${escapeHtml(a.employee_name || '-')}</td>
                <td>${escapeHtml(a.department_name || '-')}</td>
                <td class="small">${new Date(a.assigned_at).toLocaleString()}</td>
                <td class="small">${a.returned_at ? new Date(a.returned_at).toLocaleString() : '-'}</td>
                <td><span class="badge ${a.is_active ? 'bg-success' : 'bg-secondary'}">${a.is_active ? 'Active' : 'Returned'}</span></td>
            </tr>`).join('')}</tbody></table></div>`;
    }).catch(() => { el.innerHTML = '<div class="text-danger">Failed to load assignments</div>'; });
}

function loadTransfers() {
    const el = document.getElementById('transfersContent');
    if (!el) return;
    el.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm"></div></div>';
    fetch(`/api/asset-transfers?asset=${ASSET_KEY}`).then(r => r.json()).then(data => {
        assetTransfers = data || [];
        if (assetTransfers.length === 0) {
            el.innerHTML = '<div class="text-secondary text-center py-3">No transfer history</div>';
            return;
        }
        el.innerHTML = `<div class="table-responsive"><table class="table table-dark table-hover table-sm mb-0">
            <thead><tr><th>From</th><th>To</th><th>Date</th><th>Reason</th></tr></thead>
            <tbody>${assetTransfers.map(t => `<tr>
                <td>${escapeHtml(t.from_employee_name || '-')}</td>
                <td>${escapeHtml(t.to_employee_name || '-')}</td>
                <td class="small">${new Date(t.transfer_date).toLocaleString()}</td>
                <td class="small">${escapeHtml(t.reason || '-')}</td>
            </tr>`).join('')}</tbody></table></div>`;
    }).catch(() => { el.innerHTML = '<div class="text-danger">Failed to load transfers</div>'; });
}

function renderChildren() {
    const el = document.getElementById('childrenContent');
    if (!el || !asset) return;
    const children = asset.children || [];
    if (children.length === 0) {
        el.innerHTML = '<div class="text-secondary text-center py-3">No child assets</div>';
        return;
    }
    el.innerHTML = `<div class="table-responsive"><table class="table table-dark table-hover table-sm mb-0">
        <thead><tr><th>Asset Tag</th><th>Name</th><th>Category</th><th>Status</th></tr></thead>
        <tbody>${children.map(c => `<tr>
            <td><code>${escapeHtml(c.asset_tag)}</code></td>
            <td><a href="/assets/${c.id}/" class="text-decoration-none">${escapeHtml(c.asset_name)}</a></td>
            <td>${escapeHtml(c.category_name || '-')}</td>
            <td><span class="badge ${STATUS_BADGES[c.asset_status] || 'bg-secondary'}">${escapeHtml(c.asset_status)}</span></td>
        </tr>`).join('')}</tbody></table></div>`;
}

function changeStatus(newStatus) {
    const notes = prompt(`Change status to "${newStatus}". Add notes (optional):`);
    if (notes === null) return;
    fetch(`/api/assets/${ASSET_KEY}/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, notes: notes })
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message); });
        return r.json();
    }).then(data => {
        showToast(`Status changed to ${newStatus}`, 'success');
        loadAsset();
    }).catch(err => showToast(err.message, 'danger'));
}

function showAssignDialog() {
    showToast('Use the Assign button from the asset list to assign this asset', 'info');
}

function showReturnDialog() {
    fetch(`/api/assets/${ASSET_KEY}/return`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}'
    }).then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.message); });
        return r.json();
    }).then(res => {
        if (res.status === 'ok') { showToast('Asset returned!', 'success'); loadAsset(); }
        else showToast(res.message || 'Failed', 'danger');
    }).catch(err => showToast(err.message, 'danger'));
}

function showTransferDialog() {
    showToast('Use the Transfer button from the asset list to transfer this asset', 'info');
}

document.addEventListener('DOMContentLoaded', loadAsset);
