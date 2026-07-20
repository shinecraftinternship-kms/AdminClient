let adminChart = null;

function loadAdminData() {
    Promise.all([
        fetch('/api/admin/users').then(r => r.json()),
        fetch('/api/admin/stats').then(r => r.json()),
        fetch('/api/settings').then(r => r.json()),
        fetch('/api/activity-log?limit=20').then(r => r.json()),
    ]).then(([users, stats, settings, logs]) => {
        renderUsers(users);
        renderStats(stats);
        renderActivity(logs);
        document.getElementById('adminClientKey').textContent = settings.admin_client_key || 'N/A';
        document.getElementById('autoApproveStatus').textContent = settings.auto_approve ? 'Enabled' : 'Disabled';
        renderChart(stats);
    }).catch(() => {
        showToast('Failed to load admin data', 'danger');
    });
}

function renderUsers(users) {
    const tbody = document.getElementById('adminUsersBody');
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-secondary">No users found</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => `<tr>
        <td>${escapeHtml(u.username)}</td>
        <td class="small">${escapeHtml(u.email || '-')}</td>
        <td>${u.is_superuser ? '<span class="badge bg-success">Yes</span>' : '<span class="badge bg-secondary">No</span>'}</td>
        <td>${u.is_active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-danger">Inactive</span>'}</td>
        <td>
            <button class="btn btn-sm btn-outline-danger" onclick="deleteUser(${u.id}, '${escapeHtml(u.username)}')" ${users.length <= 1 ? 'disabled' : ''}>
                <i class="bi bi-trash"></i>
            </button>
        </td>
    </tr>`).join('');
}

function renderStats(stats) {
    document.getElementById('totalAdmins').textContent = stats.total_admins || 0;
    document.getElementById('totalClients').textContent = stats.total_clients || 0;
    document.getElementById('totalScans').textContent = stats.total_scans || 0;
    document.getElementById('totalLogs').textContent = stats.total_logs || 0;
}

function renderActivity(logs) {
    const tbody = document.getElementById('adminActivityBody');
    if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center text-secondary">No activity</td></tr>';
        return;
    }
    tbody.innerHTML = logs.map(log => `<tr>
        <td class="small text-secondary">${timeAgo(log.created_at)}</td>
        <td><span class="badge bg-secondary">${escapeHtml(log.action)}</span></td>
        <td class="small">${escapeHtml(log.details)}${log.client ? ' - ' + escapeHtml(log.client.hostname || log.client.registration_key || '') : ''}</td>
    </tr>`).join('');
}

function renderChart(stats) {
    const ctx = document.getElementById('adminStatusChart').getContext('2d');
    if (adminChart) adminChart.destroy();

    const data = {
        labels: ['Online', 'Offline', 'Pending'],
        datasets: [{
            data: [
                stats.clients_online || 0,
                stats.clients_offline || 0,
                stats.clients_pending || 0,
            ],
            backgroundColor: ['#198754', '#ffc107', '#0dcaf0'],
            borderWidth: 0,
        }]
    };

    adminChart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#adb5bd', padding: 16 } }
            }
        }
    });
}

function createAdminUser() {
    const username = document.getElementById('newUsername').value.trim();
    const email = document.getElementById('newEmail').value.trim();
    const password = document.getElementById('newPassword').value;
    const isSuperuser = document.getElementById('newIsSuperuser').checked;

    if (!username || !password) {
        showToast('Username and password required', 'warning');
        return;
    }

    fetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password, is_superuser: isSuperuser })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            showToast('Admin user created!', 'success');
            document.getElementById('newUsername').value = '';
            document.getElementById('newEmail').value = '';
            document.getElementById('newPassword').value = '';
            const modal = bootstrap.Modal.getInstance(document.getElementById('createUserModal'));
            modal.hide();
            loadAdminData();
        } else {
            showToast(res.message || 'Failed to create user', 'danger');
        }
    }).catch(() => showToast('Failed to create user', 'danger'));
}

function deleteUser(id, username) {
    if (!confirm(`Delete user "${username}"? This cannot be undone.`)) return;
    fetch(`/api/admin/users/${id}`, { method: 'DELETE' })
        .then(r => r.json()).then(res => {
            if (res.status === 'ok') {
                showToast('User deleted', 'success');
                loadAdminData();
            } else {
                showToast(res.message || 'Failed to delete user', 'danger');
            }
        }).catch(() => showToast('Failed to delete user', 'danger'));
}

function refreshAdminPage() {
    showToast('Refreshing...', 'info');
    loadAdminData();
}

function exportBackup() {
    showToast('Preparing backup...', 'info');
    Promise.all([
        fetch('/api/clients').then(r => r.json()),
        fetch('/api/groups').then(r => r.json()),
        fetch('/api/activity-log?limit=500').then(r => r.json()),
    ]).then(([clients, groups, logs]) => {
        const data = { export_date: new Date().toISOString(), clients, groups, activity_logs: logs };
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = `scanner_backup_${new Date().toISOString().slice(0, 10)}.json`; a.click();
        URL.revokeObjectURL(url);
        showToast('Backup exported!', 'success');
    });
}

loadAdminData();