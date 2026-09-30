"""Allow tenant-scoped market region edits without broadening other column grants."""

from alembic import op

revision = "0005_property_region_write"
down_revision = "0004_public_accommodation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("GRANT UPDATE (region_id) ON app.properties TO stay_insight_runtime")


def downgrade() -> None:
    op.execute("REVOKE UPDATE (region_id) ON app.properties FROM stay_insight_runtime")
