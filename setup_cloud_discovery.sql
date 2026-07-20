-- ============================================================
-- System Scanner Pro v3.0 - Cloud Discovery Setup
-- Run this SQL in the Supabase SQL Editor to create the
-- server_registry table used for dynamic IP discovery.
-- ============================================================

-- 1. Create the server_registry table
CREATE TABLE IF NOT EXISTS server_registry (
  id          TEXT PRIMARY KEY DEFAULT 'admin',
  ip_address  TEXT NOT NULL,
  port        INTEGER DEFAULT 80,
  protocol    TEXT DEFAULT 'http',
  server_name TEXT DEFAULT 'System Scanner Pro Admin',
  is_active   BOOLEAN DEFAULT true,
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- 2. Insert the initial admin row
INSERT INTO server_registry (id, ip_address, port, protocol)
VALUES ('admin', '0.0.0.0', 80, 'http')
ON CONFLICT (id) DO NOTHING;

-- 3. Enable Row Level Security
ALTER TABLE server_registry ENABLE ROW LEVEL SECURITY;

-- 4. Public read policy (anyone can query to find the admin)
DROP POLICY IF EXISTS "Public read access" ON server_registry;
CREATE POLICY "Public read access"
  ON server_registry
  FOR SELECT
  USING (true);

-- 5. Service role write policy (only admin server can update)
DROP POLICY IF EXISTS "Service role full access" ON server_registry;
CREATE POLICY "Service role full access"
  ON server_registry
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- ============================================================
-- Verification: run this to check the table was created
-- SELECT * FROM server_registry;
-- ============================================================
