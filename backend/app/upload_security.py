"""Upload security for Project A RAG Platform."""
from __future__ import annotations

import uuid
from pathlib import Path


def safe_save_upload(file, target_dir: Path, max_bytes: int = 10 * 1024 * 1024):
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = file.filename or f"upload_{uuid.uuid4().hex[:8]}"
    # Sanitize filename
    filename = Path(filename).name  # Remove any path components
    saved_path = target_dir / filename
    content = file.file.read()
    if len(content) > max_bytes:
        raise ValueError(f"File too large: {len(content)} bytes (max {max_bytes})")
    saved_path.write_bytes(content)
    return filename, saved_path
