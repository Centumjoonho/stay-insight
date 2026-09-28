"""Shared public license context, explicit admin region assignment; no owner-data rewrite."""

from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa

from alembic import op

revision = "0004_public_accommodation"
down_revision = "0003_expenses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='stay_insight_ingestion') THEN
            CREATE ROLE stay_insight_ingestion NOLOGIN;
        END IF;
    END $$""")
    op.execute("GRANT USAGE ON SCHEMA app TO stay_insight_ingestion")
    op.execute("""CREATE TABLE app.regions (
        id UUID PRIMARY KEY, sido_name VARCHAR(40) NOT NULL,
        sigungu_name VARCHAR(40) NOT NULL, region_level VARCHAR(20) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(sido_name,sigungu_name),
        CHECK(sido_name='부산광역시' AND region_level='SIGUNGU'))""")
    districts = (
        "중구",
        "서구",
        "동구",
        "영도구",
        "부산진구",
        "동래구",
        "남구",
        "북구",
        "해운대구",
        "사하구",
        "금정구",
        "강서구",
        "연제구",
        "수영구",
        "사상구",
        "기장군",
    )
    for name in districts:
        # Deterministic internal UUIDs, explicitly not official geographic codes.
        op.execute(
            sa.text("""INSERT INTO app.regions
            (id,sido_name,sigungu_name,region_level) VALUES
            (:id,'부산광역시',:name,'SIGUNGU')""").bindparams(
                id=uuid5(NAMESPACE_URL, "stay-insight:busan:" + name), name=name
            )
        )
    op.execute("""ALTER TABLE app.properties
        ADD COLUMN region_id UUID REFERENCES app.regions(id),
        ADD COLUMN region_address VARCHAR(500),
        ADD COLUMN region_road_address VARCHAR(500)""")
    op.execute("""CREATE TABLE app.public_accommodation_licenses (
        id UUID PRIMARY KEY, source VARCHAR(40) NOT NULL, source_record_id VARCHAR(200) NOT NULL,
        business_name VARCHAR(300) NOT NULL, source_license_type VARCHAR(200) NOT NULL,
        normalized_license_type VARCHAR(40) NOT NULL, source_business_status VARCHAR(200) NOT NULL,
        normalized_business_status VARCHAR(20) NOT NULL,
        region_id UUID NOT NULL REFERENCES app.regions(id), license_date DATE, closure_date DATE,
        source_updated_at TIMESTAMPTZ, collected_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(source,source_record_id), CHECK(length(trim(source_record_id))>0),
        CHECK(normalized_business_status IN ('OPEN','CLOSED','SUSPENDED','UNKNOWN')),
        CHECK(normalized_license_type IN
            ('GENERAL_ACCOMMODATION','TOURIST_HOTEL','LIFESTYLE_ACCOMMODATION','OTHER'))
    )""")
    op.execute("""CREATE INDEX ix_public_licenses_region_source
        ON app.public_accommodation_licenses(region_id,source)""")
    op.execute("""CREATE TABLE app.public_data_sync_runs (
        id UUID PRIMARY KEY, source VARCHAR(40) NOT NULL, status VARCHAR(20) NOT NULL,
        started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ, collected_at TIMESTAMPTZ,
        source_reference_date DATE, closure_dates_supported BOOLEAN NOT NULL DEFAULT false,
        covered_districts JSONB NOT NULL DEFAULT '[]',
        fetched_count INTEGER NOT NULL DEFAULT 0, inserted_count INTEGER NOT NULL DEFAULT 0,
        updated_count INTEGER NOT NULL DEFAULT 0, unchanged_count INTEGER NOT NULL DEFAULT 0,
        failed_count INTEGER NOT NULL DEFAULT 0, error_summary VARCHAR(100),
        CHECK(status IN ('RUNNING','COMPLETED','FAILED'))
    )""")
    op.execute("""CREATE INDEX ix_public_sync_source_started
        ON app.public_data_sync_runs(source,started_at DESC)""")
    # Shared public context is not tenant-owned. Grants, not fictitious tenant RLS,
    # restrict this data to API reads and a separate command-only writer.
    for table in ("regions", "public_accommodation_licenses", "public_data_sync_runs"):
        op.execute(f"REVOKE ALL ON app.{table} FROM PUBLIC")
        op.execute(f"GRANT SELECT ON app.{table} TO stay_insight_runtime, stay_insight_ingestion")
    for table in ("public_accommodation_licenses", "public_data_sync_runs"):
        op.execute(f"GRANT INSERT, UPDATE ON app.{table} TO stay_insight_ingestion")


def downgrade() -> None:
    op.drop_table("public_data_sync_runs", schema="app")
    op.drop_table("public_accommodation_licenses", schema="app")
    op.execute("""ALTER TABLE app.properties DROP COLUMN region_id,
        DROP COLUMN region_address, DROP COLUMN region_road_address""")
    op.drop_table("regions", schema="app")
