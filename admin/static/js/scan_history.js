let searchTimer = null;

function debounceSearch() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadScans, 300);
}

function loadScans() {
    const q = document.getElementById('searchInput').value.trim();
    const type = document.getElementById('typeFilter').value;
    const params = new URLSearchParams({ limit: 200 });
    if (q) params.set('q', q);
    if (type) params.set('type', type);

    document.getElementById('scanList').innerHTML = '<div class="text-center py-5 text-secondary"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Loading scans...</div>';

    fetch(`/api/scan/history?${params}`)
        .then(r => r.json())
        .then(scans => {
            document.getElementById('scanCount').textContent = `${scans.length} scan(s) found`;
            renderScans(scans);
        }).catch(() => {
            document.getElementById('scanList').innerHTML = '<div class="text-center py-5 text-danger">Failed to load scans</div>';
        });
}

function renderScans(scans) {
    const container = document.getElementById('scanList');
    if (scans.length === 0) {
        container.innerHTML = '<div class="text-center py-5 text-secondary"><i class="bi bi-inbox fs-1 d-block mb-2"></i>No scans found</div>';
        return;
    }

    container.innerHTML = scans.map(s => {
        const data = s.scan_data || {};
        const os = data.os_info || {};
        const cpu = data.processor || {};
        const ram = data.ram || {};
        const storage = data.storage || {};

        const osLabel = os.name || os.version || 'N/A';
        const cpuLabel = cpu.model || cpu.name || 'N/A';
        const ramLabel = ram.capacity_gb ? `${ram.capacity_gb} GB` : 'N/A';
        const disks = storage.disks || storage.drives || [];
        const diskCount = Array.isArray(disks) ? disks.length : 0;

        return `<div class="card mb-3 scan-card" onclick="showScanDetail(${s.id})" role="button">
            <div class="card-body py-3">
                <div class="row align-items-center g-2">
                    <div class="col-md-2">
                        <strong class="text-primary">${escapeHtml(s.client_hostname || 'Unknown')}</strong>
                        <div class="small text-secondary">${escapeHtml(s.client_key || '')}</div>
                    </div>
                    <div class="col-md-2">
                        <span class="badge bg-${s.scan_type === 'local' ? 'info' : s.scan_type === 'manual' ? 'warning' : 'secondary'} me-1">${s.scan_type}</span>
                        <span class="small text-secondary d-block mt-1">${escapeHtml(s.client_platform || '')}</span>
                    </div>
                    <div class="col-md-2 small">
                        <div><span class="text-secondary">OS:</span> ${escapeHtml(String(osLabel).slice(0, 40))}</div>
                        <div><span class="text-secondary">CPU:</span> ${escapeHtml(String(cpuLabel).slice(0, 30))}</div>
                    </div>
                    <div class="col-md-2 small">
                        <div><span class="text-secondary">RAM:</span> ${ramLabel}</div>
                        <div><span class="text-secondary">Disks:</span> ${diskCount}</div>
                    </div>
                    <div class="col-md-2 small text-secondary">
                        <i class="bi bi-clock me-1"></i>${timeAgo(s.created_at)}
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); showScanDetail(${s.id})">
                            <i class="bi bi-eye"></i> View
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');
}

function showScanDetail(scanId) {
    const modal = new bootstrap.Modal(document.getElementById('scanDetailModal'));
    const body = document.getElementById('scanDetailBody');
    body.innerHTML = '<div class="text-center py-4 text-secondary"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Loading...</div>';
    modal.show();

    fetch('/api/scan/history?limit=500')
        .then(r => r.json())
        .then(scans => {
            const scan = scans.find(s => s.id === scanId);
            if (!scan) {
                body.innerHTML = '<div class="text-center py-4 text-danger">Scan not found</div>';
                return;
            }
            body.innerHTML = renderScanDetail(scan);
        }).catch(() => {
            body.innerHTML = '<div class="text-center py-4 text-danger">Failed to load scan details</div>';
        });
}

function renderScanDetail(scan) {
    const data = scan.scan_data || {};

    const os = data.os_info || {};
    const cpu = data.processor || {};
    const ram = data.ram || {};
    const storage = data.storage || {};
    const motherboard = data.motherboard || {};
    const gpuList = data.gpu || [];
    const network = data.network || {};
    const peripherals = data.peripherals || {};
    const software = data.software || [];
    const accounts = data.accounts || [];
    const updates = data.updates || [];
    const antivirus = data.antivirus || {};

    function section(title, content) {
        return content ? `<div class="mb-3"><h6 class="text-secondary border-bottom pb-1">${title}</h6>${content}</div>` : '';
    }

    function kv(key, val) {
        if (val === undefined || val === null || val === '') return '';
        return `<div class="row mb-1"><div class="col-4 text-secondary small">${key}</div><div class="col-8 small">${escapeHtml(String(val))}</div></div>`;
    }

    function listItems(items, labelKey, valKey) {
        if (!items || items.length === 0) return '<div class="text-secondary small">None</div>';
        return items.map(item => {
            const label = labelKey ? item[labelKey] || item.name || item.displayName || '' : '';
            const val = valKey ? item[valKey] || item.version || item.capacity || '' : '';
            return `<div class="small mb-1">${escapeHtml(String(label))} ${val ? '<span class="text-secondary">' + escapeHtml(String(val)) + '</span>' : ''}</div>`;
        }).join('');
    }

    function table(headers, rows) {
        if (!rows || rows.length === 0) return '<div class="text-secondary small">None</div>';
        return `<div class="table-responsive"><table class="table table-dark table-sm table-hover mb-0">
            <thead><tr>${headers.map(h => `<th class="small">${h}</th>`).join('')}</tr></thead>
            <tbody>${rows.map(row => `<tr>${row.map(c => `<td class="small">${c}</td>`).join('')}</tr>`).join('')}</tbody>
        </table></div>`;
    }

    const diskRows = (storage.disks || storage.drives || []).map(d => [
        escapeHtml(d.model || d.name || ''),
        d.type || '',
        d.size || d.capacity || '',
        d.interface_type || d.interface || '',
        d.filesystem || ''
    ]);

    const gpuRows = gpuList.map(g => [
        escapeHtml(g.name || g.model || ''),
        g.vendor || g.manufacturer || '',
        g.dedicated_memory || g.memory || '',
    ]);

    const netIfs = network.interfaces || network.adapters || [];
    const netRows = netIfs.map(n => [
        escapeHtml(n.name || n.interface_name || ''),
        n.mac || n.mac_address || '',
        n.ipv4 || n.ip_address || '',
        n.status || n.state || ''
    ]);

    const peripheralItems = peripherals.devices || peripherals.peripherals || peripherals;
    const periphRows = Array.isArray(peripheralItems) ? peripheralItems.map(p => [
        escapeHtml(p.name || p.device_name || ''),
        p.type || p.device_type || '',
        p.manufacturer || p.vendor || '',
    ]) : [];

    const softwareItems = Array.isArray(software) ? software : [];
    const swRows = softwareItems.map(s => [
        escapeHtml(s.name || s.displayName || ''),
        s.version || '',
        s.publisher || s.vendor || '',
    ]);

    const accountItems = Array.isArray(accounts) ? accounts : [];
    const updateItems = Array.isArray(updates) ? updates : [];

    const cpuCores = cpu.cores || cpu.core_count || cpu.number_of_cores || '';
    const cpuThreads = cpu.threads || cpu.thread_count || cpu.number_of_logical_processors || '';
    const cpuSpeed = cpu.speed || cpu.max_speed || cpu.speed_ghz || '';

    return `
        <div class="row g-3">
            <div class="col-md-6">
                ${section('Device', `
                    ${kv('Hostname', scan.client_hostname)}
                    ${kv('Key', scan.client_key)}
                    ${kv('Platform', scan.client_platform)}
                    ${kv('Scan Type', scan.scan_type)}
                    ${kv('Scan Time', new Date(scan.created_at).toLocaleString())}
                `)}
                ${section('Operating System', `
                    ${kv('Name', os.name)}
                    ${kv('Version', os.version)}
                    ${kv('Architecture', os.architecture)}
                    ${kv('Install Date', os.install_date)}
                    ${kv('Last Boot', os.last_boot)}
                `)}
                ${section('Processor', `
                    ${kv('Model', cpu.model || cpu.name)}
                    ${kv('Manufacturer', cpu.manufacturer || cpu.vendor)}
                    ${kv('Cores', cpuCores)}
                    ${kv('Threads', cpuThreads)}
                    ${kv('Max Speed', cpuSpeed)}
                    ${kv('L2 Cache', cpu.l2_cache || '')}
                    ${kv('L3 Cache', cpu.l3_cache || '')}
                `)}
                ${section('Motherboard', `
                    ${kv('Manufacturer', motherboard.manufacturer)}
                    ${kv('Model', motherboard.model)}
                    ${kv('Serial', motherboard.serial_number || motherboard.serial)}
                    ${kv('BIOS', motherboard.bios_version || motherboard.bios)}
                `)}
                ${section('RAM', `
                    ${kv('Total Capacity', ram.capacity_gb ? ram.capacity_gb + ' GB' : '')}
                    ${kv('Form Factor', ram.form_factor)}
                    ${kv('Type', ram.type)}
                    ${kv('Speed', ram.speed)}
                    ${kv('Slots Used', ram.slots_used || '')}
                    ${kv('Total Slots', ram.total_slots || '')}
                `)}
            </div>
            <div class="col-md-6">
                ${section('Storage', storage.disks || storage.drives ? table(['Model', 'Type', 'Size', 'Interface', 'FS'], diskRows) : '')}
                ${storage.total_capacity ? section('Total Storage', kv('Total', storage.total_capacity)) : ''}
                ${section('GPU', gpuList.length ? table(['Name', 'Vendor', 'Memory'], gpuRows) : '')}
                ${section('Network', netIfs.length ? table(['Interface', 'MAC', 'IPv4', 'Status'], netRows) : '')}
                ${section('Peripherals', periphRows.length ? table(['Name', 'Type', 'Manufacturer'], periphRows) : '')}
                ${section('Software', swRows.length ? `<div class="table-responsive" style="max-height:300px;overflow-y:auto;">${table(['Name', 'Version', 'Publisher'], swRows)}</div>` : '')}
                ${section('User Accounts', accountItems.length ? listItems(accountItems, 'name', 'type') : '')}
                ${section('Pending Updates', updateItems.length ? listItems(updateItems, 'title', 'severity') : '')}
                ${section('Antivirus', antivirus.name ? kv('Product', `${antivirus.name} ${antivirus.version || ''}`) : '')}
                ${section('Firewall', antivirus.firewall ? kv('Firewall', antivirus.firewall) : '')}
            </div>
        </div>
    `;
}

loadScans();