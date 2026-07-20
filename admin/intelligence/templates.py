from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def alerts_page(request):
    return render(request, "intelligence/alerts.html")


@login_required
def intelligence_dashboard_page(request):
    return render(request, "intelligence/dashboard.html")


@login_required
def notifications_page(request):
    return render(request, "intelligence/notifications.html")


@login_required
def reports_page(request):
    return render(request, "intelligence/reports.html")


@login_required
def audit_logs_page(request):
    return render(request, "intelligence/audit_logs.html")


@login_required
def compliance_page(request):
    return render(request, "intelligence/compliance.html")


@login_required
def scheduled_reports_page(request):
    return render(request, "intelligence/scheduled_reports.html")
