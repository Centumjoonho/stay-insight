"""Organization, membership and property foundation with restricted-role RLS."""

import sqlalchemy as sa

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA app")
    op.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'stay_insight_runtime') THEN
            CREATE ROLE stay_insight_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS;
        END IF;
    END $$""")
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("length(trim(name)) > 0"),
        schema="app",
    )
    op.create_table(
        "organization_members",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("app.organizations.id"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("organization_id", "user_id"),
        sa.CheckConstraint("role IN ('OWNER', 'MEMBER')"),
        schema="app",
    )
    op.create_index(
        "ix_organization_members_user_id", "organization_members", ["user_id"], schema="app"
    )
    op.create_table(
        "properties",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id", sa.Uuid(), sa.ForeignKey("app.organizations.id"), nullable=False
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(500), nullable=False),
        sa.Column("road_address", sa.String(500)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("accommodation_type", sa.String(40), nullable=False),
        sa.Column("inventory_units", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Seoul"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("organization_id", "id"),
        sa.CheckConstraint("inventory_units >= 1"),
        sa.CheckConstraint("length(trim(name)) > 0 AND length(trim(address)) > 0"),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180"),
        sa.CheckConstraint("(latitude IS NULL) = (longitude IS NULL)"),
        sa.CheckConstraint("timezone = 'Asia/Seoul'"),
        sa.CheckConstraint(
            "accommodation_type IN ('HOTEL','MOTEL','HOSTEL','GUESTHOUSE',"
            "'LIFESTYLE_ACCOMMODATION','PENSION','VACATION_RENTAL','OTHER')"
        ),
        schema="app",
    )
    op.create_index(
        "ix_properties_organization_id", "properties", ["organization_id"], schema="app"
    )
    op.execute("REVOKE ALL ON SCHEMA app FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA app FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA app TO stay_insight_runtime")
    op.execute("GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA app TO stay_insight_runtime")
    op.execute("""GRANT UPDATE (name,address,road_address,latitude,longitude,accommodation_type,
        inventory_units,timezone,updated_at) ON app.properties TO stay_insight_runtime""")
    for table in ("organizations", "organization_members", "properties"):
        op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
    user = "nullif(current_setting('app.user_id', true), '')::uuid"
    org = "nullif(current_setting('app.organization_id', true), '')::uuid"
    new_org = "nullif(current_setting('app.new_organization_id', true), '')::uuid"
    op.execute(f"""CREATE POLICY member_read ON app.organization_members
        FOR SELECT TO stay_insight_runtime USING (user_id = {user})""")
    op.execute(f"""CREATE POLICY organization_read ON app.organizations
        FOR SELECT TO stay_insight_runtime USING (
            (id = {new_org} AND {user} IS NOT NULL)
            OR EXISTS (SELECT 1 FROM app.organization_members m
                       WHERE m.organization_id = organizations.id AND m.user_id = {user}))""")
    op.execute(f"""CREATE POLICY organization_create ON app.organizations
        FOR INSERT TO stay_insight_runtime WITH CHECK (id = {new_org} AND {user} IS NOT NULL)""")
    # Bootstrap is restricted to an organization inserted in this same transaction.
    op.execute(f"""CREATE POLICY member_create ON app.organization_members
        FOR INSERT TO stay_insight_runtime WITH CHECK (
            user_id = {user} AND role = 'OWNER' AND organization_id = {new_org}
            AND EXISTS (SELECT 1 FROM app.organizations o WHERE o.id = organization_id
                        AND o.xmin::text = pg_current_xact_id()::text))""")
    condition = f"""organization_id = {org} AND EXISTS (
        SELECT 1 FROM app.organization_members m
        WHERE m.organization_id = properties.organization_id AND m.user_id = {user})"""
    op.execute(f"""CREATE POLICY property_access ON app.properties
        FOR ALL TO stay_insight_runtime USING ({condition}) WITH CHECK ({condition})""")


def downgrade() -> None:
    op.execute("DROP POLICY organization_read ON app.organizations")
    op.drop_table("properties", schema="app")
    op.drop_table("organization_members", schema="app")
    op.drop_table("organizations", schema="app")
    op.execute("DROP SCHEMA app")
    # Cluster-wide role is retained; it may be used by other databases/logins.
