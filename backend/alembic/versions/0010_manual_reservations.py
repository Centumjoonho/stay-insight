"""Manual reservations, field protections and append-only change history."""

from alembic import op

revision = "0010_manual_reservations"
down_revision = "0009_inventory_availability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All prior reservation writers require import_id; never synthesize historical audits.
    op.execute("""
        ALTER TABLE app.reservations
          ADD COLUMN origin VARCHAR(20) NOT NULL DEFAULT 'CSV_IMPORT',
          ADD COLUMN version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
          ALTER COLUMN import_id DROP NOT NULL,
          ALTER COLUMN external_reservation_id DROP NOT NULL,
          ADD CONSTRAINT reservation_origin CHECK (origin IN ('CSV_IMPORT','MANUAL')),
          ADD CONSTRAINT reservation_origin_lineage CHECK
            ((origin='CSV_IMPORT' AND import_id IS NOT NULL AND external_reservation_id IS NOT NULL)
             OR (origin='MANUAL' AND import_id IS NULL)),
          ADD CONSTRAINT reservation_scope_identity UNIQUE (organization_id,property_id,id);
        GRANT UPDATE (version) ON app.reservations TO stay_insight_runtime;
        ALTER TABLE app.reservation_imports ADD COLUMN protected_fields_count INTEGER
            NOT NULL DEFAULT 0 CHECK (protected_fields_count >= 0);
        GRANT UPDATE (protected_fields_count) ON app.reservation_imports TO stay_insight_runtime;
        CREATE TABLE app.reservation_manual_overrides (
            id UUID PRIMARY KEY, organization_id UUID NOT NULL, property_id UUID NOT NULL,
            reservation_id UUID NOT NULL,
            field_name VARCHAR(30) NOT NULL CHECK (field_name IN
              ('check_in','check_out','gross_revenue','channel_fee','guest_count',
               'reservation_status','room_units')),
            created_by_subject UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (reservation_id,field_name),
            FOREIGN KEY (organization_id,property_id,reservation_id)
              REFERENCES app.reservations(organization_id,property_id,id)
        );
        CREATE TABLE app.reservation_audit_events (
            id UUID PRIMARY KEY, organization_id UUID NOT NULL, property_id UUID NOT NULL,
            reservation_id UUID NOT NULL,
            event_type VARCHAR(30) NOT NULL CHECK (event_type IN
              ('MANUAL_CREATE','MANUAL_UPDATE','STATUS_CHANGE','MANUAL_OVERRIDE_RELEASED','CSV_UPDATE')),
            change_source VARCHAR(20) NOT NULL CHECK (change_source IN ('MANUAL','CSV_IMPORT')),
            actor_subject UUID NOT NULL,
            reservation_import_id UUID,
            reason VARCHAR(500), changed_fields JSONB NOT NULL,
            before_values JSONB NOT NULL, after_values JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
            FOREIGN KEY (organization_id,property_id,reservation_id)
              REFERENCES app.reservations(organization_id,property_id,id),
            FOREIGN KEY (organization_id,property_id,reservation_import_id)
              REFERENCES app.reservation_imports(organization_id,property_id,id),
            CHECK (event_type IN ('MANUAL_CREATE','CSV_UPDATE')
                   OR (reason IS NOT NULL AND length(trim(reason)) > 0)),
            CHECK (jsonb_typeof(changed_fields)='array' AND
                   jsonb_typeof(before_values)='object' AND jsonb_typeof(after_values)='object')
        );
        CREATE INDEX ix_reservation_audit_order ON app.reservation_audit_events
            (organization_id,reservation_id,created_at,id);
    """)
    for table, grants in (
        ("reservation_manual_overrides", "SELECT,INSERT,DELETE"),
        ("reservation_audit_events", "SELECT,INSERT"),
    ):
        op.execute(f"REVOKE ALL ON app.{table} FROM PUBLIC")
        op.execute(f"GRANT {grants} ON app.{table} TO stay_insight_runtime")
        op.execute(f"ALTER TABLE app.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE app.{table} FORCE ROW LEVEL SECURITY")
        condition = f"""organization_id =
            nullif(current_setting('app.organization_id',true),'')::uuid
            AND EXISTS (SELECT 1 FROM app.organization_members m
            WHERE m.organization_id={table}.organization_id
            AND m.user_id=nullif(current_setting('app.user_id',true),'')::uuid)"""
        actor_column = "actor_subject" if table.endswith("events") else "created_by_subject"
        op.execute(f"""CREATE POLICY tenant_access ON app.{table} FOR ALL
            TO stay_insight_runtime USING ({condition}) WITH CHECK ({condition}
            AND {actor_column}=nullif(current_setting('app.user_id',true),'')::uuid)""")


def downgrade() -> None:
    # Cannot safely represent manual rows in the old mandatory-import schema.
    op.execute("""DO $$ BEGIN IF EXISTS (SELECT 1 FROM app.reservations WHERE origin='MANUAL')
        THEN RAISE EXCEPTION 'Manual rows prevent safe downgrade'; END IF; END $$;""")
    op.drop_table("reservation_audit_events", schema="app")
    op.drop_table("reservation_manual_overrides", schema="app")
    op.execute("""
        ALTER TABLE app.reservations DROP CONSTRAINT reservation_scope_identity,
          DROP CONSTRAINT reservation_origin_lineage, DROP CONSTRAINT reservation_origin,
          DROP COLUMN origin, DROP COLUMN version,
          ALTER COLUMN import_id SET NOT NULL, ALTER COLUMN external_reservation_id SET NOT NULL;
        ALTER TABLE app.reservation_imports DROP COLUMN protected_fields_count;
    """)
