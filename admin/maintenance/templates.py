from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def maintenance_page(request):
    return render(request, "maintenance.html")


@login_required
def licenses_page(request):
    return render(request, "licenses.html")


@login_required
def maintenance_alerts_page(request):
    return render(request, "maintenance_alerts.html")
