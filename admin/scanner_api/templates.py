import os
import hashlib
from django.http import HttpResponseRedirect, FileResponse, Http404
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def executive_dashboard(request):
    return render(request, "executive_dashboard.html")


@login_required
def client_detail(request, key):
    return render(request, "client_detail.html", {"client_key": key})


@login_required
def settings_page(request):
    return render(request, "settings.html")


@login_required
def admin_page(request):
    return render(request, "admin_page.html")


@login_required
def account_view(request):
    return render(request, "account.html")


@login_required
def scan_history(request):
    return render(request, "scan_history.html")


@login_required
def audit_log_view(request):
    return render(request, "audit_log.html")


@login_required
def employees_page(request):
    return render(request, "employees.html")


@login_required
def departments_page(request):
    return render(request, "departments.html")


@login_required
def locations_page(request):
    return render(request, "locations.html")


@login_required
def assets_page(request):
    return render(request, "assets.html")


@login_required
def asset_detail_page(request, key):
    return render(request, "asset_detail.html", {"asset_key": key})


@login_required
def asset_dashboard_page(request):
    return render(request, "asset_dashboard.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    timeout_msg = request.GET.get("timeout") == "1"

    if request.method == "POST":
        identifier = request.POST.get("identifier", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me") == "on"

        if not identifier or not password:
            return render(request, "login.html", {"error": "All fields are required"})

        from .auth_utils import (
            check_account_lock, record_login_attempt, log_audit_event,
            create_login_history, get_client_ip,
        )
        from .validators import validate_email
        from django.contrib.auth.models import User

        locked, minutes_left = check_account_lock(identifier)
        if locked:
            log_audit_event(None, "account_locked", request, details=f"Login attempt on locked account: {identifier}", success=False)
            return render(request, "login.html", {
                "error": f"Account is locked. Try again in {minutes_left} minutes",
                "locked": True, "minutes_left": minutes_left,
            })

        user = None
        if validate_email(identifier):
            try:
                u = User.objects.get(email=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            user = authenticate(request, username=identifier, password=password)

        ip = get_client_ip(request)

        if user is None:
            record_login_attempt(identifier, ip, False)
            log_audit_event(None, "login_failure", request, details=f"Failed login for: {identifier}", success=False)
            remaining = int(__import__("scanner_api.models", fromlist=["Setting"]).Setting.get("max_login_attempts", "5"))
            attempts = __import__("scanner_api.models", fromlist=["LoginAttempt"]).LoginAttempt.objects.filter(
                identifier=identifier, success=False,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=30)
            ).count()
            remaining = max(0, remaining - attempts)
            return render(request, "login.html", {
                "error": "Invalid credentials",
                "attempts_remaining": remaining,
            })

        if not user.is_active:
            return render(request, "login.html", {"error": "Account is disabled"})

        record_login_attempt(identifier, ip, True)
        log_audit_event(user, "login_success", request, details=f"Login successful for {user.username}")
        login_history = create_login_history(user, request)

        login(request, user)

        if remember_me:
            request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            request.session.set_expiry(0)

        request.session["last_activity"] = timezone.now().isoformat()
        request.session["login_history_id"] = login_history.id

        from .models import ActivityLog, AdministratorProfile
        _profile = AdministratorProfile.objects.filter(user=user).select_related("company").first()
        ActivityLog.objects.create(action="login", company=_profile.company if _profile else None, details=f"Admin user {user.username} logged in")

        next_url = request.POST.get("next", "/") or "/"
        return redirect(next_url)

    return render(request, "login.html", {"timeout": timeout_msg})


def logout_view(request):
    from .auth_utils import log_audit_event, close_login_history
    if request.user.is_authenticated:
        log_audit_event(request.user, "logout", request, details="User logged out")
        close_login_history(request.user)
    logout(request)
    return redirect("/login/")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not username or not email or not password:
            return render(request, "signup.html", {"error": "All fields are required"})

        if password != confirm_password:
            return render(request, "signup.html", {"error": "Passwords do not match"})

        from django.contrib.auth.models import User
        from .validators import validate_email
        from .auth_utils import log_audit_event
        from .models import AdministratorProfile, ActivityLog

        if not validate_email(email):
            return render(request, "signup.html", {"error": "Please enter a valid email address"})



        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Username already exists"})

        if User.objects.filter(email=email).exists():
            return render(request, "signup.html", {"error": "Email already registered"})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_superuser = True
        user.save()

        from .models import Company
        company_name = request.POST.get("company_name", "").strip() or username
        company, _ = Company.objects.get_or_create(name=company_name)
        AdministratorProfile.objects.get_or_create(user=user, defaults={"company": company})
        log_audit_event(user, "login_success", request, details=f"Admin account created: {username}", success=True)
        ActivityLog.objects.create(action="login", company=company, details=f"New admin account created: {username}")

        return render(request, "signup.html", {"success": f"Account '{username}' created successfully! You can now sign in."})

    return render(request, "signup.html")


def download_client_view(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")

    exe_path = os.path.join(data_dir, "client_scanner.exe")
    zip_path = os.path.join(data_dir, "client_scanner.zip")

    if os.path.exists(exe_path):
        file_path = exe_path
        filename = "client_scanner.exe"
        content_type = "application/vnd.microsoft.portable-executable"
    elif os.path.exists(zip_path):
        file_path = zip_path
        filename = "client_scanner.zip"
        content_type = "application/zip"
    else:
        raise Http404("Client installer not found on the server. Run build_client.py first.")

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    response = FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )
    response["Content-SHA256"] = file_hash
    response["X-Content-Type-Options"] = "nosniff"
    return response
