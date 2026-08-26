let allSoftware = [];
let sortField = 'name';
let sortDir = 1;

function loadSoftware() {
    document.getElementById('softwareTableBody').innerHTML = '<tr><td colspan="5" class="text-center text-secondary py-4"><div class="spinner-border spinner-border-sm me-2" role="status"></div>Loading software inventory...</td></tr>';

    fetch('/api/software/inventory')
        .then(r => r.json())
        .then(data => {
            const raw = data.software || [];
            const seen = new Set();
            allSoftware = raw.map(s => {
                const entry = {
                    name: s.name || '',
                    version: s.version || '',
                    publisher: s.publisher || '',
                    source: s.source || 'registry',
                    installed_on: s.installed_on || [],
                };
                const key = (entry.name + '|' + entry.version + '|' + entry.source).toLowerCase();
                if (seen.has(key)) return null;
                seen.add(key);
                return entry;
            }).filter(Boolean);
            updateStats(data);
            populateFilters();
            filterSoftware();
        })
        .catch(err => {
            document.getElementById('softwareTableBody').innerHTML = '<tr><td colspan="5" class="text-center text-danger py-4">Failed to load software inventory</td></tr>';
        });
}

function updateStats(data) {
    document.getElementById('totalApps').textContent = data.total || 0;
    const desktop = (data.sources || {});
    const desktopCount = (desktop.registry || 0) + (desktop.macos || 0) + (desktop['macos-apps'] || 0);
    const pkgCount = (desktop.winget || 0) + (desktop.npm || 0) + (desktop.pip || 0) + (desktop.snap || 0) + (desktop.flatpak || 0) + (desktop.brew || 0) + (desktop.mas || 0) + (desktop.dpkg || 0) + (desktop.msstore || 0);
    document.getElementById('desktopApps').textContent = desktopCount;
    document.getElementById('pkgApps').textContent = pkgCount;
    document.getElementById('totalSources').textContent = Object.keys(desktop).length;
}

function populateFilters() {
    const sources = [...new Set(allSoftware.map(s => s.source).filter(Boolean))].sort();
    const sourceFilter = document.getElementById('sourceFilter');
    sourceFilter.innerHTML = '<option value="">All Sources</option>' + sources.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(sourceLabel(s))}</option>`).join('');

    const clients = [...new Set(allSoftware.flatMap(s => s.installed_on || []))].sort();
    const clientFilter = document.getElementById('clientFilter');
    clientFilter.innerHTML = '<option value="">All Clients</option>' + clients.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}

function sourceLabel(src) {
    const labels = { registry: 'Registry', msstore: 'MS Store', winget: 'Winget', npm: 'npm', pip: 'pip', snap: 'Snap', flatpak: 'Flatpak', brew: 'Homebrew', mas: 'Mac App Store', 'macos-apps': 'macOS Apps', dpkg: 'dpkg' };
    return labels[src] || src;
}

function sourceBadgeClass(src) {
    const classes = { registry: 'bg-primary', msstore: 'bg-info', winget: 'bg-success', npm: 'bg-danger', pip: 'bg-warning text-dark', snap: 'bg-purple', flatpak: 'bg-dark', brew: 'bg-warning text-dark', mas: 'bg-info', 'macos-apps': 'bg-secondary', dpkg: 'bg-danger' };
    return classes[src] || 'bg-secondary';
}

function toggleSort(field) {
    if (sortField === field) {
        sortDir *= -1;
    } else {
        sortField = field;
        sortDir = 1;
    }
    filterSoftware();
}

function filterSoftware() {
    const query = (document.getElementById('softwareSearch').value || '').toLowerCase();
    const sourceVal = document.getElementById('sourceFilter').value;
    const clientVal = document.getElementById('clientFilter').value;

    let filtered = allSoftware.filter(s => {
        const matchesQuery = !query ||
            (s.name || '').toLowerCase().includes(query) ||
            (s.publisher || '').toLowerCase().includes(query) ||
            (s.version || '').toLowerCase().includes(query);
        const matchesSource = !sourceVal || (s.source || '') === sourceVal;
        const matchesClient = !clientVal || (s.installed_on || []).includes(clientVal);
        return matchesQuery && matchesSource && matchesClient;
    });

    filtered.sort((a, b) => {
        const va = (a[sortField] || '').toLowerCase();
        const vb = (b[sortField] || '').toLowerCase();
        if (va < vb) return -1 * sortDir;
        if (va > vb) return 1 * sortDir;
        return 0;
    });

    const tbody = document.getElementById('softwareTableBody');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary py-4">No software found</td></tr>';
    } else {
        tbody.innerHTML = filtered.map(s => `<tr>
            <td><strong>${escapeHtml(s.name)}</strong></td>
            <td>${escapeHtml(s.version || '-')}</td>
            <td>${escapeHtml(s.publisher || '-')}</td>
            <td><span class="badge ${sourceBadgeClass(s.source || '')}">${escapeHtml(sourceLabel(s.source || ''))}</span></td>
            <td><span class="text-secondary small">${escapeHtml((s.installed_on || []).join(', '))}</span></td>
        </tr>`).join('');
    }
    document.getElementById('softwareCount').textContent = `Showing ${filtered.length} of ${allSoftware.length} applications`;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function exportSoftwareCSV() {
    if (allSoftware.length === 0) {
        alert('No software data to export');
        return;
    }
    const headers = ['Name', 'Version', 'Publisher', 'Source', 'Installed On'];
    const rows = allSoftware.map(s => [
        s.name, s.version, s.publisher, s.source, (s.installed_on || []).join('; ')
    ]);
    const csvContent = [headers, ...rows].map(r => r.map(c => `"${String(c || '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `software_inventory_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
}

loadSoftware();
