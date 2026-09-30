"""Ensure hosted PostGIS exists; retain shared extension on downgrade."""
from alembic import op

revision = "0006_postgis_availability"
down_revision = "0005_property_region_write"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS extensions")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions")


def downgrade() -> None:
    # Provider/local PostGIS may predate this migration and serve other applications.
    # Retain both extension and schema. No business tables or roles change.
    pass
