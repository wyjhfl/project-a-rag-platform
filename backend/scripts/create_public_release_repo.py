from __future__ import annotations

import argparse
import re
from pathlib import Path

_REPO_PARENT = r"(?:我的学习计划|鎴戜殑瀛︿範璁″垝)"
_REPO_NAME = r"(?:天空没有极限|澶╃┖娌℃湁鏋侀檺)"

SANITIZE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(rf"[A-Z]:[\\/]+[^\\/]+[\\/]+{_REPO_PARENT}[\\/]+{_REPO_NAME}", re.IGNORECASE),
        "<LOCAL_REPO_ROOT>",
    ),
    (
        re.compile(rf"/mnt/[a-z]/[^/]+/{_REPO_PARENT}/{_REPO_NAME}", re.IGNORECASE),
        "<LOCAL_REPO_ROOT>",
    ),
    (
        re.compile(r"/home/[a-zA-Z_][a-zA-Z0-9_-]*"),
        "<WSL_HOME>",
    ),
    (
        re.compile(r"[A-Z]:[\\/]+[^\\/]*[Dd]ownloads?", re.IGNORECASE),
        "<LOCAL_DOWNLOAD_DIR>",
    ),
]


def sanitize_text(text: str) -> str:
    for pattern, replacement in SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanitize text files for a public Project A release.",
    )
    parser.add_argument("source", type=Path, help="Input text file")
    parser.add_argument("target", type=Path, help="Output sanitized file")
    args = parser.parse_args()

    raw = args.source.read_text(encoding="utf-8")
    args.target.parent.mkdir(parents=True, exist_ok=True)
    args.target.write_text(sanitize_text(raw), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
