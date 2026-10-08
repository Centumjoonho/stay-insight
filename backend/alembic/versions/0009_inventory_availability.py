"""Owner capacity history, unavailable units, and nullable reservation room units."""
from alembic import op

revision = "0009_inventory_availability"
down_revision = "0008_tourism_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("""
        ALTER TABLE app.reservations ADD COLUMN room_units INTEGER
        CONSTRAINT ck_reservations_room_units CHECK (room_units > 0);
        GRANT UPDATE (room_units) ON app.reservations TO stay_insight_runtime;
        CREATE TABLE app.property_capacity_periods (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES app.organizations(id),
            property_id UUID NOT NULL,
            effective_from DATE NOT NULL, effective_to DATE,
            inventory_units INTEGER NOT NULL CHECK (inventory_units > 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id,property_id)
                REFERENCES app.properties(organization_id,id),
            CHECK (effective_to IS NULL OR effective_to >= effective_from),
            CONSTRAINT capacity_no_overlap EXCLUDE USING gist
                (property_id WITH =, daterange(effective_from,effective_to,'[]') WITH &&)
        );
        CREATE INDEX ix_capacity_scope_date ON app.property_capacity_periods
            (organization_id,property_id,effective_from);
        CREATE TABLE app.property_availability_overrides (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES app.organizations(id),
            property_id UUID NOT NULL, date DATE NOT NULL,
            unavailable_units INTEGER NOT NULL CHECK (unavailable_units >= 0),
            reason VARCHAR(20) NOT NULL CHECK
                (reason IN ('MAINTENANCE','OWNER_BLOCK','SALES_STOP','OTHER')),
            memo VARCHAR(1000),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id,property_id)
                REFERENCES app.properties(organization_id,id),
            UNIQUE (organization_id,property_id,date)
        );
    """)
    for table, columns in (
        ("property_capacity_periods", "effective_from,effective_to,inventory_units,updated_at"),
        ("property_availability_overrides", "unavailable_units,reason,memo,updated_at"),
    ):
        op.execute(f"REVOKE ALL ON app.{table} FROM PUBLIC")
        op.execute(f"GRANT SELECT, INSERT, DELETE ON app.{table} TO stay_insight_runtime")
        op.execute(f"GRANT UPDATE ({columns}) ON app.{table} TO stay_insight_runtime")
        op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
        condition = f"""organization_id =
            nullif(current_setting('app.organization_id',true),'')::uuid
            AND EXISTS (SELECT 1 FROM app.organization_members m
            WHERE m.organization_id = {table}.organization_id
            AND m.user_id = nullif(current_setting('app.user_id',true),'')::uuid)"""
        op.execute(f"""CREATE POLICY tenant_access ON app.{table} FOR ALL
            TO stay_insight_runtime USING ({condition}) WITH CHECK ({condition})""")


def downgrade() -> None:
    op.drop_table("property_availability_overrides", schema="app")
    op.drop_table("property_capacity_periods", schema="app")
    op.drop_column("reservations", "room_units", schema="app")
    # btree_gist may be shared with other schemas; never remove a shared extension.
