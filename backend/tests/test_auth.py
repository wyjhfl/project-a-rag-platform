import os
from pathlib import Path

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"
os.environ["AUTH_ENABLED"] = "false"
os.environ.pop("VIEWER_API_KEY", None)
os.environ.pop("OPERATOR_API_KEY", None)
os.environ.pop("ADMIN_API_KEY", None)

from app.auth import require_role
from app.main import create_app
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def _make_client(tmp_path: Path, auth_enabled: bool = False) -> TestClient:
    docs_dir = tmp_path / "docs"
    real_dir = tmp_path / "real_docs"
    uploaded_dir = tmp_path / "uploaded_docs"
    docs_dir.mkdir()
    real_dir.mkdir()
    uploaded_dir.mkdir()
    (docs_dir / "test.txt").write_text("test document content", encoding="utf-8")
    if auth_enabled:
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["VIEWER_API_KEY"] = "test-viewer-key"
        os.environ["OPERATOR_API_KEY"] = "test-operator-key"
        os.environ["ADMIN_API_KEY"] = "test-admin-key"
    else:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ.pop("VIEWER_API_KEY", None)
        os.environ.pop("OPERATOR_API_KEY", None)
        os.environ.pop("ADMIN_API_KEY", None)
    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
        real_docs_dir=real_dir,
        uploaded_docs_dir=uploaded_dir,
    )
    return TestClient(app)


def test_auth_disabled_no_key_needed(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=False)
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200


def test_auth_enabled_missing_key_returns_401(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=True)
    response = client.get("/api/v1/system/status")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_auth_enabled_invalid_key_returns_401(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=True)
    response = client.get(
        "/api/v1/system/status",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"


def test_auth_enabled_no_keys_configured_returns_503(tmp_path: Path):
    docs_dir = tmp_path / "docs"
    real_dir = tmp_path / "real_docs"
    uploaded_dir = tmp_path / "uploaded_docs"
    docs_dir.mkdir()
    real_dir.mkdir()
    uploaded_dir.mkdir()
    (docs_dir / "test.txt").write_text("test document content", encoding="utf-8")
    os.environ["AUTH_ENABLED"] = "true"
    os.environ["VIEWER_API_KEY"] = ""
    os.environ["OPERATOR_API_KEY"] = ""
    os.environ["ADMIN_API_KEY"] = ""
    try:
        app = create_app(
            database_path=tmp_path / "app.db",
            chroma_dir=tmp_path / "chroma",
            seed_docs_dir=docs_dir,
            real_docs_dir=real_dir,
            uploaded_docs_dir=uploaded_dir,
        )
        client = TestClient(app)
        response = client.get("/api/v1/system/status")
        assert response.status_code == 503
        assert "no API keys are configured" in response.json()["detail"]
    finally:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ.pop("VIEWER_API_KEY", None)
        os.environ.pop("OPERATOR_API_KEY", None)
        os.environ.pop("ADMIN_API_KEY", None)


def test_viewer_can_access_viewer_endpoint(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=True)
    response = client.get(
        "/api/v1/system/status",
        headers={"X-API-Key": "test-viewer-key"},
    )
    assert response.status_code == 200


def test_viewer_cannot_access_operator_endpoint(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=True)
    response = client.post(
        "/api/v1/documents/ingest",
        headers={"X-API-Key": "test-viewer-key"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_operator_can_access_operator_endpoint(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=True)
    response = client.post(
        "/api/v1/documents/ingest",
        headers={"X-API-Key": "test-operator-key"},
    )
    assert response.status_code == 200


def test_operator_cannot_access_admin_endpoint():
    test_app = FastAPI()

    @test_app.post("/admin-only", dependencies=[Depends(require_role("admin"))])
    def admin_only():
        return {"ok": True}

    os.environ["AUTH_ENABLED"] = "true"
    os.environ["VIEWER_API_KEY"] = "test-viewer-key"
    os.environ["OPERATOR_API_KEY"] = "test-operator-key"
    os.environ["ADMIN_API_KEY"] = "test-admin-key"
    try:
        client = TestClient(test_app)
        response = client.post("/admin-only", headers={"X-API-Key": "test-operator-key"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Insufficient permissions"
    finally:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ.pop("VIEWER_API_KEY", None)
        os.environ.pop("OPERATOR_API_KEY", None)
        os.environ.pop("ADMIN_API_KEY", None)


def test_admin_can_access_viewer_endpoint(tmp_path: Path):
    client = _make_client(tmp_path, auth_enabled=True)
    response = client.get(
        "/api/v1/system/status",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert response.status_code == 200


def test_duplicate_key_gets_highest_role():
    test_app = FastAPI()

    @test_app.post("/admin-only", dependencies=[Depends(require_role("admin"))])
    def admin_only():
        return {"ok": True}

    shared_key = "shared-same-key"
    os.environ["AUTH_ENABLED"] = "true"
    os.environ["VIEWER_API_KEY"] = shared_key
    os.environ["OPERATOR_API_KEY"] = shared_key
    os.environ["ADMIN_API_KEY"] = shared_key
    try:
        client = TestClient(test_app)
        response = client.post("/admin-only", headers={"X-API-Key": shared_key})
        assert response.status_code == 200
    finally:
        os.environ["AUTH_ENABLED"] = "false"
        os.environ.pop("VIEWER_API_KEY", None)
        os.environ.pop("OPERATOR_API_KEY", None)
        os.environ.pop("ADMIN_API_KEY", None)
