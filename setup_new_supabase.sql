-- ============================================================
-- System Scanner Pro v3.0 - Full Schema Setup for New Supabase Project
-- Run this in: Supabase Dashboard > SQL Editor
-- Project: zimknnadiqfapzbmfhyj
-- ============================================================

-- 1. server_registry (cloud discovery)
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

-- 2. clients
CREATE TABLE IF NOT EXISTS clients (
  id                 BIGSERIAL PRIMARY KEY,
  registration_key   TEXT UNIQUE NOT NULL,
  hostname           TEXT DEFAULT '',
  platform           TEXT DEFAULT '',
  status             TEXT DEFAULT 'pending',
  last_seen          TIMESTAMPTZ,
  approved           BOOLEAN DEFAULT false,
  auto_approved      BOOLEAN DEFAULT false,
  owner_id           INTEGER,
  company_id         BIGINT,
  group_id           BIGINT,
  tags               TEXT DEFAULT '',
  purchase_cost      NUMERIC(12,2),
  purchase_date      DATE,
  vendor_name        TEXT DEFAULT '',
  vendor_contact     TEXT DEFAULT '',
  warranty_expiry    DATE,
  notes              TEXT DEFAULT '',
  scan_interval      INTEGER DEFAULT 3600,
  scan_enabled       BOOLEAN DEFAULT true,
  scan_requested     BOOLEAN DEFAULT false,
  last_ip            TEXT DEFAULT '',
  device_fingerprint TEXT DEFAULT '',
  deleted            BOOLEAN DEFAULT false,
  client_version     TEXT DEFAULT '',
  os_version         TEXT DEFAULT '',
  cpu_model          TEXT DEFAULT '',
  ram_info           TEXT DEFAULT '',
  created_at         TIMESTAMPTZ DEFAULT now()
);

-- 3. scan_results
CREATE TABLE IF NOT EXISTS scan_results (
  id          BIGSERIAL PRIMARY KEY,
  client_id   BIGINT REFERENCES clients(id) ON DELETE CASCADE,
  scan_type   TEXT DEFAULT 'scheduled',
  scan_data   JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_scan_results_client ON scan_results(client_id, created_at DESC);

-- 4. addon_devices
CREATE TABLE IF NOT EXISTS addon_devices (
  id              BIGSERIAL PRIMARY KEY,
  client_id       BIGINT REFERENCES clients(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  description     TEXT DEFAULT '',
  serial_number   TEXT DEFAULT '',
  purchase_cost   NUMERIC(12,2),
  category        TEXT DEFAULT '',
  added_at        TIMESTAMPTZ DEFAULT now()
);

-- 5. Row Level Security policies
ALTER TABLE server_registry ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access" ON server_registry;
CREATE POLICY "Public read access" ON server_registry FOR SELECT USING (true);
DROP POLICY IF EXISTS "Service role full access" ON server_registry;
CREATE POLICY "Service role full access" ON server_registry FOR ALL
  USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access clients" ON clients;
CREATE POLICY "Service role full access clients" ON clients FOR ALL
  USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE scan_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access scans" ON scan_results;
CREATE POLICY "Service role full access scans" ON scan_results FOR ALL
  USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');

ALTER TABLE addon_devices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Service role full access addons" ON addon_devices;
CREATE POLICY "Service role full access addons" ON addon_devices FOR ALL
  USING (auth.role() = 'service_role') WITH CHECK (auth.role() = 'service_role');
