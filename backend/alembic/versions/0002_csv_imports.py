"""Generic owner CSV batches and normalized reservations; Phase 2 is unchanged."""

from alembic import op

revision = "0002_csv_imports"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE app.reservation_imports ( id UUID NOT NULL, organization_id UUID NOT NULL,
        property_id UUID NOT NULL, channel VARCHAR(20) NOT NULL, original_filename VARCHAR(200)
        NOT NULL, file_checksum VARCHAR(64) NOT NULL, status VARCHAR(20) NOT NULL, total_rows
        INTEGER NOT NULL, imported_rows INTEGER NOT NULL, rejected_rows INTEGER NOT NULL,
        inserted_rows INTEGER NOT NULL, updated_rows INTEGER NOT NULL, created_by_user_id UUID
        NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, completed_at
        TIMESTAMP WITH TIME ZONE, error_message VARCHAR(300), column_mapping JSONB NOT NULL,
        validation_errors JSONB NOT NULL, adapter_version VARCHAR(30) NOT NULL, PRIMARY KEY
        (id), FOREIGN KEY(organization_id, property_id) REFERENCES app.properties
        (organization_id, id), UNIQUE (organization_id, property_id, id), CHECK (channel IN
        ('AIRBNB', 'BOOKING', 'AGODA', 'DIRECT', 'GENERIC')), CHECK (status IN ('PENDING',
        'PROCESSING', 'COMPLETED', 'FAILED')), CHECK (total_rows >= 0 AND imported_rows >= 0 AND
        rejected_rows >= 0), CHECK (imported_rows <= total_rows AND rejected_rows <=
        total_rows), FOREIGN KEY(organization_id) REFERENCES app.organizations (id) )
    """)
    op.execute("""
        CREATE INDEX ix_imports_scope ON app.reservation_imports (organization_id, property_id,
        created_at)
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_imports_completed_file ON app.reservation_imports (property_id,
        channel, file_checksum) WHERE status = 'COMPLETED'
    """)
    op.execute("""
        REVOKE ALL ON app.reservation_imports FROM PUBLIC
    """)
    op.execute("""
        GRANT SELECT, INSERT ON app.reservation_imports TO stay_insight_runtime
    """)
    op.execute("""
        ALTER TABLE app.reservation_imports ENABLE ROW LEVEL SECURITY
    """)
    op.execute("""
        ALTER TABLE app.reservation_imports FORCE ROW LEVEL SECURITY
    """)
    op.execute("""
        CREATE POLICY tenant_access ON app.reservation_imports FOR ALL TO stay_insight_runtime
        USING (organization_id = nullif(current_setting('app.organization_id', true), '')::uuid
        AND EXISTS (SELECT 1 FROM app.organization_members m WHERE m.organization_id =
        reservation_imports.organization_id AND m.user_id =
        nullif(current_setting('app.user_id', true), '')::uuid)) WITH CHECK (organization_id =
        nullif(current_setting('app.organization_id', true), '')::uuid AND EXISTS (SELECT 1 FROM
        app.organization_members m WHERE m.organization_id = reservation_imports.organization_id
        AND m.user_id = nullif(current_setting('app.user_id', true), '')::uuid))
    """)
    op.execute("""
        CREATE TABLE app.reservations ( id UUID NOT NULL, organization_id UUID NOT NULL,
        property_id UUID NOT NULL, import_id UUID NOT NULL, channel VARCHAR(20) NOT NULL,
        external_reservation_id VARCHAR(200) NOT NULL, check_in DATE NOT NULL, check_out DATE
        NOT NULL, booked_nights INTEGER NOT NULL, guest_count INTEGER, gross_revenue NUMERIC(18,
        0) NOT NULL, channel_fee NUMERIC(18, 0), net_revenue NUMERIC(18, 0), reservation_status
        VARCHAR(20) NOT NULL, created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, PRIMARY KEY (id), FOREIGN
        KEY(organization_id, property_id) REFERENCES app.properties (organization_id, id),
        FOREIGN KEY(organization_id, property_id, import_id) REFERENCES app.reservation_imports
        (organization_id, property_id, id), UNIQUE (property_id, channel,
        external_reservation_id), CHECK (channel IN ('AIRBNB', 'BOOKING', 'AGODA', 'DIRECT',
        'GENERIC')), CHECK (check_out > check_in AND booked_nights = check_out - check_in),
        CHECK (guest_count IS NULL OR guest_count >= 1), CHECK (gross_revenue >= 0 AND
        gross_revenue <> 'NaN'::numeric), CHECK (channel_fee IS NULL OR (channel_fee >= 0 AND
        channel_fee <= gross_revenue)), CHECK ((channel_fee IS NULL AND net_revenue IS NULL) OR
        (channel_fee IS NOT NULL AND net_revenue IS NOT NULL AND net_revenue = gross_revenue -
        channel_fee)), CHECK (reservation_status IN ('CONFIRMED', 'CANCELLED', 'UNKNOWN')),
        FOREIGN KEY(organization_id) REFERENCES app.organizations (id) )
    """)
    op.execute("""
        CREATE INDEX ix_reservations_import ON app.reservations (organization_id, property_id,
        import_id)
    """)
    op.execute("""
        CREATE INDEX ix_reservations_scope_date ON app.reservations (organization_id,
        property_id, check_in, id)
    """)
    op.execute("""
        REVOKE ALL ON app.reservations FROM PUBLIC
    """)
    op.execute("""
        GRANT SELECT, INSERT ON app.reservations TO stay_insight_runtime
    """)
    op.execute("""
        ALTER TABLE app.reservations ENABLE ROW LEVEL SECURITY
    """)
    op.execute("""
        ALTER TABLE app.reservations FORCE ROW LEVEL SECURITY
    """)
    op.execute("""
        CREATE POLICY tenant_access ON app.reservations FOR ALL TO stay_insight_runtime USING
        (organization_id = nullif(current_setting('app.organization_id', true), '')::uuid AND
        EXISTS (SELECT 1 FROM app.organization_members m WHERE m.organization_id =
        reservations.organization_id AND m.user_id = nullif(current_setting('app.user_id',
        true), '')::uuid)) WITH CHECK (organization_id =
        nullif(current_setting('app.organization_id', true), '')::uuid AND EXISTS (SELECT 1 FROM
        app.organization_members m WHERE m.organization_id = reservations.organization_id AND
        m.user_id = nullif(current_setting('app.user_id', true), '')::uuid))
    """)
    op.execute("""
        GRANT UPDATE (status, imported_rows, rejected_rows, inserted_rows, updated_rows,
        completed_at, error_message) ON app.reservation_imports TO stay_insight_runtime
    """)
    op.execute("""
        GRANT UPDATE (import_id, check_in, check_out, booked_nights, guest_count, gross_revenue,
        channel_fee, net_revenue, reservation_status, updated_at) ON app.reservations TO
        stay_insight_runtime
    """)


def downgrade() -> None:
    op.drop_table("reservations", schema="app")
    op.drop_table("reservation_imports", schema="app")
