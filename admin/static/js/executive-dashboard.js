let execData = {};
let growthChart, lifecycleChart, categoryChart, deptChart, securityChart;

function refreshDashboard() {
    fetch("/api/executive-analytics")
        .then(r => r.json())
        .then(data => { execData = data; renderKPIs(data); renderCharts(data); renderActivities(data); })
        .catch(err => showToast("Dashboard load failed: " + err.message, "danger"));
}

function renderKPIs(d) {
    const a = d.asset_kpis || {};
    setText("kpi-total-assets", a.total_assets);
    setText("kpi-assigned-assets", a.assigned_assets);
    setText("kpi-available-assets", a.available_assets);
    setText("kpi-maintenance-assets", a.maintenance_assets);
    setText("kpi-warranty-expiring", a.warranty_expiring);
    const m = d.monitoring_kpis || {};
    setText("kpi-online-devices", m.online_devices);
    setText("kpi-offline-devices", m.offline_devices);
    setText("kpi-not-reporting", m.not_reporting);
    setText("kpi-critical-devices", m.critical_devices);
    setText("kpi-avg-health", m.avg_health_score ? m.avg_health_score + "%" : "--");
    const mt = d.maintenance_kpis || {};
    setText("kpi-upcoming-mnt", mt.upcoming_maintenance);
    setText("kpi-overdue-mnt", mt.overdue_maintenance);
    const l = d.license_kpis || {};
    setText("kpi-total-licenses", l.total_licenses);
    setText("kpi-expiring-licenses", l.expiring_licenses);
    setText("kpi-license-compliance", l.compliance_score ? l.compliance_score + "%" : "--");
    const s = d.security_kpis || {};
    setText("kpi-open-alerts", s.open_alerts);
    setText("kpi-critical-alerts", s.critical_alerts);
    setText("kpi-security-violations", s.security_violations);
    setText("kpi-audit-today", s.audit_events_today);
    const o = d.organization || {};
    setText("kpi-org-stats", o.total_employees + "E / " + o.total_departments + "D / " + o.total_locations + "L");
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? "--";
}

function renderCharts(d) {
    const c = d.charts || {};
    const s = d.security_kpis || {};
    const growth = c.asset_growth_trend || [];
    if (!growthChart && document.getElementById("growthChart")) {
        growthChart = new Chart(document.getElementById("growthChart"), {
            type: "line",
            data: { labels: growth.map(g => g.month), datasets: [{ label: "Assets", data: growth.map(g => g.count), borderColor: "#4f8cff", backgroundColor: "rgba(79,140,255,0.1)", fill: true, tension: 0.3 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#8888a0", maxTicksLimit: 6 } }, y: { beginAtZero: true, ticks: { color: "#8888a0" } } } }
        });
    } else if (growthChart) { growthChart.data.labels = growth.map(g => g.month); growthChart.data.datasets[0].data = growth.map(g => g.count); growthChart.update(); }

    const lifecycle = c.lifecycle_distribution || {};
    const lcKeys = Object.keys(lifecycle);
    const lcVals = Object.values(lifecycle);
    const lcColors = ["#22c55e", "#4f8cff", "#f97316", "#6b7280", "#ef4444"];
    if (!lifecycleChart && document.getElementById("lifecycleChart")) {
        lifecycleChart = new Chart(document.getElementById("lifecycleChart"), {
            type: "doughnut",
            data: { labels: lcKeys, datasets: [{ data: lcVals, backgroundColor: lcColors.slice(0, lcKeys.length || 1), borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: "#8888a0", padding: 8, font: { size: 10 } } } } }
        });
    } else if (lifecycleChart) { lifecycleChart.data.labels = lcKeys; lifecycleChart.data.datasets[0].data = lcVals; lifecycleChart.update(); }

    const cat = c.asset_by_category || [];
    const catColors = ["#4f8cff","#a78bfa","#f472b6","#34d399","#fbbf24","#f97316","#ef4444","#06b6d4","#84cc16","#8888a0"];
    if (!categoryChart && document.getElementById("categoryChart")) {
        categoryChart = new Chart(document.getElementById("categoryChart"), {
            type: "bar",
            data: { labels: cat.map(x => x.name || "U"), datasets: [{ label: "Count", data: cat.map(x => x.count), backgroundColor: catColors, borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { color: "#8888a0" } }, y: { ticks: { color: "#8888a0", font: { size: 10 } } } } }
        });
    } else if (categoryChart) { categoryChart.data.labels = cat.map(x => x.name || "U"); categoryChart.data.datasets[0].data = cat.map(x => x.count); categoryChart.update(); }

    const dept = c.asset_by_department || [];
    if (!deptChart && document.getElementById("deptChart")) {
        deptChart = new Chart(document.getElementById("deptChart"), {
            type: "bar",
            data: { labels: dept.map(x => x.name || "U"), datasets: [{ label: "Count", data: dept.map(x => x.count), backgroundColor: "#a78bfa", borderRadius: 4 }] },
            options: { responsive: true, maintainAspectRatio: false, indexAxis: "y", plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { color: "#8888a0" } }, y: { ticks: { color: "#8888a0", font: { size: 10 } } } } }
        });
    } else if (deptChart) { deptChart.data.labels = dept.map(x => x.name || "U"); deptChart.data.datasets[0].data = dept.map(x => x.count); deptChart.update(); }

    const st = s.trend || [];
    if (!securityChart && document.getElementById("securityChart")) {
        securityChart = new Chart(document.getElementById("securityChart"), {
            type: "line",
            data: { labels: st.map(x => x.date), datasets: [{ label: "Alerts", data: st.map(x => x.count), borderColor: "#ef4444", backgroundColor: "rgba(239,68,68,0.1)", fill: true, tension: 0.3 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#8888a0", maxTicksLimit: 7 } }, y: { beginAtZero: true, ticks: { color: "#8888a0" } } } }
        });
    } else if (securityChart) { securityChart.data.labels = st.map(x => x.date); securityChart.data.datasets[0].data = st.map(x => x.count); securityChart.update(); }
}

function renderActivities(d) {
    const acts = d.recent_activities || [];
    const list = document.getElementById("recentActivitiesList");
    const count = document.getElementById("activityCount");
    if (count) count.textContent = acts.length;
    if (!list) return;
    if (acts.length === 0) { list.innerHTML = '<div class="list-group-item text-center text-secondary small py-3">No activity</div>'; return; }
    list.innerHTML = acts.slice(0, 15).map(a => {
        const isAlert = a.type === "alert";
        const icon = isAlert ? "bi-bell" : "bi-journal-text";
        const color = isAlert ? (a.severity === "critical" ? "danger" : a.severity === "warning" ? "warning" : "info") : "secondary";
        return `<div class="list-group-item list-group-item-action py-2">
            <div class="d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-${color}"><i class="${icon}"></i></span>
                    <div><div class="small">${escapeHtml(a.text)}</div><small class="text-secondary">${a.username || a.severity || ""} · ${timeAgo(a.time)}</small></div>
                </div>
            </div>
        </div>`;
    }).join("");
}

document.addEventListener("DOMContentLoaded", function() { refreshDashboard(); setInterval(refreshDashboard, 30000); });
