from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.db.context import set_context
from app.db.session import get_session_factory
from app.services.foundation import authorize_organization

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def get_db(user: CurrentUser, response: Response) -> Iterator[Session]:
    response.headers["Cache-Control"] = "private, no-store"
    with get_session_factory()() as db, db.begin():
        unsafe = db.scalar(
            text("""
            SELECT rolsuper OR rolbypassrls OR EXISTS (
                SELECT 1 FROM pg_tables WHERE schemaname = 'app' AND tableowner = current_user
            ) FROM pg_roles WHERE rolname = current_user
        """)
        )
        if unsafe:
            raise HTTPException(503, "A restricted runtime database role is required")
        set_context(db, "app.user_id", user.user_id)
        yield db


Database = Annotated[Session, Depends(get_db, scope="function")]


def organization_context(
    db: Database,
    user: CurrentUser,
    x_organization_id: Annotated[UUID, Header()],
) -> UUID:
    return authorize_organization(db, user.user_id, x_organization_id)


OrganizationContext = Annotated[UUID, Depends(organization_context)]
