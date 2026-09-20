import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db, get_engine
from app.main import app


@pytest.fixture
def client(engine):
    """
    Overrides get_db/get_engine to point at the SQLite test engine
    (from conftest.py) instead of the real Postgres instance main.py
    would otherwise connect to. This is the payoff of having those as
    dependency-injectable functions rather than bare module imports.
    """
    SessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_engine():
        return engine

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_engine] = override_get_engine

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def make_csv_file(content: str, filename: str = "test.csv"):
    return {"file": (filename, io.BytesIO(content.encode()), "text/csv")}


class TestUploadEndpoint:
    def test_upload_valid_csv_returns_201(self, client):
        csv_content = "name,age\nAlice,30\nBob,25\n"
        response = client.post("/api/v1/datasets/upload", files=make_csv_file(csv_content))

        assert response.status_code == 201
        body = response.json()
        assert body["inserted_count"] == 2
        assert body["failed_rows"] == []
        assert body["dataset"]["status"] == "ingested"
        assert body["dataset"]["row_count"] == 2
        assert len(body["dataset"]["columns"]) == 2

    def test_upload_rejects_unsupported_extension(self, client):
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("data.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_rejects_empty_file(self, client):
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
        )
        assert response.status_code == 400

    def test_column_types_reflected_in_response(self, client):
        csv_content = "count,label\n1,a\n2,b\n3,c\n"
        response = client.post("/api/v1/datasets/upload", files=make_csv_file(csv_content))

        columns = {c["name"]: c["inferred_type"] for c in response.json()["dataset"]["columns"]}
        assert columns["count"] == "integer"
        assert columns["label"] == "string"


class TestListEndpoint:
    def test_list_empty_initially(self, client):
        response = client.get("/api/v1/datasets")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_uploaded_datasets(self, client):
        client.post("/api/v1/datasets/upload", files=make_csv_file("x\n1\n2\n"))
        client.post(
            "/api/v1/datasets/upload", files=make_csv_file("y\n3\n4\n", filename="second.csv")
        )

        response = client.get("/api/v1/datasets")
        body = response.json()
        assert len(body) == 2
        # summary shape shouldn't include per-column detail
        assert "columns" not in body[0]

    def test_list_ordered_newest_first(self, client):
        client.post(
            "/api/v1/datasets/upload", files=make_csv_file("x\n1\n", filename="first.csv")
        )
        client.post(
            "/api/v1/datasets/upload", files=make_csv_file("x\n1\n", filename="second.csv")
        )

        body = client.get("/api/v1/datasets").json()
        assert body[0]["original_filename"] == "second.csv"


class TestGetByIdEndpoint:
    def test_get_existing_dataset_returns_full_detail(self, client):
        upload_response = client.post(
            "/api/v1/datasets/upload", files=make_csv_file("x,y\n1,a\n2,b\n")
        )
        dataset_id = upload_response.json()["dataset"]["id"]

        response = client.get(f"/api/v1/datasets/{dataset_id}")
        assert response.status_code == 200
        assert response.json()["id"] == dataset_id
        assert len(response.json()["columns"]) == 2

    def test_get_nonexistent_dataset_returns_404(self, client):
        response = client.get("/api/v1/datasets/99999")
        assert response.status_code == 404


class TestProfileEndpoint:
    def test_profile_returns_stats_for_each_column(self, client):
        upload_response = client.post(
            "/api/v1/datasets/upload",
            files=make_csv_file("score,label\n10,a\n20,b\n30,a\n"),
        )
        dataset_id = upload_response.json()["dataset"]["id"]

        response = client.get(f"/api/v1/datasets/{dataset_id}/profile")
        assert response.status_code == 200

        body = response.json()
        assert body["row_count"] == 3
        columns = {c["name"]: c for c in body["columns"]}

        assert columns["score"]["mean"] == 20.0
        assert columns["score"]["min_value"] == 10
        assert columns["label"]["top_values"][0]["value"] == "a"

    def test_profile_nonexistent_dataset_returns_404(self, client):
        response = client.get("/api/v1/datasets/99999/profile")
        assert response.status_code == 404


class TestCorrelationsEndpoint:
    def test_correlations_returns_pairs_for_numeric_columns(self, client):
        upload_response = client.post(
            "/api/v1/datasets/upload",
            files=make_csv_file("x,y\n1,2\n2,4\n3,6\n4,8\n"),
        )
        dataset_id = upload_response.json()["dataset"]["id"]

        response = client.get(f"/api/v1/datasets/{dataset_id}/correlations")
        assert response.status_code == 200

        body = response.json()
        assert body["insufficient_columns"] is False
        assert body["pairs"][0]["correlation"] == 1.0
        assert body["pairs"][0]["strength"] == "strong"

    def test_correlations_flags_insufficient_numeric_columns(self, client):
        upload_response = client.post(
            "/api/v1/datasets/upload",
            files=make_csv_file("label\na\nb\nc\n"),
        )
        dataset_id = upload_response.json()["dataset"]["id"]

        response = client.get(f"/api/v1/datasets/{dataset_id}/correlations")
        assert response.status_code == 200
        assert response.json()["insufficient_columns"] is True

    def test_correlations_nonexistent_dataset_returns_404(self, client):
        response = client.get("/api/v1/datasets/99999/correlations")
        assert response.status_code == 404
