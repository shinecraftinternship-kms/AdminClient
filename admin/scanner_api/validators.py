import re

WEAK_PASSWORDS = {
    "admin123", "password", "password123", "company2026", "letmein",
    "welcome1", "monkey123", "12345678", "qwerty123", "abc12345",
    "password1", "changeme", "test1234", "admin", "root1234",
}


def validate_strong_password(password):
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        errors.append("Password must contain at least one special character")
    if password.lower() in WEAK_PASSWORDS:
        errors.append("This password is too common. Please choose a stronger one")
    return errors


def validate_email(email):
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def parse_user_agent_string(ua_string):
    browser = "Unknown"
    os_name = "Unknown"
    device_type = "desktop"

    if not ua_string:
        return browser, os_name, device_type

    ua_lower = ua_string.lower()

    if "mobile" in ua_lower or "android" in ua_lower and "tablet" not in ua_lower:
        device_type = "mobile"
    elif "tablet" in ua_lower or "ipad" in ua_lower:
        device_type = "tablet"

    if "edg/" in ua_lower or "edge/" in ua_lower:
        browser = "Edge"
    elif "opr/" in ua_lower or "opera" in ua_lower:
        browser = "Opera"
    elif "chrome" in ua_lower and "safari" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    elif "msie" in ua_lower or "trident" in ua_lower:
        browser = "Internet Explorer"

    if "windows" in ua_lower:
        os_name = "Windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower and "android" not in ua_lower:
        os_name = "Linux"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower or "ios" in ua_lower:
        os_name = "iOS"

    return browser, os_name, device_type
