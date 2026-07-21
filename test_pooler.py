import os, socket, ssl
from dotenv import load_dotenv
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "db.eekerbqgmektmrzjiyyv.supabase.co")
DB_PASS = os.getenv("DB_PASSWORD", "")
PROJECT_REF = DB_HOST.split(".")[1]
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

print(f"Project ref: {PROJECT_REF}")

# Test Supabase REST API with correct URL
print("\n=== Supabase REST API ===")
import requests
correct_api_url = f"https://{PROJECT_REF}.supabase.co"
print(f"Correct API URL: {correct_api_url}")
try:
    r = requests.get(f"{correct_api_url}/rest/v1/", headers={
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
    }, timeout=10)
    print(f"API status: {r.status_code}")
    if r.status_code < 400:
        print(f"API response: {r.text[:300]}")
except Exception as e:
    print(f"API error: {e}")

# Now try pooler with port 5432 (session mode)
POOLER_HOST = "aws-0-us-east-1.pooler.supabase.com"
try:
    infos = socket.getaddrinfo(POOLER_HOST, 5432, socket.AF_INET, socket.SOCK_STREAM)
    pooler_ip = infos[0][4][0]
except:
    pooler_ip = None
    print("Failed to resolve pooler")

if pooler_ip:
    _orig = socket.getaddrinfo
    def _patched(host, port, *a, **kw):
        if host and host.lower() == DB_HOST.lower():
            return _orig(pooler_ip, port, *a, **kw)
        return _orig(host, port, *a, **kw)
    socket.getaddrinfo = _patched

    import pg8000
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for port in [5432, 6543]:
        for user in [f"postgres.{PROJECT_REF}", "postgres"]:
            print(f"\n--- pooler:{port} user={user} ---")
            try:
                conn = pg8000.connect(
                    user=user, password=DB_PASS, host=DB_HOST,
                    port=port, database="postgres",
                    ssl_context=ctx, timeout=10,
                )
                cur = conn.cursor()
                cur.execute("SELECT current_database(), current_user")
                print(f"SUCCESS: {cur.fetchone()}")
                conn.close()
            except Exception as e:
                print(f"FAILED: {e}")

    socket.getaddrinfo = _orig
