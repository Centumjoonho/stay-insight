-- Run with psql ON_ERROR_STOP=1 using the proposed migration/admin connection.
-- Disposable transactional probe only; always ROLLBACK. Never use apply_migration for this.
BEGIN;
CREATE ROLE stay_insight_phase8_probe NOLOGIN NOSUPERUSER NOBYPASSRLS;
GRANT stay_insight_phase8_probe TO CURRENT_USER;
CREATE SCHEMA stay_insight_phase8_probe;
GRANT USAGE ON SCHEMA stay_insight_phase8_probe TO stay_insight_phase8_probe;
CREATE TABLE stay_insight_phase8_probe.records (tenant text);
INSERT INTO stay_insight_phase8_probe.records VALUES ('allowed'), ('other');
ALTER TABLE stay_insight_phase8_probe.records ENABLE ROW LEVEL SECURITY;
ALTER TABLE stay_insight_phase8_probe.records FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_scope ON stay_insight_phase8_probe.records
TO stay_insight_phase8_probe
USING (tenant = current_setting('app.phase8_probe',true))
WITH CHECK (tenant = current_setting('app.phase8_probe',true));
GRANT SELECT, INSERT ON stay_insight_phase8_probe.records TO stay_insight_phase8_probe;
SELECT set_config('app.phase8_probe','allowed',true);
SET LOCAL ROLE stay_insight_phase8_probe;
DO $$ BEGIN
  IF (SELECT count(*) FROM stay_insight_phase8_probe.records) <> 1 THEN
    RAISE EXCEPTION 'Probe RLS failed';
  END IF;
  BEGIN
    INSERT INTO stay_insight_phase8_probe.records VALUES ('other');
    RAISE EXCEPTION 'Probe RLS write isolation failed';
  EXCEPTION WHEN insufficient_privilege THEN
    NULL;
  END;
END $$;
SELECT set_config('app.phase8_probe','',true);
DO $$ BEGIN
  IF (SELECT count(*) FROM stay_insight_phase8_probe.records) <> 0 THEN
    RAISE EXCEPTION 'Probe missing context failed';
  END IF;
END $$;
RESET ROLE;
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis') THEN
    RAISE EXCEPTION 'PostGIS probe failed';
  END IF;
END $$;
ROLLBACK;
-- Session-local values must not survive the transaction.
SELECT nullif(current_setting('app.phase8_probe',true),'') IS NULL AS context_reset;
SELECT 'app schema must be absent before fresh bootstrap' AS requirement,
       to_regnamespace('app') IS NULL AS empty_app_schema;
