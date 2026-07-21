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
r3 = s.get("https://admin-client-weld.vercel.app/api/executive-analytics", timeout=30)
print(f"Status: {r3.status_code}")
if r3.status_code == 500:
    print(r3.text[:5000])
