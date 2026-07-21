import os
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SERVICE_KEY: {'set' if SUPABASE_SERVICE_KEY else 'not set'}")

from supabase import create_client

# Try with anon key first (for auth)
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Try to sign in
try:
    result = client.auth.sign_in_with_password({
        "email": "admin@example.com",
        "password": "admin123"
    })
    print(f"Auth SUCCESS: user={result.user.id}")
except Exception as e:
    print(f"Auth FAILED: {type(e).__name__}: {e}")

# Try querying the DB via REST
try:
    resp = client.table("scanner_api_user").select("*").limit(1).execute()
    print(f"Table query SUCCESS: {resp}")
except Exception as e:
    print(f"Table query FAILED: {type(e).__name__}: {e}")
