# Vercel Deployment Fix for "Checking..." Issue

## Root Cause
The client shows "Checking..." on Vercel because:
1. **Cloud discovery doesn't work on Vercel** - The `admin/main.py` script (which registers the server in Supabase) never runs on Vercel's serverless platform
2. **`VERCEL_URL` is empty** in your `.env.vercel` (line 30) 
3. **Client falls back to localhost/cached config** - That's why it "works on localhost" but not Vercel

## Solution (Choose One)

### Option 1: Set Environment Variables in Vercel Dashboard (Recommended)
1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add/Update these variables:
   - `VERCEL_URL` = `your-actual-vercel-url.vercel.app` (e.g., `my-project.vercel.app`)
   - `ADMIN_SERVER_URL` = `https://your-actual-vercel-url.vercel.app` (for clients)
3. Redeploy

### Option 2: Run Registration Script After Deployment
After deploying to Vercel, run:
```bash
# Set your actual Vercel URL
export VERCEL_URL="your-project.vercel.app"
export SUPABASE_URL="your-supabase-url"
export SUPABASE_SERVICE_KEY="your-service-key"
python deploy_vercel.py
```

### Option 3: Set `ADMIN_SERVER_URL` on Client Machines
On each client machine, set the environment variable before running the client:
```bash
# Windows (PowerShell)
$env:ADMIN_SERVER_URL = "https://your-project.vercel.app"
python client/main.py

# Windows (CMD)
set ADMIN_SERVER_URL=https://your-project.vercel.app
python client/main.py

# Linux/Mac
export ADMIN_SERVER_URL=https://your-project.vercel.app
python client/main.py
```

## What I Fixed

1. **`api/index.py`** - Now automatically registers the Vercel URL in Supabase on first request (if `VERCEL_URL` is set)
2. **`deploy_vercel.py`** - New script to manually register Vercel URL in Supabase after deployment
3. **Client config** - Already prioritizes `ADMIN_SERVER_URL` env var (no changes needed)

## Verification

After fixing, verify by visiting:
- `https://your-project.vercel.app/__health` - Should show database connection OK
- `https://your-project.vercel.app/__diag` - Should show init log with "[OK] Registered Vercel URL in Supabase"

## Client Behavior After Fix

The client will now:
1. Check `ADMIN_SERVER_URL` env var first (set this on client machines)
2. Fall back to cloud discovery via Supabase (now works because Vercel registers itself)
3. Fall back to cached config / UDP / manual prompt

The "Checking..." status means the client registered but is waiting for admin approval. Check the admin dashboard at `https://your-project.vercel.app` and approve the client.