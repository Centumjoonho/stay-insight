"""Explicit admin-only association. Never guess a district from free-text addresses."""

import argparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.providers.accommodation import BUSAN_DISTRICTS
from app.repositories.market import assign_property_region


def main() -> None:
    parser = argparse.ArgumentParser(description="Admin-confirmed Busan district association")
    parser.add_argument("--organization-id", type=UUID, required=True)
    parser.add_argument("--property-id", type=UUID, required=True)
    parser.add_argument("--district", choices=BUSAN_DISTRICTS, required=True)
    parser.add_argument(
        "--confirmed-address",
        required=True,
        help="Exact current address, independently checked by the administrator",
    )
    args = parser.parse_args()
    with Session(get_engine()) as db, db.begin():
        changed = assign_property_region(
            db, args.organization_id, args.property_id, args.district, args.confirmed_address
        )
        if not changed:
            raise SystemExit("Property/context/address mismatch; no assignment made")
    print("Region assigned by explicit administrator confirmation; addresses unchanged.")


if __name__ == "__main__":
    main()
