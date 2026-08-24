-- ============================================================
-- System Scanner Pro v3.0 - Setup for New Supabase Project
-- Run this in: Supabase Dashboard > SQL Editor
-- Project: zimknnadiqfapzbmfhyj
--
-- IMPORTANT: This script ONLY creates the server_registry table
-- used by cloud discovery (scanner_api/supabase_client.py).
--
-- Do NOT create clients / scan_results / addon_devices here.
-- Those tables are owned by Django migrations and are created
-- automatically on app startup (api/index.py runs `migrate`).
-- Manually creating them breaks the Vercel deployment:
-- the cold-start migration fails with DuplicateTable and every
-- authenticated API call returns 500 until the DB is repaired.
--
-- To apply the Django schema, just deploy - or run locally:
--   VERCEL=1 python manage.py migrate
-- ============================================================

CREATE TABLE IF NOT EXISTS server_registry (
  id          TEXT PRIMARY KEY DEFAULT 'admin',
  ip_address  TEXT NOT NULL,
  port        INTEGER DEFAULT 80,
  protocol    TEXT DEFAULT 'http',
  server_name TEXT DEFAULT 'System Scanner Pro Admin',
  is_active   BOOLEAN DEFAULT true,
  updated_at  TIMESTAMPTZ DEFAULT now()
);

INSERT INTO server_registry (id, ip_address, port, protocol)
VALUES ('admin', '0.0.0.0', 80, 'http')
ON CONFLICT (id) DO NOTHING;

-- Row Level Security policies
ALTER TABLE server_registry ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access" ON server_registry;
CREATE POLICY "Public read access" ON server_registry FOR SELECT USING (true);
DROP POLICY IF EXISTS "Service role full access" ON server_registry;
CREATE POLICY "Service role full access" ON server_registry FOR ALL
  USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
