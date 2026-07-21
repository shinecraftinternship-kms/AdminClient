import requests, re

s = requests.Session()
r = s.get("https://admin-client-weld.vercel.app/login/")
m = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', r.text)
token = m.group(1)

headers = {"Referer": "https://admin-client-weld.vercel.app/login/"}
r2 = s.post(
    "https://admin-client-weld.vercel.app/login/",
    data={"csrfmiddlewaretoken": token, "identifier": "admin", "password": "admin123"},
    allow_redirects=True,
    headers=headers,
)
print("POST status:", r2.status_code)
print("Final URL:", r2.url)

# Check for errors
error_ps = re.findall(r'<p[^>]*>(.*?)</p>', r2.text)
for p in error_ps:
    if any(w in p.lower() for w in ["error", "invalid", "incorrect", "wrong", "please", "enter"]):
        print("Error p:", p.strip()[:200])

error_divs = re.findall(r'<div[^>]*alert[^>]*>(.*?)</div>', r2.text, re.DOTALL)
if error_divs:
    print("Alert divs:", [d.strip()[:100] for d in error_divs])

# If we're on a different page now, it might mean login succeeded
if "login" not in r2.url.lower():
    print("LOGIN SUCCEEDED - redirected to:", r2.url)
