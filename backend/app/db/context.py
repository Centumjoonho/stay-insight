from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def set_context(db: Session, key: str, value: UUID) -> None:
    db.execute(text("SELECT set_config(:key, :value, true)"), {"key": key, "value": str(value)})
