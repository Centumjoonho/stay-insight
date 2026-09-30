"""Shared daily visitor observations and dataset-specific coverage audit."""

from alembic import op

revision = "0007_tourism_visitor_daily"
down_revision = "0006_postgis_availability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE app.tourism_visitor_daily (
        id UUID PRIMARY KEY, region_id UUID NOT NULL REFERENCES app.regions(id),
        source VARCHAR(40) NOT NULL CHECK(source='KTO_DATALAB_VISITORS_DAILY'),
        source_dataset VARCHAR(100) NOT NULL,
        source_region_code VARCHAR(5) NOT NULL CHECK(source_region_code IN
          ('26110','26140','26170','26200','26230','26260','26290','26320',
           '26350','26380','26410','26440','26470','26500','26530','26710')),
        source_region_name VARCHAR(40) NOT NULL,
        visitor_category_code VARCHAR(1) NOT NULL CHECK(visitor_category_code IN ('1','2','3')),
        visitor_category_name VARCHAR(40) NOT NULL,
        reference_date DATE NOT NULL,
        visitor_value NUMERIC CHECK(visitor_value >= 0
            AND visitor_value::text NOT IN ('NaN','Infinity','-Infinity')),
        day_of_week_code VARCHAR(1) CHECK(day_of_week_code IN ('1','2','3','4','5','6','7')),
        day_of_week_name VARCHAR(10),
        collected_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(source,source_region_code,visitor_category_code,reference_date)
    )""")
    op.execute(
        "CREATE INDEX ix_visitor_region_category_date "
        "ON app.tourism_visitor_daily(region_id,visitor_category_code,reference_date)"
    )
    op.execute("ALTER TABLE app.public_data_sync_runs ADD COLUMN visitor_coverage JSONB")
    op.execute("REVOKE ALL ON app.tourism_visitor_daily FROM PUBLIC")
    op.execute(
        "GRANT SELECT ON app.tourism_visitor_daily TO stay_insight_runtime, stay_insight_ingestion"
    )
    op.execute("GRANT INSERT, UPDATE ON app.tourism_visitor_daily TO stay_insight_ingestion")


def downgrade() -> None:
    op.execute("ALTER TABLE app.public_data_sync_runs DROP COLUMN visitor_coverage")
    op.execute("DROP TABLE app.tourism_visitor_daily")
