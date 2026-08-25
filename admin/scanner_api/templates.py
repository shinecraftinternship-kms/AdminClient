import time
import os
import hashlib
from django.http import HttpResponseRedirect, FileResponse, Http404
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.urls import resolve, Resolver404
from django.utils import timezone
from .middleware import build_url_prefix_path


def normalize_next_url(next_url, prefix):
    if not next_url:
        return build_url_prefix_path(prefix, "/")

    candidate = str(next_url).strip()
    if not candidate or candidate in {"/", "#"}:
        return build_url_prefix_path(prefix, "/")

    if candidate.startswith(("http://", "https://", "//")):
        return build_url_prefix_path(prefix, "/")

    if not candidate.startswith("/"):
        candidate = f"/{candidate}"

    if candidate in {"/login/", "/signup/", "/logout/"} or candidate.startswith(("/api/", "/static/", "/download-client/")):
        return build_url_prefix_path(prefix, "/")

    if candidate in {"/settings", "/settings/"}:
        return build_url_prefix_path(prefix, "/setting/")

    if prefix:
        if candidate == f"/{prefix}" or candidate.startswith(f"/{prefix}/"):
            return candidate
        return build_url_prefix_path(prefix, candidate)

    return candidate


def public_root(request):
    """Default landing page.

    - If not authenticated: redirect to login
    - If authenticated: go straight to the dashboard. The personal connect
      page stays reachable at /connect/<user>/<company>/ (linked from
      Admin Server page) but is never forced on navigation.
    """
    if not request.user.is_authenticated:
        return redirect("/login/")
    return redirect("/dashboard/")

    from django.contrib.auth.models import User
    from .models import AdministratorProfile, Company
    from django.utils.text import slugify as _slugify

    user = request.user
    profile = AdministratorProfile.objects.filter(user=user).select_related("company").first()

    if not profile or not profile.company:
        # User doesn't have a company, create one
        _slug = _slugify(user.username) or user.username.lower().replace(" ", "-")
        company, _ = Company.objects.get_or_create(name=user.username, defaults={"slug": _slug})
        if profile:
            profile.company = company
            profile.save(update_fields=["company"])
        else:
            profile, _ = AdministratorProfile.objects.get_or_create(user=user, defaults={"company": company})
    else:
        company = profile.company

    company_slug = company.slug if company else (_slugify(user.username) or user.username.lower().replace(" ", "-"))
    connect_url = f"/connect/{user.username}/{company_slug}/"
    return redirect(connect_url)


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
def admin_server_page(request):
    return render(request, "admin_server.html")


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


def connect_page(request, username, company_slug):
    """Public-facing connect page for a specific admin.

    Displays the admin's connection URL and a download link for the client.
    The URL format is: /connect/<username>/<company>/
    """
    from django.contrib.auth.models import User
    from .models import AdministratorProfile, Company, Setting

    admin_user = None
    company = None
    try:
        company = Company.objects.get(slug=company_slug)
    except Company.DoesNotExist:
        try:
            company = Company.objects.get(name__iexact=company_slug.replace("-", " "))
        except Company.DoesNotExist:
            pass

    if company:
        profile = AdministratorProfile.objects.filter(company=company).select_related("user").first()
        if profile:
            admin_user = profile.user

    if not admin_user:
        try:
            admin_user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            pass

    server_url = Setting.get("admin_server_url", "")
    token = Setting.get("admin_connection_token", "")
    base_url = request.build_absolute_uri("/").rstrip("/")

    context = {
        "admin_username": username,
        "company_name": company.name if company else company_slug,
        "company_slug": company_slug,
        "server_url": server_url,
        "base_url": base_url,
        "token": token[:8] + "..." if token else "",
        "admin_found": admin_user is not None,
    }
    return render(request, "connect.html", context)


@csrf_exempt
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    timeout_msg = request.GET.get("timeout") == "1"
    registered = request.GET.get("registered") == "1"

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
                "registered": registered,
            })

        user = authenticate(request, username=identifier, password=password)
        if user is None and validate_email(identifier):
            try:
                u = User.objects.get(email=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                pass

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
                "registered": registered,
            })

        if not user.is_active:
            return render(request, "login.html", {"error": "Account is disabled", "registered": registered})

        record_login_attempt(identifier, ip, True)
        log_audit_event(user, "login_success", request, details=f"Login successful for {user.username}")
        login_history = create_login_history(user, request)

        login(request, user)

        if remember_me:
            request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            request.session.set_expiry(60 * 60 * 24 * 7)

        request.session["last_activity_ts"] = str(time.time())
        request.session["login_history_id"] = login_history.id

        from django.conf import settings
        from django.core.signing import TimestampSigner
        import json
        signer = TimestampSigner(salt="scanner-auth-cookie")
        payload = signer.sign(json.dumps({"user_id": user.pk, "username": user.username}))

        from .models import ActivityLog, AdministratorProfile, Company
        _profile, _ = AdministratorProfile.objects.get_or_create(user=user)
        if not _profile.company:
            from django.utils.text import slugify as _slugify
            _slug = _slugify(user.username) or user.username.lower().replace(" ", "-")
            company, _ = Company.objects.get_or_create(name=user.username, defaults={"slug": _slug})
            _profile.company = company
            _profile.save(update_fields=["company"])
        ActivityLog.objects.create(action="login", company=_profile.company, details=f"Admin user {user.username} logged in")

        request.session.pop("url_prefix", None)

        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and next_url != "/":
            response = redirect(normalize_next_url(next_url, ""))
        else:
            # Land directly on the dashboard after sign-in. The personal
            # connect URL is available from Admin Server page, never forced.
            response = redirect("/dashboard/")
        response.set_cookie(
            "scanner_auth",
            payload,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="Lax",
            secure=request.is_secure() or getattr(settings, "IS_VERCEL", False),
        )

        return response

    return render(request, "login.html", {"timeout": timeout_msg, "registered": registered})


def logout_view(request):
    from .auth_utils import log_audit_event, close_login_history
    if request.user.is_authenticated:
        log_audit_event(request.user, "logout", request, details="User logged out")
        close_login_history(request.user)
    logout(request)
    response = redirect("/login/")
    response.delete_cookie("scanner_auth")
    return response


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        company_name = request.POST.get("company_name", "").strip()

        if not username or not email or not password or not company_name:
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
        user.is_superuser = False
        user.save()

        from .models import Company
        from django.utils.text import slugify
        import uuid as _uuid
        company_slug = slugify(company_name) or slugify(username)
        try:
            company = Company.objects.get(name=company_name)
        except Company.DoesNotExist:
            if Company.objects.filter(slug=company_slug).exists():
                company_slug = f"{company_slug}-{_uuid.uuid4().hex[:8]}"
            company = Company.objects.create(name=company_name, slug=company_slug)
        if AdministratorProfile.objects.filter(user=user, company=company).exists():
            return render(request, "signup.html", {"error": "This admin is already registered with this company"})
        profile, _ = AdministratorProfile.objects.get_or_create(user=user, defaults={"company": company})
        if profile.company != company:
            profile.company = company
            profile.save(update_fields=["company"])
        log_audit_event(user, "login_success", request, details=f"Admin account created: {username}", success=True)
        ActivityLog.objects.create(action="login", company=company, details=f"New admin account created: {username}")

        return redirect("/login/?registered=1")

    return render(request, "signup.html")


def _detect_client_os(request):
    """Map the browser User-Agent to a client binary: windows/linux/macos."""
    ua = (request.META.get("HTTP_USER_AGENT") or "").lower()
    requested = request.GET.get("os", "").lower()
    if requested in ("windows", "linux", "macos", "mac"):
        return "macos" if requested == "mac" else requested
    if "windows" in ua or "nt 10" in ua or "nt 6" in ua:
        return "windows"
    if "mac os" in ua or "macintosh" in ua or "darwin" in ua:
        return "macos"
    if "linux" in ua or "x11" in ua or "android" in ua:
        return "linux"
    return "windows"


def download_client_view(request):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")

    # Same layout locally and on CI: every platform's binary + zip live in
    # admin/data (or <cwd>/admin/data), produced by build_client.py.
    candidates = [data_dir, os.path.join(os.getcwd(), "admin", "data")]

    def find_file(name):
        for d in candidates:
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p
        return None

    target_os = _detect_client_os(request)
    fmt = request.GET.get("format", "").lower()

    if target_os == "windows":
        primary = (
            ("client_scanner.exe", "client_scanner.exe", "application/vnd.microsoft.portable-executable")
            if fmt != "zip"
            else ("client_scanner.zip", "client_scanner.zip", "application/zip")
        )
        fallbacks = [
            ("client_scanner.zip", "client_scanner.zip", "application/zip"),
            ("client_scanner.exe", "client_scanner.exe", "application/vnd.microsoft.portable-executable"),
        ]
    elif target_os == "macos":
        # .zip containing "System Scanner.app" bundle
        primary = ("client_scanner-macos.zip", "client_scanner-macos.zip", "application/zip")
        fallbacks = [("client_scanner-macos", "client_scanner-macos", "application/octet-stream")]
    else:
        if fmt == "zip":
            primary = ("client_scanner-linux.zip", "client_scanner-linux.zip", "application/zip")
        else:
            # Debian/Ubuntu: install with `sudo dpkg -i` or double-click in
            # Ubuntu Software. Falls back to the zip for other distros.
            primary = (
                "system-scanner_1.7.0_amd64.deb",
                "system-scanner_1.7.0_amd64.deb",
                "application/vnd.debian.binary-package",
            )
        fallbacks = [
            ("system-scanner_1.7.0_amd64.deb", "system-scanner_1.7.0_amd64.deb", "application/vnd.debian.binary-package"),
            ("client_scanner-linux.zip", "client_scanner-linux.zip", "application/zip"),
            ("client_scanner-linux", "client_scanner-linux", "application/octet-stream"),
        ]

    chosen = None
    for name, out_name, ctype in (primary,) + tuple(fallbacks):
        path = find_file(name)
        if path:
            chosen = (path, out_name, ctype)
            break

    if not chosen:
        raise Http404(
            "Client installer not found on the server for this platform. "
            "Run build_client.py (or the Build Client Binaries workflow) first."
        )

    file_path, filename, content_type = chosen

    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    file_hash = sha256.hexdigest()

    file_size = os.path.getsize(file_path)
    size_mb = round(file_size / (1024 * 1024), 1)

    response = FileResponse(
        open(file_path, "rb"),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )
    response["Content-SHA256"] = file_hash
    response["Content-Length"] = str(file_size)
    response["X-Content-Type-Options"] = "nosniff"
    response["X-File-Size-MB"] = str(size_mb)
    return response
