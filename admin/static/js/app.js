function showToast(message, type) {
    const container = document.querySelector('.toast-container');
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    container.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3000 });
    bsToast.show();
    toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

function timeAgo(dateStr) {
    if (!dateStr) return 'never';
    const now = new Date();
    const d = new Date(dateStr);
    const seconds = Math.floor((now - d) / 1000);
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
}

function escapeHtml(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function formatBytes(bytes) {
    if (!bytes || isNaN(bytes)) return 'N/A';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let i = 0;
    let val = bytes;
    while (val >= 1024 && i < units.length - 1) { val /= 1024; i++; }
    return val.toFixed(1) + ' ' + units[i];
}

function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-bs-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', next);
    const link = document.getElementById('themeToggle');
    if (link) {
        link.innerHTML = next === 'dark'
            ? '<i class="bi bi-sun-fill me-2"></i><span>Light Mode</span>'
            : '<i class="bi bi-moon-fill me-2"></i><span>Dark Mode</span>';
    }
    localStorage.setItem('theme', next);
}

(function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-bs-theme', saved);
    }
})();
