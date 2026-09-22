from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.models.foundation import Organization, OrganizationMember, Property


def user_memberships(db: Session, user_id: UUID) -> list[tuple[OrganizationMember, Organization]]:
    rows = db.execute(
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == user_id)
        .order_by(OrganizationMember.created_at, OrganizationMember.id)
    ).all()
    return [(row[0], row[1]) for row in rows]


def membership(db: Session, user_id: UUID, organization_id: UUID) -> OrganizationMember | None:
    return db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user_id,
            OrganizationMember.organization_id == organization_id,
        )
    )


def lock_onboarding(db: Session, user_id: UUID) -> None:
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": "onboarding:" + str(user_id)},
    )


def insert_organization(db: Session, organization: Organization) -> None:
    db.add(organization)
    db.flush()


def insert_owner(db: Session, organization_id: UUID, user_id: UUID) -> None:
    db.add(OrganizationMember(organization_id=organization_id, user_id=user_id, role="OWNER"))
    db.flush()


def insert_property(db: Session, item: Property) -> Property:
    db.add(item)
    db.flush()
    return item


def get_property(db: Session, organization_id: UUID, property_id: UUID) -> Property | None:
    return db.scalar(
        select(Property).where(
            Property.organization_id == organization_id,
            Property.id == property_id,
        )
    )


def list_properties(
    db: Session,
    organization_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[Property], int]:
    scope = Property.organization_id == organization_id
    items = list(
        db.scalars(
            select(Property)
            .where(scope)
            .order_by(Property.created_at, Property.id)
            .limit(limit)
            .offset(offset)
        )
    )
    total = db.scalar(select(func.count()).select_from(Property).where(scope))
    return items, total or 0


def save_property(
    db: Session,
    organization_id: UUID,
    property_id: UUID,
    changes: dict[str, object],
) -> Property | None:
    item = db.scalar(
        update(Property)
        .where(
            Property.organization_id == organization_id,
            Property.id == property_id,
        )
        .values(**changes)
        .returning(Property)
        .execution_options(populate_existing=True)
    )
    return item
