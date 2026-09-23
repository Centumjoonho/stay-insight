"""Manual property expenses, separate from reservation channel fees."""

from alembic import op

revision = "0003_expenses"
down_revision = "0002_csv_imports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE app.expenses (
            id UUID PRIMARY KEY, organization_id UUID NOT NULL REFERENCES app.organizations(id),
            property_id UUID NOT NULL, expense_date DATE NOT NULL,
            category VARCHAR(30) NOT NULL, cost_type VARCHAR(20) NOT NULL,
            amount NUMERIC(18,0) NOT NULL, memo VARCHAR(1000),
            source VARCHAR(20) NOT NULL, created_by_user_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, property_id)
                REFERENCES app.properties(organization_id,id),
            CHECK (amount >= 0 AND amount <> 'NaN'::numeric),
            CHECK (category IN ('RENT','MANAGEMENT_FEE','CLEANING','LAUNDRY','ELECTRICITY',
                'GAS','WATER','SUPPLIES','LABOR','MARKETING','MAINTENANCE','SUBSCRIPTION',
                'INSURANCE','TAX_AND_FEE','OTHER')),
            CHECK (cost_type IN ('FIXED','VARIABLE')), CHECK (source = 'MANUAL')
        )
    """)
    op.execute(
        "CREATE INDEX ix_expenses_scope_date ON app.expenses"
        " (organization_id,property_id,expense_date,id)"
    )
    op.execute("REVOKE ALL ON app.expenses FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT, DELETE ON app.expenses TO stay_insight_runtime")
    op.execute("""GRANT UPDATE (expense_date,category,cost_type,amount,memo,updated_at)
                  ON app.expenses TO stay_insight_runtime""")
    op.execute("ALTER TABLE app.expenses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE app.expenses FORCE ROW LEVEL SECURITY")
    condition = """organization_id = nullif(current_setting('app.organization_id',true),'')::uuid
        AND EXISTS (SELECT 1 FROM app.organization_members m
                    WHERE m.organization_id = expenses.organization_id
                    AND m.user_id = nullif(current_setting('app.user_id',true),'')::uuid)"""
    op.execute(f"""CREATE POLICY tenant_access ON app.expenses FOR ALL TO stay_insight_runtime
                   USING ({condition}) WITH CHECK ({condition})""")


def downgrade() -> None:
    op.drop_table("expenses", schema="app")
