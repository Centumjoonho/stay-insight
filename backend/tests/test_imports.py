import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text
from sqlalchemy.orm import Session
from test_foundation import onboard, property_body

from app.core.auth.jwt import AuthenticatedUser, get_current_user
from app.core.config import Settings
from app.db.context import set_context
from app.importers.generic import MAX_BYTES, GenericCsvAdapter, NormalizedRow, parse_csv
from app.main import create_app
from app.models.imports import ReservationImport
from app.repositories import imports as repo
from app.schemas.imports import ColumnMapping

pytest_plugins = ["test_foundation"]
CSV = (
    b"id,in,out,gross,fee,guests,status,nights\n"
    b"R1,2026-09-01,2026-09-03,200000,20000,2,CONFIRMED,999\n"
)
MAPPING = {
    "external_reservation_id": "id",
    "check_in": "in",
    "check_out": "out",
    "gross_revenue": "gross",
    "channel_fee": "fee",
    "guest_count": "guests",
    "reservation_status": "status",
}


def setup(client: TestClient) -> tuple[dict[str, str], str]:
    org = onboard(client)
    headers = {"X-Organization-Id": org}
    property_id = client.post("/api/v1/properties", headers=headers, json=property_body()).json()[
        "id"
    ]
    return headers, property_id


def upload(
    client: TestClient,
    headers: dict[str, str],
    property_id: str,
    data: bytes = CSV,
    endpoint: str = "/api/v1/imports",
    mapping: dict[str, str] | None = None,
) -> Response:
    return cast(
        Response,
        client.post(
            endpoint,
            headers=headers,
            files={"file": ("data.csv", data, "text/csv")},
            data={
                "property_id": property_id,
                "channel": "GENERIC",
                "column_mapping": json.dumps(MAPPING if mapping is None else mapping),
            },
        ),
    )


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp949"])
def test_preview_encodings(encoding: str) -> None:
    data = "예약번호,체크인\n테스트,2026-09-01\n".encode(encoding)
    doc = parse_csv("테스트.csv", data)
    assert doc.encoding == encoding
    assert doc.headers == ["예약번호", "체크인"]
    assert doc.rows[0][0] == "테스트"


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"\x00binary",
        b'a,b\n"unterminated',
        b"a,a\n1,2",
        b"a,b\n1",
        b"a,b\n1,2,3",
        b"a,b\n",
        b" a,b\n1,2",
        b"a,b\n\xff,2",
        b"a,b\n" + b"x" * 4097 + b",2",
    ],
)
def test_invalid_csv(data: bytes) -> None:
    with pytest.raises(HTTPException):
        parse_csv("data.csv", data)


def test_limits_and_extension() -> None:
    for filename, data, status in [
        ("x.xlsx", CSV, 422),
        ("x.csv", b"x" * (MAX_BYTES + 1), 413),
        ("x.csv", b"a\n" + b"v\n" * 10001, 413),
    ]:
        with pytest.raises(HTTPException) as error:
            parse_csv(filename, data)
        assert error.value.status_code == status


@pytest.mark.parametrize(
    "old,new",
    [
        (b"2026-09-03", b"2026-09-01"),
        (b"2026-09-03", b"2026-08-31"),
        (b"2026-09-01", b"2026-02-30"),
        (b"200000", b"NaN"),
        (b"200000", b"1e5"),
        (b"200000", b"1.50"),
        (b"200000", b"-100"),
        (b"20000,", b"300000,"),
        (b"CONFIRMED", b"maybe"),
        (b",2,", b",0,"),
        (b"R1,", b"=cmd,"),
    ],
)
def test_invalid_normalized_values(old: bytes, new: bytes) -> None:
    rows, result = GenericCsvAdapter().normalize(
        parse_csv("data.csv", CSV.replace(old, new)), ColumnMapping(**MAPPING)
    )
    assert not rows and result.invalid_rows == 1
    assert result.errors[0].row == 2
    assert new.decode() not in result.errors[0].message


def test_exact_money_nights_and_nullable_values() -> None:
    data = CSV.replace(b"200000", b"999999999999999999").replace(b"20000,", b",")
    rows, result = GenericCsvAdapter().normalize(
        parse_csv("data.csv", data), ColumnMapping(**MAPPING)
    )
    assert result.valid_rows == 1
    assert rows[0].booked_nights == 2
    assert rows[0].gross_revenue == Decimal("999999999999999999")
    assert rows[0].net_revenue is None


def test_import_roundtrip_upsert_and_filters(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        preview = client.post("/api/v1/imports/preview", files={"file": ("x.csv", CSV)})
        assert preview.status_code == 200
        assert preview.json()["total_rows"] == 1
        assert client.get("/api/v1/imports", headers=headers).json()["total"] == 0
        validation = upload(client, headers, prop, endpoint="/api/v1/imports/validate")
        assert validation.json()["valid_rows"] == 1
        assert client.get("/api/v1/imports", headers=headers).json()["total"] == 0
        result = upload(client, headers, prop)
        assert result.status_code == 200, result.text
        batch = result.json()
        assert batch["status"] == "COMPLETED" and batch["inserted_rows"] == 1
        duplicate = upload(client, headers, prop).json()
        assert duplicate["duplicate"] and duplicate["id"] == batch["id"]
        changed = upload(client, headers, prop, CSV.replace(b"200000", b"300000")).json()
        assert changed["updated_rows"] == 1 and changed["inserted_rows"] == 0
        reservations = client.get("/api/v1/reservations", headers=headers).json()
        assert reservations["total"] == 1
        item = reservations["items"][0]
        assert item["booked_nights"] == 2 and item["gross_revenue"] == "300000"
        assert item["net_revenue"] == "280000"
        assert item["import_id"] == changed["id"]
        assert client.get("/api/v1/reservations/" + item["id"], headers=headers).status_code == 200
        assert client.get("/api/v1/imports/" + batch["id"], headers=headers).status_code == 200
        for query, total in [
            ("channel=AIRBNB", 0),
            ("from=2026-09-02", 0),
            ("to=2026-08-31", 0),
            ("reservation_status=CANCELLED", 0),
            ("from=2026-09-01&to=2026-09-01", 1),
            ("limit=1&offset=1", 1),
        ]:
            response = client.get("/api/v1/reservations?" + query, headers=headers)
            assert response.json()["total"] == total
            if "offset" in query:
                assert response.json()["items"] == []
        assert client.get("/api/v1/reservations?limit=101", headers=headers).status_code == 422
        assert (
            client.get(
                "/api/v1/reservations?from=2026-10-01&to=2026-09-01", headers=headers
            ).status_code
            == 422
        )
        assert client.get("/api/v1/imports?channel=AIRBNB", headers=headers).json()["total"] == 0


@pytest.mark.parametrize(
    "field", ["external_reservation_id", "check_in", "check_out", "gross_revenue"]
)
def test_required_mapping(context: SimpleNamespace, field: str) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        mapping = dict(MAPPING)
        del mapping[field]
        assert upload(client, headers, prop, mapping=mapping).status_code == 422


def test_all_or_nothing_and_duplicate_ids(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        rows = CSV + b"R2,2026-09-01,2026-08-31,100000,0,1,UNKNOWN,1\n"
        result = upload(client, headers, prop, rows).json()
        assert result["status"] == "FAILED"
        assert result["imported_rows"] == 0 and result["rejected_rows"] == 1
        assert result["validation_errors"][0]["row"] == 3
        assert client.get("/api/v1/reservations", headers=headers).json()["total"] == 0
        duplicate_rows = CSV + CSV.split(b"\n")[1] + b"\n"
        assert upload(client, headers, prop, duplicate_rows).json()["status"] == "FAILED"


def test_rollback_after_write(context: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    real_upsert = repo.upsert_rows

    def failing(
        db: Session, batch: ReservationImport, rows: list[NormalizedRow]
    ) -> tuple[int, int]:
        real_upsert(db, batch, rows)
        raise RuntimeError("sensitive source must not be logged")

    with TestClient(context.app) as client:
        headers, prop = setup(client)
        assert upload(client, headers, prop).json()["status"] == "COMPLETED"
        monkeypatch.setattr(repo, "upsert_rows", failing)
        result = upload(client, headers, prop, CSV.replace(b"200000", b"300000")).json()
        assert result["status"] == "FAILED" and result["imported_rows"] == 0
        assert "sensitive" not in result["error_message"]
        item = client.get("/api/v1/reservations", headers=headers).json()["items"][0]
        assert item["gross_revenue"] == "200000"
        monkeypatch.setattr(repo, "upsert_rows", real_upsert)
        assert (
            upload(client, headers, prop, CSV.replace(b"200000", b"300000")).json()["status"]
            == "COMPLETED"
        )


def test_import_security(context: SimpleNamespace) -> None:
    public = create_app(Settings())
    other = create_app(Settings())
    other.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uuid4())
    with TestClient(context.app) as a, TestClient(public) as anonymous, TestClient(other) as b:
        headers, prop = setup(a)
        for path in ["/api/v1/imports", "/api/v1/imports/preview", "/api/v1/imports/validate"]:
            assert upload(anonymous, headers, prop, endpoint=path).status_code == 401
        batch = upload(a, headers, prop).json()
        item = a.get("/api/v1/reservations", headers=headers).json()["items"][0]
        # Stable second user for all requests.
        uid = uuid4()
        other.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid)
        hb, pb = setup(b)
        assert upload(b, hb, prop).status_code == 404
        assert upload(b, headers, prop).status_code == 403
        for path in [
            "/api/v1/imports/" + batch["id"],
            "/api/v1/reservations/" + item["id"],
            "/api/v1/imports?property_id=" + prop,
            "/api/v1/reservations?property_id=" + prop,
        ]:
            assert b.get(path, headers=hb).status_code == 404
        assert b.get("/api/v1/imports", headers=hb).json()["total"] == 0
        assert b.get("/api/v1/reservations", headers=hb).json()["total"] == 0
        with context.db.factory() as db, db.begin():
            set_context(db, "app.user_id", uid)
            set_context(db, "app.organization_id", UUID(hb["X-Organization-Id"]))
            assert db.execute(text("SELECT id FROM app.reservations")).all() == []
            assert db.execute(text("SELECT id FROM app.reservation_imports")).all() == []
        assert upload(a, headers, prop, b"x" * (MAX_BYTES + 1)).status_code == 413
        assert upload(a, headers, prop, b"x" * (7 * 1024 * 1024)).status_code == 413
        assert upload(a, headers, prop, b'a,b\n"unterminated').status_code == 422


def test_concurrent_same_file(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)

    def submit() -> dict[str, object]:
        with TestClient(context.app) as client:
            return cast(dict[str, object], upload(client, headers, prop).json())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert results[0]["id"] == results[1]["id"]
    assert sorted(bool(result["duplicate"]) for result in results) == [False, True]


def test_phase3_migration_preserves_phase2_data(context: SimpleNamespace) -> None:
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    with TestClient(context.app) as client:
        headers, prop = setup(client)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        command.downgrade(config, "0001_foundation")
        assert client.get("/api/v1/properties/" + prop, headers=headers).status_code == 200
        command.upgrade(config, "head")
        assert client.get("/api/v1/properties/" + prop, headers=headers).status_code == 200
        assert upload(client, headers, prop).json()["status"] == "COMPLETED"


def test_mapping_and_duplicate_scope(context: SimpleNamespace) -> None:
    with TestClient(context.app) as client:
        headers, prop = setup(client)
        bad_mapping = dict(MAPPING, check_out="in")
        assert upload(client, headers, prop, mapping=bad_mapping).status_code == 422
        assert (
            upload(client, headers, prop, mapping=dict(MAPPING, gross_revenue="absent")).status_code
            == 422
        )
        assert upload(client, headers, prop).json()["status"] == "COMPLETED"
        prop2 = client.post("/api/v1/properties", headers=headers, json=property_body()).json()[
            "id"
        ]
        assert not upload(client, headers, prop2).json()["duplicate"]
        result = client.post(
            "/api/v1/imports",
            headers=headers,
            files={"file": ("x.csv", CSV)},
            data={"property_id": prop, "channel": "AIRBNB", "column_mapping": json.dumps(MAPPING)},
        )
        assert result.json()["status"] == "COMPLETED"
        assert not result.json()["duplicate"]


def test_csv_error_summary_is_bounded() -> None:
    document = parse_csv("errors.csv", b"id,in,out,gross\n" + b"x,no,no,no\n" * 120)
    _, result = GenericCsvAdapter().normalize(
        document,
        ColumnMapping(
            external_reservation_id="id", check_in="in", check_out="out", gross_revenue="gross"
        ),
    )
    assert result.invalid_rows == 120 and len(result.errors) == 100 and result.errors_truncated


def test_import_foreign_keys_and_revoked_membership(context: SimpleNamespace) -> None:
    from sqlalchemy.exc import IntegrityError

    uid = uuid4()
    other = create_app(Settings())
    other.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(uid)
    with TestClient(context.app) as a, TestClient(other) as b:
        ha, pa = setup(a)
        hb, pb = setup(b)
        with pytest.raises(IntegrityError), context.db.factory() as db, db.begin():
            set_context(db, "app.user_id", uid)
            set_context(db, "app.organization_id", UUID(hb["X-Organization-Id"]))
            forged = ReservationImport(
                organization_id=UUID(hb["X-Organization-Id"]),
                property_id=UUID(pa),
                channel="GENERIC",
                original_filename="fixture.csv",
                file_checksum="a" * 64,
                status="PENDING",
                total_rows=1,
                created_by_user_id=uid,
                column_mapping=MAPPING,
                validation_errors=[],
            )
            repo.save_batch(db, forged)
        assert upload(b, hb, pb).json()["status"] == "COMPLETED"
        with context.db.admin.begin() as db:
            db.execute(
                text(
                    "DELETE FROM app.organization_members WHERE user_id=:user "
                    "AND organization_id=:org"
                ),
                {"user": uid, "org": UUID(hb["X-Organization-Id"])},
            )
        assert b.get("/api/v1/imports", headers=hb).status_code == 403
        assert b.get("/api/v1/reservations", headers=hb).status_code == 403
        assert upload(b, hb, pb).status_code == 403
        assert a.get("/api/v1/properties/" + pa, headers=ha).json()["inventory_units"] == 3
