import os
from pathlib import Path

os.environ["STORAGE_BACKEND"] = "sqlite"
os.environ["VECTOR_BACKEND"] = "chroma"
os.environ["CACHE_ENABLED"] = "false"
os.environ["GRAPH_RETRIEVAL_ENABLED"] = "false"

from app.main import create_app
from fastapi.testclient import TestClient


def _make_client(tmp_path: Path) -> TestClient:
    docs_dir = tmp_path / "docs"
    real_dir = tmp_path / "real_docs"
    uploaded_dir = tmp_path / "uploaded_docs"
    docs_dir.mkdir()
    real_dir.mkdir()
    uploaded_dir.mkdir()
    (docs_dir / "test.txt").write_text("test document content", encoding="utf-8")
    app = create_app(
        database_path=tmp_path / "app.db",
        chroma_dir=tmp_path / "chroma",
        seed_docs_dir=docs_dir,
        real_docs_dir=real_dir,
        uploaded_docs_dir=uploaded_dir,
    )
    return TestClient(app)


def test_healthz_returns_200(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "project-a-rag-platform"
    assert body["version"] == "v1.0.5"
    assert body["release_url"] == "https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.5"


def test_readyz_returns_200(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["version"] == "v1.0.5"
    assert body["release_url"] == "https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.5"


def test_readyz_contains_required_checks(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/readyz")
    body = response.json()
    checks = body["checks"]
    assert "config" in checks
    assert "storage" in checks
    assert "vector_store" in checks
    assert "optional_dependencies" in checks


def test_readyz_config_check_ok(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/readyz")
    body = response.json()
    assert body["checks"]["config"]["status"] == "ok"
    assert "provider" in body["checks"]["config"]


def test_readyz_storage_check_ok(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/readyz")
    body = response.json()
    assert body["checks"]["storage"]["status"] == "ok"
    assert "backend" in body["checks"]["storage"]


def test_readyz_vector_store_check(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/readyz")
    body = response.json()
    assert body["checks"]["vector_store"]["status"] in ("ok", "degraded")


def test_readyz_optional_deps_disabled_when_not_configured(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/readyz")
    body = response.json()
    opt = body["checks"]["optional_dependencies"]
    assert opt["redis"] == "disabled"
    assert opt["milvus"] == "disabled"
    assert opt["neo4j"] == "disabled"


def test_legacy_health_still_works(tmp_path: Path):
    client = _make_client(tmp_path)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_returns_503_when_storage_fails(tmp_path: Path):
    client = _make_client(tmp_path)

    class FakeStore:
        def list_chat_records(self):
            raise RuntimeError("storage unavailable")

    client.app.state._store = FakeStore()
    response = client.get("/readyz")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] != "ok"
    assert body["checks"]["storage"]["status"] == "error"


def test_readyz_returns_200_degraded_when_optional_dep_fails(tmp_path: Path):
    client = _make_client(tmp_path)

    class FakeCache:
        def __init__(self):
            self.client = self

        def ping(self):
            raise RuntimeError("redis connection refused")

    object.__setattr__(client.app.state._settings, "cache_enabled", True)
    client.app.state._cache = FakeCache()
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["optional_dependencies"]["redis"].startswith("error:")
