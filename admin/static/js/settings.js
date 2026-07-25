let settings = {};
let groups = [];

const _fetchOpts = { credentials: 'same-origin' };

function loadSettings() {
    Promise.all([
        fetch('/api/settings', _fetchOpts).then(r => r.json()),
        fetch('/api/groups', _fetchOpts).then(r => r.json()).catch(() => []),
        fetch('/api/clients', _fetchOpts).then(r => r.json()).catch(() => []),
        fetch('/api/settings/organization', _fetchOpts).then(r => r.json()).catch(() => ({})),
        fetch('/api/settings/security', _fetchOpts).then(r => r.json()).catch(() => ({})),
        fetch('/api/settings/notifications', _fetchOpts).then(r => r.json()).catch(() => ({})),
        fetch('/api/settings/connection', _fetchOpts).then(r => r.json()).catch(() => ({})),
    ]).then(([s, g, clients, org, sec, notif, conn]) => {
        settings = s;
        groups = g;

        document.getElementById('autoApprove').checked = s.auto_approve || false;
        document.getElementById('staleThreshold').value = s.stale_threshold_seconds || 7200;
        document.getElementById('defaultScanInterval').value = s.scan_all_interval || 86400;
        document.getElementById('adminClientKey').textContent = s.admin_client_key || 'N/A';
        document.getElementById('totalScans').textContent = clients.reduce((sum, c) => sum + (c._scan_count || 0), 0) || 'N/A';

        document.getElementById('orgName').value = org.org_name || '';
        document.getElementById('orgLogoUrl').value = org.org_logo_url || '';
        document.getElementById('orgTimezone').value = org.org_timezone || 'UTC';
        document.getElementById('orgCurrency').value = org.org_currency || 'USD';
        document.getElementById('orgDateFormat').value = org.org_date_format || 'YYYY-MM-DD';

        document.getElementById('sessionTimeout').value = sec.session_timeout_minutes || 30;
        document.getElementById('maxLoginAttempts').value = sec.max_login_attempts || 5;
        document.getElementById('lockDuration').value = sec.lock_duration_minutes || 30;
        document.getElementById('passwordExpiry').value = sec.password_expiry_days || 0;

        document.getElementById('notifEmail').checked = notif.notification_email !== false;
        document.getElementById('notifInApp').checked = notif.notification_in_app !== false;
        document.getElementById('notifDailySummary').checked = notif.notification_daily_summary || false;

        if (conn.server_url) {
            document.getElementById('adminServerUrl').textContent = conn.server_url;
            document.getElementById('adminServerUrl').href = conn.server_url;
        } else {
            document.getElementById('adminServerUrl').textContent = 'Not configured';
            document.getElementById('adminServerUrl').removeAttribute('href');
        }
        if (conn.connection_token) {
            document.getElementById('connectionToken').textContent = conn.connection_token;
        } else {
            document.getElementById('connectionToken').textContent = '---';
        }

        renderGroups();
    });
}

function saveOrgSettings() {
    fetch('/api/settings/organization', {
        ..._fetchOpts,
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            org_name: document.getElementById('orgName').value.trim(),
            org_logo_url: document.getElementById('orgLogoUrl').value.trim(),
            org_timezone: document.getElementById('orgTimezone').value,
            org_currency: document.getElementById('orgCurrency').value,
            org_date_format: document.getElementById('orgDateFormat').value,
        })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') showToast('Organization settings saved!', 'success');
    });
}

function saveSecuritySettings() {
    fetch('/api/settings/security', {
        ..._fetchOpts,
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_timeout_minutes: parseInt(document.getElementById('sessionTimeout').value),
            max_login_attempts: parseInt(document.getElementById('maxLoginAttempts').value),
            lock_duration_minutes: parseInt(document.getElementById('lockDuration').value),
            password_expiry_days: parseInt(document.getElementById('passwordExpiry').value),
        })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') showToast('Security settings saved!', 'success');
    });
}

function saveNotificationSettings() {
    fetch('/api/settings/notifications', {
        ..._fetchOpts,
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            notification_email: document.getElementById('notifEmail').checked,
            notification_in_app: document.getElementById('notifInApp').checked,
            notification_daily_summary: document.getElementById('notifDailySummary').checked,
        })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') showToast('Notification settings saved!', 'success');
    });
}

function saveSettings() {
    fetch('/api/settings', {
        ..._fetchOpts,
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            auto_approve: document.getElementById('autoApprove').checked,
            stale_threshold_seconds: parseInt(document.getElementById('staleThreshold').value),
            scan_all_interval: parseInt(document.getElementById('defaultScanInterval').value),
        })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') showToast('Settings saved!', 'success');
    });
}

function scanAdminServer() {
    showToast('Scanning server...', 'info');
    fetch('/api/scan/local', { ..._fetchOpts, method: 'POST' }).then(r => r.json()).then(() => {
        showToast('Server scan started!', 'success');
    });
}

function generateServerUrl() {
    fetch('/api/settings/connection', { ..._fetchOpts, method: 'POST' })
        .then(r => r.json())
        .then(res => {
            if (res.server_url) {
                document.getElementById('adminServerUrl').textContent = res.server_url;
                document.getElementById('adminServerUrl').href = res.server_url;
                document.getElementById('connectionToken').textContent = res.connection_token;
                showToast('Admin server URL generated!', 'success');
            } else {
                showToast('Error: ' + (res.message || 'Failed to generate'), 'danger');
            }
        })
        .catch(err => showToast('Error: ' + err.message, 'danger'));
}

function regenerateToken() {
    if (!confirm('Regenerate the connection token? Clients using the old token will need to reconfigure.')) return;
    fetch('/api/settings/connection', { ..._fetchOpts, method: 'PUT' })
        .then(r => r.json())
        .then(res => {
            if (res.connection_token) {
                document.getElementById('connectionToken').textContent = res.connection_token;
                showToast('Token regenerated!', 'success');
            } else {
                showToast('Error: ' + (res.message || 'Failed to regenerate'), 'danger');
            }
        })
        .catch(err => showToast('Error: ' + err.message, 'danger'));
}

function copyServerUrl() {
    const url = document.getElementById('adminServerUrl').textContent;
    if (!url || url === 'Not configured') {
        showToast('Generate a server URL first', 'warning');
        return;
    }
    navigator.clipboard.writeText(url).then(() => {
        showToast('Server URL copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Copy failed — select and copy manually', 'warning');
    });
}

function copyToken() {
    const token = document.getElementById('connectionToken').textContent;
    if (!token || token === '---') {
        showToast('No token to copy', 'warning');
        return;
    }
    navigator.clipboard.writeText(token).then(() => {
        showToast('Token copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Copy failed — select and copy manually', 'warning');
    });
}

function renderGroups() {
    const container = document.getElementById('groupsList');
    if (groups.length === 0) {
        container.innerHTML = '<div class="text-secondary small">No groups created yet</div>';
        return;
    }
    container.innerHTML = groups.map(g => '<div class="d-flex justify-content-between align-items-center p-2 mb-2 rounded" style="background:rgba(255,255,255,0.05);">' +
        '<div>' +
        '<strong>' + escapeHtml(g.name) + '</strong>' +
        '<span class="text-secondary small ms-2">' + (g.client_count || 0) + ' clients</span>' +
        (g.description ? '<div class="small text-secondary">' + escapeHtml(g.description) + '</div>' : '') +
        '</div>' +
        '<button class="btn btn-sm btn-outline-danger" onclick="deleteGroup(' + g.id + ')"><i class="bi bi-trash"></i></button>' +
        '</div>').join('');
}

function createGroup() {
    const name = document.getElementById('newGroupName').value.trim();
    if (!name) { showToast('Enter a group name', 'warning'); return; }
    fetch('/api/groups', {
        ..._fetchOpts,
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    }).then(r => r.json()).then(() => {
        document.getElementById('newGroupName').value = '';
        showToast('Group created!', 'success');
        loadSettings();
    });
}

function deleteGroup(id) {
    if (!confirm('Delete this group? Clients will be ungrouped.')) return;
    fetch('/api/groups/' + id, { ..._fetchOpts, method: 'DELETE' }).then(r => r.json()).then(() => {
        showToast('Group deleted', 'success');
        loadSettings();
    });
}

function exportBackup() {
    showToast('Preparing backup...', 'info');
    Promise.all([
        fetch('/api/clients', _fetchOpts).then(r => r.json()),
        fetch('/api/groups', _fetchOpts).then(r => r.json()),
        fetch('/api/activity-log?limit=500', _fetchOpts).then(r => r.json()),
    ]).then(([clients, groups, logs]) => {
        const data = { export_date: new Date().toISOString(), clients, groups, activity_logs: logs };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'scanner_backup_' + new Date().toISOString().slice(0, 10) + '.json'; a.click();
        URL.revokeObjectURL(url);
        showToast('Backup exported!', 'success');
    });
}

loadSettings();
