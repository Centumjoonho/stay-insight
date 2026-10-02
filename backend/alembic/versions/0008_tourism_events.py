"""Shared official events and explicit collection-window audit."""
from alembic import op

revision = "0008_tourism_events"
down_revision = "0007_tourism_visitor_daily"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE app.tourism_events (
        id UUID PRIMARY KEY,
        source VARCHAR(40) NOT NULL CHECK(source='KTO_TOURAPI_EVENTS'),
        source_dataset VARCHAR(100) NOT NULL,
        source_event_id VARCHAR(40) NOT NULL CHECK(source_event_id ~ '^[0-9]+$'),
        region_id UUID NOT NULL REFERENCES app.regions(id),
        source_region_code VARCHAR(2) NOT NULL CHECK(source_region_code='26'),
        source_sigungu_code VARCHAR(3) NOT NULL CHECK(source_sigungu_code IN
          ('110','140','170','200','230','260','290','320','350','380','410','440','470','500','530','710')),
        title VARCHAR(500) NOT NULL CHECK(length(trim(title))>0),
        start_date DATE NOT NULL, end_date DATE NOT NULL CHECK(end_date>=start_date),
        address VARCHAR(1001), source_status VARCHAR(100),
        last_seen_at TIMESTAMPTZ NOT NULL, collected_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(source,source_event_id)
    )""")
    op.execute("CREATE INDEX ix_events_region_start ON app.tourism_events(region_id,start_date)")
    op.execute("ALTER TABLE app.public_data_sync_runs ADD COLUMN event_coverage JSONB")
    op.execute("REVOKE ALL ON app.tourism_events FROM PUBLIC")
    op.execute("GRANT SELECT ON app.tourism_events TO stay_insight_runtime,stay_insight_ingestion")
    op.execute("GRANT INSERT,UPDATE ON app.tourism_events TO stay_insight_ingestion")


def downgrade() -> None:
    op.execute("ALTER TABLE app.public_data_sync_runs DROP COLUMN event_coverage")
    op.execute("DROP TABLE app.tourism_events")

