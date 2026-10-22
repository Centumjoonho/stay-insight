"""Canonical mutable reservation fields; no identity or authorization metadata."""

from enum import StrEnum


class ReservationField(StrEnum):
    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    GROSS_REVENUE = "gross_revenue"
    CHANNEL_FEE = "channel_fee"
    GUEST_COUNT = "guest_count"
    STATUS = "reservation_status"
    ROOM_UNITS = "room_units"


MUTABLE_FIELDS = tuple(field.value for field in ReservationField)
