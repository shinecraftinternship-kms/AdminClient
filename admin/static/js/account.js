let currentProfile = null;

function loadProfile() {
    fetch('/api/auth/me').then(r => r.json()).then(data => {
        if (!data.authenticated) return;
        currentProfile = data;
        const u = data.user;
        const p = data.profile;

        document.getElementById('firstName').value = u.first_name || '';
        document.getElementById('lastName').value = u.last_name || '';
        document.getElementById('profileEmail').value = u.email || '';
        document.getElementById('phone').value = p.phone_number || '';
        document.getElementById('timezone').value = p.timezone || 'UTC';
        document.getElementById('currency').value = p.currency || 'USD';
        document.getElementById('dateFormat').value = p.date_format || 'YYYY-MM-DD';

        document.getElementById('displayEmail').textContent = u.email || 'Not set';
        document.getElementById('displayPhone').textContent = p.phone_number || 'Not set';

        if (u.first_name || u.last_name) {
            document.getElementById('accountName').textContent = (u.first_name + ' ' + u.last_name).trim();
        }

        if (p.profile_picture_url) {
            const display = document.getElementById('avatarDisplay');
            display.innerHTML = '<img src="' + escapeHtml(p.profile_picture_url) + '" alt="Avatar" style="width:5rem;height:5rem;border-radius:50%;object-fit:cover;">';
        }
    });
}

function saveProfile() {
    fetch('/api/auth/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            first_name: document.getElementById('firstName').value.trim(),
            last_name: document.getElementById('lastName').value.trim(),
            email: document.getElementById('profileEmail').value.trim(),
            phone_number: document.getElementById('phone').value.trim(),
            timezone: document.getElementById('timezone').value,
            currency: document.getElementById('currency').value,
            date_format: document.getElementById('dateFormat').value,
        })
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            showToast('Profile updated successfully!', 'success');
            loadProfile();
        } else {
            showToast(res.message || 'Failed to update profile', 'danger');
        }
    }).catch(() => showToast('An error occurred', 'danger'));
}

function triggerAvatarUpload() {
    document.getElementById('avatarInput').click();
}

function uploadAvatar() {
    const input = document.getElementById('avatarInput');
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    if (file.size > 2 * 1024 * 1024) {
        showToast('File too large (max 2MB)', 'warning');
        return;
    }
    const formData = new FormData();
    formData.append('avatar', file);
    fetch('/api/auth/upload-avatar', { method: 'POST', body: formData })
        .then(r => r.json()).then(res => {
            if (res.status === 'ok') {
                showToast('Profile picture updated!', 'success');
                const display = document.getElementById('avatarDisplay');
                display.innerHTML = '<img src="' + escapeHtml(res.profile_picture_url) + '" alt="Avatar" style="width:5rem;height:5rem;border-radius:50%;object-fit:cover;">';
            } else {
                showToast(res.message || 'Upload failed', 'danger');
            }
        }).catch(() => showToast('Upload failed', 'danger'));
}

function changePassword() {
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorDiv = document.getElementById('passwordError');
    const strengthDiv = document.getElementById('passwordStrength');

    errorDiv.classList.add('d-none');

    if (!oldPassword || !newPassword || !confirmPassword) {
        errorDiv.textContent = 'All fields are required';
        errorDiv.classList.remove('d-none');
        return;
    }

    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'New passwords do not match';
        errorDiv.classList.remove('d-none');
        return;
    }

    const userIdEl = document.querySelector('[data-user-id]');
    const userId = userIdEl ? userIdEl.dataset.userId : null;

    fetch('/api/admin/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            old_password: oldPassword,
            new_password: newPassword,
        }),
    }).then(r => r.json()).then(res => {
        if (res.status === 'ok') {
            showToast('Password updated successfully!', 'success');
            document.getElementById('oldPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
            strengthDiv.textContent = '';
        } else {
            errorDiv.textContent = res.message || 'Failed to update password';
            errorDiv.classList.remove('d-none');
        }
    }).catch(() => {
        errorDiv.textContent = 'An error occurred';
        errorDiv.classList.remove('d-none');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const np = document.getElementById('newPassword');
    if (np) {
        np.addEventListener('input', function() {
            const v = this.value;
            const strengthDiv = document.getElementById('passwordStrength');
            if (!v) { strengthDiv.textContent = ''; return; }
            let score = 0;
            if (v.length >= 8) score++;
            if (/[A-Z]/.test(v)) score++;
            if (/[a-z]/.test(v)) score++;
            if (/\d/.test(v)) score++;
            if (/[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]/.test(v)) score++;
            const labels = ['', 'Very Weak', 'Weak', 'Fair', 'Strong', 'Very Strong'];
            const colors = ['', 'danger', 'danger', 'warning', 'success', 'success'];
            strengthDiv.innerHTML = '<span class="text-' + colors[score] + '">Strength: ' + labels[score] + '</span>';
        });
    }
});

function loadLoginHistory() {
    fetch('/api/auth/login-history?limit=30').then(r => r.json()).then(data => {
        const tbody = document.getElementById('loginHistoryBody');
        if (!data.entries || data.entries.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-secondary">No login history</td></tr>';
            return;
        }
        tbody.innerHTML = data.entries.map(h => '<tr>' +
            '<td class="small">' + timeAgo(h.login_time) + '</td>' +
            '<td>' + escapeHtml(h.browser) + '</td>' +
            '<td>' + escapeHtml(h.os) + '</td>' +
            '<td><span class="badge bg-secondary">' + escapeHtml(h.device_type) + '</span></td>' +
            '<td class="small">' + escapeHtml(h.ip_address || '') + '</td>' +
            '<td>' + (h.logout_time ? '<span class="badge bg-secondary">Ended</span>' : '<span class="badge bg-success">Active</span>') + '</td>' +
            '</tr>').join('');
    });
}

function exportLoginHistory() {
    fetch('/api/auth/login-history?limit=500').then(r => r.json()).then(data => {
        if (!data.entries || data.entries.length === 0) {
            showToast('No data to export', 'warning');
            return;
        }
        let csv = 'Time,Browser,OS,Device,IP,Status\n';
        data.entries.forEach(h => {
            csv += '"' + (h.login_time || '') + '","' + (h.browser || '') + '","' + (h.os || '') + '","' + (h.device_type || '') + '","' + (h.ip_address || '') + '","' + (h.logout_time ? 'Ended' : 'Active') + '"\n';
        });
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'login_history_' + new Date().toISOString().slice(0, 10) + '.csv';
        a.click();
        URL.revokeObjectURL(url);
        showToast('Login history exported!', 'success');
    });
}

function loadActiveSessions() {
    fetch('/api/auth/active-sessions').then(r => r.json()).then(sessions => {
        const container = document.getElementById('activeSessions');
        if (!sessions || sessions.length === 0) {
            container.innerHTML = '<div class="text-secondary small">No active sessions</div>';
            return;
        }
        container.innerHTML = sessions.map(s => '<div class="d-flex justify-content-between align-items-center p-2 mb-2 rounded" style="background:rgba(255,255,255,0.05);">' +
            '<div>' +
            '<div class="small"><i class="bi bi-laptop me-1"></i> ' + escapeHtml(s.browser) + ' on ' + escapeHtml(s.os) + '</div>' +
            '<div class="text-secondary" style="font-size:0.75rem;">' + escapeHtml(s.ip_address || 'Unknown IP') + ' &middot; ' + timeAgo(s.login_time) + '</div>' +
            '</div>' +
            '<span class="badge bg-success">Active</span>' +
            '</div>').join('');
    });
}

loadProfile();
loadLoginHistory();
loadActiveSessions();
