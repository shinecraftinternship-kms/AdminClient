# admin/scanner_api/migrations/0002_fix_company_fks.py
# --------------------------------------------------------------
# One‑off migration that adds the missing company_id (and a few
# created_by_user_id) columns, creates the FK constraints with
# ON DELETE SET NULL, and makes every existing company_id FK safe.
# --------------------------------------------------------------

from django.db import migrations

SQL = r"""
-- -----------------------------------------------------------
-- 1️⃣  Add missing company_id columns + FK (ON DELETE SET NULL)
-- ------------------------------------------------------------

-- intelligence_alerts
ALTER TABLE public.intelligence_alerts
    ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE public.intelligence_alerts
    ADD CONSTRAINT intelligence_alerts_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL;

-- intelligence_dashboard_analytics
ALTER TABLE public.intelligence_dashboard_analytics
    ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE public.intelligence_dashboard_analytics
    ADD CONSTRAINT intelligence_dashboard_analytics_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL;

-- intelligence_retention_policies
ALTER TABLE public.intelligence_retention_policies
    ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE public.intelligence_retention_policies
    ADD CONSTRAINT intelligence_retention_policies_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL;

-- intelligence_scheduled_reports  (also add created_by_user_id)
ALTER TABLE public.intelligence_scheduled_reports
    ADD COLUMN IF NOT EXISTS company_id BIGINT,
    ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER;
ALTER TABLE public.intelligence_scheduled_reports
    ADD CONSTRAINT intelligence_scheduled_reports_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL,
    ADD CONSTRAINT intelligence_scheduled_reports_created_by_fk
        FOREIGN KEY (created_by_user_id) REFERENCES public.auth_user(id)
        ON DELETE SET NULL;

-- intelligence_reports  (also add generated_by_user_id)
ALTER TABLE public.intelligence_reports
    ADD COLUMN IF NOT EXISTS company_id BIGINT,
    ADD COLUMN IF NOT EXISTS generated_by_user_id INTEGER;
ALTER TABLE public.intelligence_reports
    ADD CONSTRAINT intelligence_reports_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL,
    ADD CONSTRAINT intelligence_reports_generated_by_fk
        FOREIGN KEY (generated_by_user_id) REFERENCES public.auth_user(id)
        ON DELETE SET NULL;

-- intelligence_audit_logs
ALTER TABLE public.intelligence_audit_logs
    ADD COLUMN IF NOT EXISTS company_id BIGINT;
ALTER TABLE public.intelligence_audit_logs
    ADD CONSTRAINT intelligence_audit_logs_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL;

-- intelligence_alert_rules  (also add created_by_user_id)
ALTER TABLE public.intelligence_alert_rules
    ADD COLUMN IF NOT EXISTS company_id BIGINT,
    ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER;
ALTER TABLE public.intelligence_alert_rules
    ADD CONSTRAINT intelligence_alert_rules_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL,
    ADD CONSTRAINT intelligence_alert_rules_created_by_fk
        FOREIGN KEY (created_by_user_id) REFERENCES public.auth_user(id)
        ON DELETE SET NULL;

-- monitoring_agent_versions  (also add released_by_user_id)
ALTER TABLE public.monitoring_agent_versions
    ADD COLUMN IF NOT EXISTS company_id BIGINT,
    ADD COLUMN IF NOT EXISTS released_by_user_id INTEGER;
ALTER TABLE public.monitoring_agent_versions
    ADD CONSTRAINT monitoring_agent_versions_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL,
    ADD CONSTRAINT monitoring_agent_versions_released_by_fk
        FOREIGN KEY (released_by_user_id) REFERENCES public.auth_user(id)
        ON DELETE SET NULL;

-- monitoring_scheduled_scans  (also add created_by_user_id)
ALTER TABLE public.monitoring_scheduled_scans
    ADD COLUMN IF NOT EXISTS company_id BIGINT,
    ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER;
ALTER TABLE public.monitoring_scheduled_scans
    ADD CONSTRAINT monitoring_scheduled_scans_company_id_fk
        FOREIGN KEY (company_id) REFERENCES public.companies(id)
        ON DELETE SET NULL,
    ADD CONSTRAINT monitoring_scheduled_scans_created_by_fk
        FOREIGN KEY (created_by_user_id) REFERENCES public.auth_user(id)
        ON DELETE SET NULL;

-- ------------------------------------------------------------
-- 2️⃣  Make every *existing* company_id FK explicit + safe
-- ------------------------------------------------------------
DO $$
DECLARE
    tbl record;
BEGIN
    FOR tbl IN
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS ref_table,
            ccu.column_name AS ref_column,
            tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
            ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'company_id'
          AND ccu.table_name = 'companies'
    LOOP
        EXECUTE format(
            'ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I;',
            tbl.table_name, tbl.constraint_name
        );
        EXECUTE format(
            'ALTER TABLE %I ADD CONSTRAINT %I_fk_safe
                 FOREIGN KEY (company_id) REFERENCES %I(%I)
                 ON DELETE SET NULL;',
            tbl.table_name,
            tbl.table_name || '_company_id',
            tbl.ref_table,
            tbl.ref_column
        );
    END LOOP;
END $$;

-- ------------------------------------------------------------
-- 3️⃣  Harden a few other important FKs to SET NULL as well
-- ------------------------------------------------------------
ALTER TABLE public.clients
    DROP CONSTRAINT IF EXISTS clients_owner_id_70c42260_fk_auth_user_id,
    ADD CONSTRAINT clients_owner_id_fk
        FOREIGN KEY (owner_id) REFERENCES public.auth_user(id)
        ON DELETE SET NULL;

ALTER TABLE public.clients
    DROP CONSTRAINT IF EXISTS clients_group_id_f6f081c8_fk_client_groups_id,
    ADD CONSTRAINT clients_group_id_fk
        FOREIGN KEY (group_id) REFERENCES public.client_groups(id)
        ON DELETE SET NULL;

ALTER TABLE public.assets
    DROP CONSTRAINT IF EXISTS assets_assigned_to_id_bbc2794b_fk_employees_id,
    ADD CONSTRAINT assets_assigned_to_id_fk
        FOREIGN KEY (assigned_to_id) REFERENCES public.employees(id)
        ON DELETE SET NULL;
-- (add more tables here in the same pattern if you wish)
"""

class Migration(migrations.Migration):

    # This migration depends on the *initial* migration of scanner_api
    # (which creates the base tables). Adjust the name if your first
    # migration has a different number.
    dependencies = [
        ("scanner_api", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]