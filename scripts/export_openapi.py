"""Export the FastAPI OpenAPI schema to docs/openapi.json.

This script is intentionally deterministic so CI can detect schema/type drift.
It builds the app with isolated temporary storage and local-only settings, then
    writes a pretty JSON schema while preserving FastAPI's native key order.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
OPENAPI_PATH = PROJECT_ROOT / "docs" / "openapi.json"


def _prepare_env(tmp_dir: Path) -> None:
    defaults = {
        "STORAGE_BACKEND": "sqlite",
        "VECTOR_BACKEND": "chroma",
        "CACHE_ENABLED": "false",
        "AUTH_ENABLED": "false",
        "RATE_LIMIT_ENABLED": "false",
        "METRICS_ENABLED": "false",
        "GRAPH_RETRIEVAL_ENABLED": "false",
        "APP_DATABASE_PATH": str(tmp_dir / "openapi_export.db"),
        "CHROMA_PERSIST_DIR": str(tmp_dir / "chroma"),
        "SEED_DOCS_DIR": str(PROJECT_ROOT / "data" / "seed_docs"),
        "REAL_DOCS_DIR": str(PROJECT_ROOT / "data" / "real_manuals_sanitized"),
        "UPLOADED_DOCS_DIR": str(tmp_dir / "uploaded_docs"),
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


def export_openapi() -> None:
    sys.path.insert(0, str(BACKEND_DIR))
    with tempfile.TemporaryDirectory(prefix="project_a_openapi_", ignore_cleanup_errors=True) as tmp:
        tmp_dir = Path(tmp)
        (tmp_dir / "uploaded_docs").mkdir(parents=True, exist_ok=True)
        _prepare_env(tmp_dir)

        from app.main import create_app

        app = create_app(
            database_path=tmp_dir / "openapi_export.db",
            chroma_dir=tmp_dir / "chroma",
            uploaded_docs_dir=tmp_dir / "uploaded_docs",
        )
        schema = app.openapi()

    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Exported OpenAPI schema to docs/openapi.json")


if __name__ == "__main__":
    export_openapi()
