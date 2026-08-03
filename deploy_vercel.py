#!/usr/bin/env python3
"""
Vercel deployment script - registers the Vercel URL in Supabase for cloud discovery.
Run this after deploying to Vercel, or add to your CI/CD pipeline.
"""
import os
import sys
import json
import urllib.request
import urllib.error

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

def register_vercel_in_supabase():
    """Register the Vercel deployment URL in Supabase server_registry table."""
    
    # Get Vercel URL from environment (set by Vercel automatically)
    vercel_url = os.getenv("VERCEL_URL", "").strip()
    if not vercel_url:
        print("[ERROR] VERCEL_URL not set. Set it in Vercel dashboard or pass as env var.")
        return False
    
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    
    if not supabase_url or not supabase_key:
        print("[ERROR] SUPABASE_URL or SUPABASE_SERVICE_KEY not set")
        return False
    
    # Vercel uses HTTPS on port 443
    protocol = "https"
    port = 443
    
    # Extract hostname from Vercel URL (remove https:// if present)
    if vercel_url.startswith("https://"):
        hostname = vercel_url[8:]
    elif vercel_url.startswith("http://"):
        hostname = vercel_url[7:]
    else:
        hostname = vercel_url
    
    # Remove any path
    hostname = hostname.split("/")[0]
    
    print(f"[INFO] Registering Vercel URL: {protocol}://{hostname}")
    
    # Prepare the upsert request
    endpoint = f"{supabase_url}/rest/v1/server_registry"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    payload = json.dumps({
        "id": "admin",
        "ip_address": hostname,  # Store hostname instead of IP for Vercel
        "port": port,
        "protocol": protocol,
        "is_active": True,
        "updated_at": "now()",
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[OK] Successfully registered in Supabase: {protocol}://{hostname}")
            return True
    except urllib.error.HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"[ERROR] Registration failed: {e}")
        return False


def verify_registration():
    """Verify the registration worked by querying Supabase."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    
    if not supabase_url or not supabase_key:
        return False
    
    endpoint = f"{supabase_url}/rest/v1/server_registry?id=eq.admin&select=ip_address,port,protocol,is_active"
    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
    }
    
    try:
        req = urllib.request.Request(endpoint, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data:
                row = data[0]
                print(f"[VERIFY] Registered: {row.get('protocol')}://{row.get('ip_address')}:{row.get('port')} (active: {row.get('is_active')})")
                return True
            else:
                print("[VERIFY] No registration found")
                return False
    except Exception as e:
        print(f"[VERIFY] Failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  Vercel Supabase Registration")
    print("=" * 50)
    print()
    
    if register_vercel_in_supabase():
        print()
        verify_registration()
        print()
        print("[SUCCESS] Vercel URL registered for cloud discovery")
        sys.exit(0)
    else:
        print()
        print("[FAILED] Could not register Vercel URL")
        sys.exit(1)