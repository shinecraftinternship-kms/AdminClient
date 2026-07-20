let clientData = null;
let latestScan = null;
let groups = [];
let scanTriggerPoll = null;
let detailRefreshInterval;
let hasLoadedOnce = false;

function loadClient() {
    Promise.all([
        fetch(`/api/clients/${CLIENT_KEY}`).then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        }),
        fetch('/api/groups').then(r => r.json()).catch(() => []),
    ]).then(([data, groupsData]) => {
        clientData = data;
        groups = groupsData;
        latestScan = (data.scans && data.scans.length > 0) ? data.scans[0] : null;
        hasLoadedOnce = true;
        renderClientInfo();
        renderChanges();
        renderSystem();
        renderManual();
        renderAddons();
        renderNetwork();
        renderPeripherals();
        renderSoftware();
        renderScanConfig();
    }).catch(err => {
        if (!hasLoadedOnce) showLoadError(err.message);
        showToast('Failed to load client: ' + err.message, 'danger');
    });
}

function showLoadError(message) {
    const errorHtml = '<div class="col-12 text-center py-5 text-danger">' +
        '<i class="bi bi-exclamation-triangle fs-1 mb-2 d-block"></i>' +
        '<p>Failed to load device data</p>' +
        '<p class="small text-secondary">' + escapeHtml(message) + '</p>' +
        '<button class="btn btn-sm btn-outline-secondary mt-2" onclick="loadClient()">' +
        '<i class="bi bi-arrow-clockwise"></i> Retry</button></div>';

    const perErrorHtml = '<div class="text-center py-5 text-danger">' +
        '<i class="bi bi-exclamation-triangle fs-1 mb-2 d-block"></i>' +
        '<p>Failed to load device data</p>' +
        '<p class="small text-secondary">' + escapeHtml(message) + '</p>' +
        '<button class="btn btn-sm btn-outline-secondary mt-2" onclick="loadClient()">' +
        '<i class="bi bi-arrow-clockwise"></i> Retry</button></div>';

    document.getElementById('systemContent').innerHTML = errorHtml;
    document.getElementById('peripheralsContent').innerHTML = perErrorHtml;
    document.getElementById('networkTableBody').innerHTML = '<tr><td colspan="4" class="text-center text-secondary">Failed to load</td></tr>';
    document.getElementById('softwareTableBody').innerHTML = '<tr><td colspan="3" class="text-center text-secondary">Failed to load</td></tr>';
    document.getElementById('addonsTableBody').innerHTML = '<tr><td colspan="6" class="text-center text-secondary">Failed to load</td></tr>';
}

// ── Data normalizer: supports both old (shared/scanner.py) and new scanner schemas ──
function val(v, fallback) { return (v !== undefined && v !== null && v !== '') ? v : (fallback || '-'); }

function getAssetDetails(sd) {
    return sd && sd['Asset Details'] && sd['Asset Details']['ComputerDetails']
        ? sd['Asset Details']['ComputerDetails'] : null;
}

function getComputerSystem(sd) {
    const ad = getAssetDetails(sd);
    return ad && ad['Computer system'] ? ad['Computer system'] : null;
}

function getProcessor(sd) {
    if (sd && sd.processor && sd.processor.model !== undefined) return sd.processor;
    if (sd && sd.processor && sd.processor.Model !== undefined) {
        const p = sd.processor;
        return {
            manufacturer: p.Manufacturer, model: p.Model, serial: p['Serial Number'],
            cores: p.cores || p.Cores, logical: p.logical_processors || p['Logical Processors'],
            speed_mhz: p.speed_mhz || p['Processor Speed (MHz)'], architecture: p.Architecture
        };
    }
    if (sd && sd.components && sd.components.cpu) {
        const c = sd.components.cpu;
        return {
            manufacturer: c.Manufacturer, model: c.Model, serial: c['Serial Number'],
            cores: c.Cores, logical: c['Logical Processors'],
            speed_mhz: c['Processor Speed (MHz)'], architecture: c.Architecture
        };
    }
    const cs = getComputerSystem(sd);
    if (cs) {
        return {
            manufacturer: cs['cpu manufacturer'], model: cs['CPU model'] || cs['cpu manufacturer'],
            cores: 0, logical: 0, speed_mhz: 0
        };
    }
    return null;
}

function getRAM(sd) {
    if (sd && sd.ram && sd.ram.capacity_gb !== undefined) return sd.ram;
    if (sd && sd['RAM Details']) {
        const r = sd['RAM Details'];
        return {
            manufacturer: r.Manufacturer, capacity_gb: r.capacity_gb,
            serial: r['serial number'], frequency_mhz: r.frequency_mhz, slot: r.port_slot
        };
    }
    const cs = getComputerSystem(sd);
    if (cs && cs.ram) {
        const deets = (cs.ram.details && cs.ram.details.length > 0) ? cs.ram.details[0] : null;
        if (deets) {
            return {
                manufacturer: deets.Manufacturer, capacity_gb: cs.ram.total,
                serial: deets['Serial Number'], frequency_mhz: deets['Frequency MHz'],
                slot: deets['Port / Slot']
            };
        }
        return { capacity_gb: cs.ram.total, available: cs.ram.available };
    }
    return null;
}

function getStorageDisks(sd) {
    if (sd && sd.storage && sd.storage.disks) return sd.storage.disks.map(d => ({ model: d.model, serial: d.serial, size_gb: d.size_gb }));
    if (sd && sd['Hard Disk Details']) return sd['Hard Disk Details'].map(d => ({ model: d.Model, serial: d['Serial Number'], size_gb: d['Size GB'] }));
    return [];
}

function getStoragePartitions(sd) {
    if (sd && sd.storage && sd.storage.partitions) return sd.storage.partitions.map(p => ({ device: p.device, filesystem: p.filesystem, free_gb: p.free_gb, total_gb: p.total_gb }));
    if (sd && sd['Disk Partitions']) return sd['Disk Partitions'].map(p => ({ device: p['Device ID'], filesystem: p['File System'], free_gb: p['Free Space GB'], total_gb: p['Total Size GB'] }));
    return [];
}

function getMotherboard(sd) {
    if (sd && sd.motherboard && sd.motherboard.manufacturer !== undefined) return sd.motherboard;
    if (sd && sd.components && sd.components.motherboard) return sd.components.motherboard;
    const cs = getComputerSystem(sd);
    if (cs) {
        const bios = cs.Bios || {};
        return { manufacturer: cs.manufacturer, product: cs.model, serial: cs.serial_number, bios_vendor: bios.Manufacturer, bios_version: bios.Version };
    }
    return null;
}

function getGPU(sd) {
    if (sd && sd.gpu && sd.gpu.length > 0) {
        if (sd.gpu[0].name !== undefined) return sd.gpu;
    }
    if (sd && sd.components && sd.components.gpu && sd.components.gpu.length > 0) {
        return sd.components.gpu.map(g => ({ name: g.name, driver: g.driver_version, vram_mb: g.vram_mb }));
    }
    return [];
}

function getOSInfo(sd) {
    if (sd && sd.os_info && sd.os_info.version !== undefined) return sd.os_info;
    const ad = getAssetDetails(sd);
    if (ad && ad['Operating System']) {
        const os = ad['Operating System'];
        return {
            version: os['OS Version'], build: os['build number'],
            architecture: os['System type'], hostname: os['registered_to'],
            user_accounts: os['user_accounts'] || []
        };
    }
    return null;
}

function getAntivirus(sd) {
    if (sd && sd.antivirus && sd.antivirus.products) return sd.antivirus.products;
    const ad = getAssetDetails(sd);
    if (ad && ad.Antivirus && ad.Antivirus.products) return ad.Antivirus.products.map(a => ({ name: a.name }));
    return [];
}

function getNetworkInterfaces(sd) {
    if (!sd || !sd.network) return [];
    const n = sd.network;
    if (n.interfaces && n.interfaces.length > 0) {
        if (n.interfaces[0].name !== undefined) return n.interfaces;
        return n.interfaces.map(i => ({
            name: i.nic_name, mac: i.mac_address,
            ipv4: i.ipv4 || [], status: i.connection_status
        }));
    }
    return [];
}

function getPeripherals(sd) {
    if (sd && sd.peripherals && sd.peripherals.keyboard !== undefined) return sd.peripherals;
    if (sd && sd['Peripheral Devices']) return sd['Peripheral Devices'];
    return null;
}

function getSoftware(sd) {
    if (sd && sd.software && sd.software.length > 0 && sd.software[0].name !== undefined) return sd.software;
    if (sd && sd.installed_software_list && sd.installed_software_list.length > 0) return sd.installed_software_list;
    return [];
}

function getAccounts(sd) {
    if (sd && sd.accounts) return sd.accounts;
    if (sd && sd['system accounts']) {
        const sa = sd['system accounts'];
        return (sa['accounts names'] || []).map(a => ({
            name: a['Account Name'], disabled: a['Status'] === 'Disabled', sid: a['SID']
        }));
    }
    return [];
}

function getUpdates(sd) {
    if (sd && sd.updates) return sd.updates;
    if (sd && sd.installed_updates && sd.installed_updates.updates) {
        return sd.installed_updates.updates.map(u => ({ kb: u.kb, description: u.description }));
    }
    return [];
}

function renderClientInfo() {
    const h = document.getElementById('clientHostname');
    h.textContent = clientData.hostname || 'Unknown';
    document.getElementById('clientKey').textContent = clientData.registration_key;
    const badge = document.getElementById('clientStatusBadge');
    if (clientData.deleted) {
        badge.textContent = 'DELETED';
        badge.className = 'badge ms-2 bg-danger';
    } else if (clientData.is_stale) {
        badge.textContent = 'STALE';
        badge.className = 'badge ms-2 bg-danger';
    } else {
        const status = clientData.status || 'offline';
        badge.textContent = status.toUpperCase();
        badge.className = 'badge ms-2 bg-' + (status === 'online' ? 'success' : status === 'pending' ? 'warning' : 'danger');
    }

    const groupEl = document.getElementById('clientGroup');
    if (clientData.group_name) {
        groupEl.textContent = clientData.group_name;
        groupEl.style.display = '';
    } else {
        groupEl.style.display = 'none';
    }

    const ipEl = document.getElementById('clientLastIp');
    if (clientData.last_ip) {
        ipEl.innerHTML = '<i class="bi bi-globe me-1"></i>' + escapeHtml(clientData.last_ip);
        ipEl.style.display = '';
    } else {
        ipEl.style.display = 'none';
    }

    const delBtn = document.getElementById('deleteBtn');
    const scanBtn = document.querySelector('.btn-outline-primary[onclick="triggerScan()"]');
    if (clientData.deleted) {
        delBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> Restore';
        delBtn.className = 'btn btn-outline-success btn-sm';
        if (scanBtn) scanBtn.style.display = 'none';
    } else {
        delBtn.innerHTML = '<i class="bi bi-trash"></i> Delete';
        delBtn.className = 'btn btn-outline-danger btn-sm';
        if (scanBtn) scanBtn.style.display = '';
    }
}

function renderChanges() {
    const container = document.getElementById('changesContainer');
    const list = document.getElementById('changesList');
    const count = document.getElementById('changesCount');
    const changes = clientData?.scan_changes || [];
    if (changes.length === 0) { container.style.display = 'none'; return; }
    container.style.display = '';
    count.textContent = changes.length;
    list.innerHTML = changes.map(c => {
        const isAdd = c.startsWith('+ ');
        const isRemove = c.startsWith('\u2212 ');
        let icon = 'bi-arrow-right-short';
        let color = 'text-secondary';
        if (isAdd) { icon = 'bi-plus-circle text-success'; color = 'text-success'; }
        else if (isRemove) { icon = 'bi-dash-circle text-danger'; color = 'text-danger'; }
        return `<div class="small mb-1 ${color}"><i class="bi ${icon} me-1"></i>${escapeHtml(c)}</div>`;
    }).join('');
}

function renderSystem() {
    const container = document.getElementById('systemContent');
    if (!latestScan) {
        container.innerHTML = '<div class="col-12 text-center py-5 text-secondary">No scan data available. Run a scan from the client or click "Scan Now".</div>';
        return;
    }
    const sd = latestScan.scan_data || {};
    const cs = getComputerSystem(sd);
    const ad = getAssetDetails(sd);

    const proc = getProcessor(sd);
    const ram = getRAM(sd);
    const disks = getStorageDisks(sd);
    const partitions = getStoragePartitions(sd);
    const mb = getMotherboard(sd);
    const gpus = getGPU(sd);
    const osi = getOSInfo(sd);
    const av = getAntivirus(sd);

    let html = '';

    // ── Asset / Computer System card ──
    if (cs) {
        const bios = cs.Bios || {};
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-laptop me-1"></i>Computer System</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Name</td><td>${escapeHtml(cs.Name || '-')}</td></tr>
                <tr><td class="text-secondary">Service Tag</td><td><code>${escapeHtml(cs['service tag'] || '-')}</code></td></tr>
                <tr><td class="text-secondary">Manufacturer</td><td>${escapeHtml(cs.manufacturer || '-')}</td></tr>
                <tr><td class="text-secondary">Model</td><td>${escapeHtml(cs.model || '-')}</td></tr>
                <tr><td class="text-secondary">Serial / Asset Tag</td><td><code>${escapeHtml(cs.serial_number || (cs['asset_tag'] || []).join(', ') || '-')}</code></td></tr>
                <tr><td class="text-secondary">Type</td><td>${escapeHtml(cs.computer_type || '-')}</td></tr>
                <tr><td class="text-secondary">Logged In User</td><td>${escapeHtml(cs.logged_in_user || '-')}</td></tr>
                <tr><td class="text-secondary">BIOS Version</td><td>${escapeHtml(bios.Version || '-')} (${escapeHtml(bios.Manufacturer || '-')})</td></tr>
                <tr><td class="text-secondary">BIOS Date</td><td>${escapeHtml(bios.Date || '-')}</td></tr>
            </table>
        </div></div></div>`;
    }

    // ── Site / Geo card ──
    if (ad) {
        const site = ad['site information'] || {};
        const geo = ad['Geo Location'] || {};
        const ip = ad['IP address'] || {};
        const vendor = ad['vendor and warrenty'] || {};
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-geo-alt me-1"></i>Location & Network</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Site</td><td>${escapeHtml(site['site name'] || '-')}</td></tr>
                <tr><td class="text-secondary">City / Country</td><td>${escapeHtml(geo.city || '-')}${geo.country ? ', ' + escapeHtml(geo.country) : ''}</td></tr>
                <tr><td class="text-secondary">Public IPv4</td><td><code>${escapeHtml(ip.public_ip?.ipv4 || '-')}</code></td></tr>
                <tr><td class="text-secondary">Primary Private IP</td><td><code>${escapeHtml(ip.private_ip?.primary_ip || '-')}</code></td></tr>
                <tr><td class="text-secondary">DNS Servers</td><td>${escapeHtml(ip['DNS Servers'] || '-')}</td></tr>
                <tr><td class="text-secondary">ISP</td><td>${escapeHtml(geo['ISP provider'] || '-')}</td></tr>
            </table>
        </div></div></div>`;
    }

    // ── Processor ──
    if (proc) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-cpu me-1"></i>Processor</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Model</td><td>${escapeHtml(proc.model || '-')}</td></tr>
                <tr><td class="text-secondary">Manufacturer</td><td>${escapeHtml(proc.manufacturer || '-')}</td></tr>
                <tr><td class="text-secondary">Serial</td><td><code>${escapeHtml(proc.serial || '-')}</code></td></tr>
                <tr><td class="text-secondary">Cores</td><td>${proc.cores || 0} physical / ${proc.logical || 0} logical</td></tr>
                <tr><td class="text-secondary">Speed</td><td>${proc.speed_mhz || 0} MHz</td></tr>
                <tr><td class="text-secondary">Architecture</td><td>${escapeHtml(proc.architecture || '-')}</td></tr>
            </table>
        </div></div></div>`;
    }

    // ── Memory ──
    if (ram) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-memory me-1"></i>Memory</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Capacity</td><td>${escapeHtml(ram.capacity_gb || '-')}</td></tr>
                <tr><td class="text-secondary">Manufacturer</td><td>${escapeHtml(ram.manufacturer || '-')}</td></tr>
                <tr><td class="text-secondary">Serial</td><td><code>${escapeHtml(ram.serial || '-')}</code></td></tr>
                <tr><td class="text-secondary">Frequency</td><td>${ram.frequency_mhz || 0} MHz</td></tr>
                <tr><td class="text-secondary">Slot</td><td>${escapeHtml(ram.slot || '-')}</td></tr>
                ${ram.available ? `<tr><td class="text-secondary">Available</td><td>${escapeHtml(ram.available)}</td></tr>` : ''}
                ${ram.percent_used ? `<tr><td class="text-secondary">Used</td><td>${escapeHtml(ram['percent_used'] || ram.percent_used)}</td></tr>` : ''}
            </table>
        </div></div></div>`;
    }

    // ── Storage ──
    if (disks.length > 0 || partitions.length > 0) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-device-hdd me-1"></i>Storage</h6>
            ${disks.map(d => `<div class="mb-2 p-2" style="background:rgba(255,255,255,0.03);border-radius:6px;">
                <div class="small">${escapeHtml(d.model || 'Unknown')}</div>
                <div class="small text-secondary">SN: ${escapeHtml(d.serial || '-')} | ${d.size_gb || 0} GB</div>
            </div>`).join('') || '<div class="text-secondary">No disks</div>'}
            ${partitions.map(p => `<div class="small text-secondary">${p.device} (${p.filesystem}): ${p.free_gb || 0} / ${p.total_gb || 0} GB free</div>`).join('') || ''}
        </div></div></div>`;
    }

    // ── Motherboard ──
    if (mb) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-motherboard me-1"></i>Motherboard</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Manufacturer</td><td>${escapeHtml(mb.manufacturer || '-')}</td></tr>
                <tr><td class="text-secondary">Product</td><td>${escapeHtml(mb.product || '-')}</td></tr>
                <tr><td class="text-secondary">Serial</td><td><code>${escapeHtml(mb.serial || '-')}</code></td></tr>
                ${mb.version ? `<tr><td class="text-secondary">Version</td><td>${escapeHtml(mb.version)}</td></tr>` : ''}
                <tr><td class="text-secondary">BIOS</td><td>${escapeHtml(mb.bios_vendor || '-')} ${escapeHtml(mb.bios_version || '')}</td></tr>
            </table>
        </div></div></div>`;
    }

    // ── Graphics ──
    if (gpus.length > 0) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-display me-1"></i>Graphics</h6>
            ${gpus.map(g => `<div class="mb-2 p-2" style="background:rgba(255,255,255,0.03);border-radius:6px;">
                <div>${escapeHtml(g.name || 'Unknown')}</div>
                <div class="small text-secondary">VRAM: ${g.vram_mb || 0} MB | Driver: ${escapeHtml(g.driver || '-')}</div>
            </div>`).join('')}
        </div></div></div>`;
    }

    // ── Monitor ──
    const mon = sd && sd['Montitor Details'];
    if (mon && (mon.name || mon.model)) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-display me-1"></i>Monitor</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Name</td><td>${escapeHtml(mon.name || '-')}</td></tr>
                <tr><td class="text-secondary">Manufacturer</td><td>${escapeHtml(mon.manufacturer || '-')}</td></tr>
                <tr><td class="text-secondary">Model</td><td>${escapeHtml(mon.model || '-')}</td></tr>
                <tr><td class="text-secondary">Serial Number</td><td><code>${escapeHtml(mon.serial_number || '-')}</code></td></tr>
            </table>
        </div></div></div>`;
    }

    // ── Vendor & Warranty ──
    if (ad) {
        const vw = ad['vendor and warrenty'] || {};
        if (vw['vendor name']) {
            html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
                <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-tag me-1"></i>Vendor & Warranty</h6>
                <table class="table table-sm table-borderless">
                    <tr><td class="text-secondary">Vendor</td><td>${escapeHtml(vw['vendor name'] || '-')}</td></tr>
                    ${vw['purchase_cost'] !== null && vw['purchase_cost'] !== undefined ? `<tr><td class="text-secondary">Cost</td><td>$${vw['purchase_cost']}</td></tr>` : ''}
                    ${vw['purchase_date'] ? `<tr><td class="text-secondary">Purchase Date</td><td>${escapeHtml(vw['purchase_date'])}</td></tr>` : ''}
                    ${vw['warranty_expiry_date'] ? `<tr><td class="text-secondary">Warranty Expiry</td><td>${escapeHtml(vw['warranty_expiry_date'])}</td></tr>` : ''}
                    ${vw['asset_created_date'] ? `<tr><td class="text-secondary">Asset Created</td><td>${escapeHtml(vw['asset_created_date'])}</td></tr>` : ''}
                </table>
            </div></div></div>`;
        }
    }

    // ── Operating System ──
    if (osi) {
        html += `<div class="col-md-6 mb-3"><div class="card h-100"><div class="card-body">
            <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-windows me-1"></i>Operating System</h6>
            <table class="table table-sm table-borderless">
                <tr><td class="text-secondary">Version</td><td>${escapeHtml(osi.version || '-')}</td></tr>
                <tr><td class="text-secondary">Build</td><td>${escapeHtml(osi.build || '-')}</td></tr>
                <tr><td class="text-secondary">Architecture</td><td>${escapeHtml(osi.architecture || '-')}</td></tr>
                <tr><td class="text-secondary">Hostname</td><td>${escapeHtml(osi.hostname || '-')}</td></tr>
            </table>
        </div></div></div>`;
    }

    // ── Info bar (always show) ──
    html += `<div class="col-12 mb-3"><div class="card"><div class="card-body">
        <h6 class="card-subtitle mb-2 text-secondary"><i class="bi bi-shield me-1"></i>Info</h6>
        <div class="row">
            <div class="col-md-3"><strong>Antivirus:</strong> ${av.map(a => escapeHtml(a.name)).join(', ') || 'None'}</div>
            <div class="col-md-2"><strong>Type:</strong> ${latestScan.scan_type || 'N/A'}</div>
            <div class="col-md-2"><strong>Source:</strong> ${sd.scanned_by === 'client_agent' ? '<span class="badge bg-success mt-1">Client</span>' : '<span class="badge bg-warning text-dark mt-1">Admin Local</span>'}</div>
            <div class="col-md-2"><strong>Last Scan:</strong> ${timeAgo(latestScan.created_at)}</div>
            <div class="col-md-3 d-flex align-items-center"><button class="btn btn-sm btn-outline-info w-100" onclick="triggerScan()"><i class="bi bi-play-fill"></i> Scan Now</button></div>
        </div>
    </div></div></div>`;

    container.innerHTML = html;
}

function renderManual() {
    if (!clientData) return;
    document.getElementById('manualHostname').value = clientData.hostname || '';
    document.getElementById('manualCost').value = clientData.purchase_cost || '';
    document.getElementById('manualPurchaseDate').value = clientData.purchase_date || '';
    document.getElementById('manualWarranty').value = clientData.warranty_expiry || '';
    document.getElementById('manualVendor').value = clientData.vendor_name || '';
    document.getElementById('manualVendorContact').value = clientData.vendor_contact || '';
    document.getElementById('manualNotes').value = clientData.notes || '';
    document.getElementById('manualTags').value = clientData.tags || '';

    const sel = document.getElementById('manualGroup');
    sel.innerHTML = '<option value="">No Group</option>' + groups.map(g => `<option value="${g.id}" ${clientData.group === g.id ? 'selected' : ''}>${escapeHtml(g.name)}</option>`).join('');
}

function saveManual() {
    const data = {
        hostname: document.getElementById('manualHostname').value || null,
        purchase_cost: document.getElementById('manualCost').value ? parseFloat(document.getElementById('manualCost').value) : null,
        purchase_date: document.getElementById('manualPurchaseDate').value || null,
        warranty_expiry: document.getElementById('manualWarranty').value || null,
        vendor_name: document.getElementById('manualVendor').value || null,
        vendor_contact: document.getElementById('manualVendorContact').value || null,
        notes: document.getElementById('manualNotes').value || null,
        group: document.getElementById('manualGroup').value || null,
        tags: document.getElementById('manualTags').value || '',
    };
    fetch(`/api/clients/${CLIENT_KEY}/manual`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') { showToast('Saved!', 'success'); loadClient(); }
        else { showToast('Error: ' + (res.message || 'Unknown'), 'danger'); }
    });
}

function renderAddons() {
    const tbody = document.getElementById('addonsTableBody');
    const addons = clientData?.addons || [];
    if (addons.length === 0) { tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary">No add-on devices</td></tr>'; return; }
    tbody.innerHTML = addons.map(a => `<tr>
        <td>${escapeHtml(a.name)}</td>
        <td>${escapeHtml(a.description || '')}</td>
        <td><code>${escapeHtml(a.serial_number || '')}</code></td>
        <td>${a.purchase_cost ? '$' + parseFloat(a.purchase_cost).toFixed(2) : '-'}</td>
        <td>${escapeHtml(a.category || '')}</td>
        <td><button class="btn btn-sm btn-outline-danger" onclick="deleteAddon(${a.id})"><i class="bi bi-trash"></i></button></td>
    </tr>`).join('');
}

function showAddAddonModal() {
    ['addonName', 'addonDesc', 'addonSerial', 'addonCost'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('addonCategory').value = '';
    new bootstrap.Modal(document.getElementById('addAddonModal')).show();
}

function saveAddon() {
    const name = document.getElementById('addonName').value.trim();
    if (!name) { showToast('Device name is required', 'warning'); return; }
    const data = {
        name, description: document.getElementById('addonDesc').value.trim(),
        serial_number: document.getElementById('addonSerial').value.trim(),
        purchase_cost: document.getElementById('addonCost').value ? parseFloat(document.getElementById('addonCost').value) : null,
        category: document.getElementById('addonCategory').value,
    };
    fetch(`/api/clients/${CLIENT_KEY}/addons`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            showToast('Device added!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('addAddonModal')).hide();
            loadClient();
        }
    });
}

function deleteAddon(addonId) {
    if (!confirm('Delete this device?')) return;
    fetch(`/api/clients/${CLIENT_KEY}/addons/${addonId}`, { method: 'DELETE' }).then(r => r.json()).then(res => {
        if (res.status === 'ok') { showToast('Deleted', 'success'); loadClient(); }
    });
}

function renderNetwork() {
    const tbody = document.getElementById('networkTableBody');
    const ifaces = getNetworkInterfaces(latestScan?.scan_data);
    if (ifaces.length === 0) { tbody.innerHTML = '<tr><td colspan="4" class="text-center text-secondary">No network data</td></tr>'; return; }
    tbody.innerHTML = ifaces.map(i => `<tr>
        <td>${escapeHtml(i.name || '')}</td>
        <td><code>${escapeHtml(i.mac || '')}</code></td>
        <td>${(i.ipv4 || []).join(', ') || '-'}</td>
        <td><span class="badge bg-${((i.ipv4 || []).length > 0 && (i.status || '').toLowerCase() !== 'down') ? 'success' : 'secondary'}">${(i.status && i.status.toLowerCase() !== 'down') ? 'Active' : 'Inactive'}</span></td>
    </tr>`).join('');
}

function renderPeripherals() {
    const container = document.getElementById('peripheralsContent');
    const per = getPeripherals(latestScan?.scan_data);
    if (!per) {
        container.innerHTML = '<div class="text-center py-5 text-secondary">No peripherals detected</div>';
        return;
    }

    const categories = [
        {key: 'keyboard', icon: 'bi-keyboard', label: 'Keyboards'},
        {key: 'mouse', icon: 'bi-mouse', label: 'Mice'},
        {key: 'printers', icon: 'bi-printer', label: 'Printers'},
        {key: 'storage', icon: 'bi-device-hdd', label: 'USB Storage'},
        {key: 'audio', icon: 'bi-speaker', label: 'Audio Devices'},
        {key: 'webcam', icon: 'bi-camera', label: 'Webcams'},
        {key: 'other_usb', icon: 'bi-plug', label: 'Other USB Devices'},
        {key: 'headset', icon: 'bi-headphones', label: 'Headsets'},
    ];

    let hasDevices = false;
    let html = '';
    for (const cat of categories) {
        let devices = per[cat.key] || [];
        if (devices.length === 0) continue;
        hasDevices = true;
        html += `<div class="mb-4"><h6 class="text-secondary mb-2"><i class="bi ${cat.icon} me-1"></i>${cat.label} (${devices.length})</h6>
            <div class="table-responsive"><table class="table table-dark table-hover table-sm"><thead><tr>
                <th>Name</th><th>Manufacturer</th><th>Description / Model</th>
                ${cat.key === 'storage' ? '<th>Serial</th><th>Size</th>' : ''}
                <th>Status</th><th>Connection</th>
            </tr></thead><tbody>
            ${devices.map(d => {
                const name = d.Name || d.name || '';
                const mfr = d.Manufacturer || d.manufacturer || '-';
                const desc = d.Model || d.description || d.Description || '-';
                const serial = d['Serial Number'] || d.serial_number || d.serial || '';
                let detailRow = '';
                if (cat.key === 'storage') detailRow = `<td><code>${escapeHtml(serial)}</code></td><td>${d.size_gb ? d.size_gb + ' GB' : '-'}</td>`;
                const status = d.Status || d.status || 'Unknown';
                const isUsb = d.USB || d.usb || false;
                return `<tr><td>${escapeHtml(name)}</td><td>${escapeHtml(mfr)}</td><td>${escapeHtml(desc)}</td>${detailRow}<td><span class="badge ${status === 'OK' || status === 'connected' || status === 'Up' || status === 'Enabled' ? 'bg-success' : 'bg-secondary'}">${escapeHtml(status)}</span></td><td>${isUsb ? '<span class="badge bg-info">USB</span>' : '<span class="badge bg-secondary">Internal</span>'}</td></tr>`;
            }).join('')}
            </tbody></table></div></div>`;
    }
    container.innerHTML = hasDevices ? html : '<div class="text-center py-5 text-secondary">No peripherals detected</div>';
}

function renderSoftware() {
    const software = getSoftware(latestScan?.scan_data);
    if (software.length === 0) {
        document.getElementById('softwareTableBody').innerHTML = '<tr><td colspan="3" class="text-center text-secondary">No software data</td></tr>';
        document.getElementById('softwareCount').textContent = '';
        return;
    }
    window._softwareData = software;
    document.getElementById('softwareCount').textContent = `Showing ${software.length} applications`;
    filterSoftware();
}

function filterSoftware() {
    const query = (document.getElementById('softwareSearch').value || '').toLowerCase();
    const filtered = (window._softwareData || []).filter(s =>
        (s.name || '').toLowerCase().includes(query) || (s.publisher || '').toLowerCase().includes(query)
    );
    document.getElementById('softwareTableBody').innerHTML = filtered.map(s => `<tr>
        <td>${escapeHtml(s.name)}</td><td>${escapeHtml(s.version || '')}</td><td>${escapeHtml(s.publisher || '')}</td>
    </tr>`).join('');
    document.getElementById('softwareCount').textContent = `Showing ${filtered.length} of ${window._softwareData.length} applications`;
}

function renderScanConfig() {
    fetch(`/api/clients/${CLIENT_KEY}/scan-config`).then(r => r.json()).then(config => {
        document.getElementById('scanInterval').value = config.interval_seconds || 3600;
        document.getElementById('scanEnabled').checked = config.enabled !== false;
    }).catch(() => {});
}

function saveScanConfig() {
    fetch(`/api/clients/${CLIENT_KEY}/scan-config`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_seconds: parseInt(document.getElementById('scanInterval').value), enabled: document.getElementById('scanEnabled').checked })
    }).then(r => r.json()).then(res => { if (res.status === 'ok') showToast('Scan config saved!', 'success'); });
}

function triggerScan() {
    showToast('Scan requested — waiting for client...', 'info');
    fetch(`/api/clients/${CLIENT_KEY}/scan-now`, { method: 'POST' })
        .then(r => r.json())
        .then(res => {
            if (res.status === 'ok') {
                const oldId = latestScan?.id || null;
                let attempts = 0;
                if (scanTriggerPoll) clearInterval(scanTriggerPoll);
                scanTriggerPoll = setInterval(() => {
                    attempts++;
                    if (attempts > 40) { clearInterval(scanTriggerPoll); scanTriggerPoll = null; loadClient(); showToast('Timed out. Check if the client agent is running.', 'warning'); return; }
                    fetch(`/api/clients/${CLIENT_KEY}`).then(r => r.json()).then(data => {
                        const newScan = (data.scans && data.scans.length > 0) ? data.scans[0] : null;
                        if (newScan && newScan.id !== oldId) {
                            clearInterval(scanTriggerPoll); scanTriggerPoll = null;
                            clientData = data; latestScan = newScan;
                            renderClientInfo(); renderChanges(); renderSystem(); renderNetwork(); renderPeripherals(); renderSoftware();
                            showToast('New scan data received from client!', 'success');
                        }
                    }).catch(() => {});
                }, 3000);
            } else { showToast('Error: ' + (res.message || 'Unknown'), 'danger'); }
        })
        .catch(err => showToast('Error: ' + err.message, 'danger'));
}

function deleteClient() {
    if (clientData.deleted) {
        if (!confirm('Restore this client?')) return;
        fetch(`/api/clients/${CLIENT_KEY}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deleted: false, status: 'offline' })
        }).then(r => r.json()).then(res => {
            if (res.status === 'ok') { showToast('Client restored', 'success'); location.reload(); }
            else { showToast('Restore failed: ' + (res.message || 'Unknown error'), 'danger'); }
        }).catch(err => showToast('Restore failed: ' + err.message, 'danger'));
        return;
    }
    if (!confirm('Delete this client? It will be hidden and counted as offline.')) return;
    fetch(`/api/clients/${CLIENT_KEY}`, { method: 'DELETE' }).then(r => r.json()).then(res => {
        if (res.status === 'ok') { showToast('Client deleted', 'success'); window.location.href = '/'; }
        else { showToast('Delete failed: ' + (res.message || 'Unknown error'), 'danger'); }
    }).catch(err => showToast('Delete failed: ' + err.message, 'danger'));
}

function startDetailRefresh() {
    if (detailRefreshInterval) clearInterval(detailRefreshInterval);
    detailRefreshInterval = setInterval(loadClient, 10000);
}

loadClient();
startDetailRefresh();
