"""Secret scan for Project A RAG Platform.

Scans the project for accidentally committed secrets, API keys,
passwords, and other sensitive data.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

# Patterns that indicate potential secrets
_SECRET_PATTERNS = [
    (r'(?:password|passwd|pwd)\s*[:=]\s*["\'][^"\']{4,}["\']', "hardcoded password"),
    (r'(?:api[_-]?key|apikey)\s*[:=]\s*["\'][^"\']{8,}["\']', "hardcoded API key"),
    (r'(?:secret|token)\s*[:=]\s*["\'][^"\']{8,}["\']', "hardcoded secret/token"),
    (r'(?:aws_access_key_id)\s*[:=]\s*["\']AKIA[0-9A-Z]{16}["\']', "AWS access key"),
    (r'(?:aws_secret_access_key)\s*[:=]\s*["\'][^"\']{20,}["\']', "AWS secret key"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "private key"),
    (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API key pattern"),
    (r'ghp_[a-zA-Z0-9]{36}', "GitHub PAT pattern"),
    (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth token"),
    (r'glpat-[a-zA-Z0-9\-]{20,}', "GitLab PAT"),
]

# Files/directories to skip
_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".pg_deps", "dist",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", "frontend/node_modules",
    "frontend/dist",
}

_SKIP_FILES = {
    ".env.example", ".env.production.example", "acceptance.defaults.json",
    "secret_scan.py",  # Don't scan ourselves
    "test_production_landing.py",  # Contains test fixture keys, not real secrets
}

# Known safe patterns (false positives to ignore)
_SAFE_PATTERNS = [
    "smoke_test_pw_placeholder",
    "project-a@rag-platform.local",
    "your-api-key",
    "your-secret",
    "REPLACE_ME",
    "changeme",
    "example",
    "placeholder",
    "default",
    "project_a_api_key",  # localStorage key name, not a secret
]


def _should_skip_dir(dirname: str) -> bool:
    return dirname in _SKIP_DIRS or dirname.startswith(".")


def _should_skip_file(filename: str) -> bool:
    if filename in _SKIP_FILES:
        return True
    ext = os.path.splitext(filename)[1]
    if ext in {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".png", ".jpg", ".ico"}:
        return True
    return False


def _is_safe_match(line: str) -> bool:
    lower = line.lower()
    return any(s in lower for s in _SAFE_PATTERNS)


def scan_directory(directory: str) -> list[tuple[str, int, str, str]]:
    """Scan directory for secrets. Returns list of (file, line_no, pattern_name, line)."""
    findings = []
    compiled = [(re.compile(p, re.IGNORECASE), name) for p, name in _SECRET_PATTERNS]

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not _should_skip_dir(d)]
        for fname in files:
            if _should_skip_file(fname):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if _is_safe_match(line):
                            continue
                        for pattern, name in compiled:
                            if pattern.search(line):
                                findings.append((fpath, lineno, name, line.strip()))
                                break
            except (OSError, PermissionError):
                continue

    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Secret scan for Project A RAG Platform")
    parser.add_argument("--dir", default=".", help="Directory to scan")
    args = parser.parse_args()

    findings = scan_directory(args.dir)

    if findings:
        print(f"FOUND {len(findings)} potential secret(s):")
        for fpath, lineno, name, line in findings:
            rel = os.path.relpath(fpath, args.dir)
            print(f"  {rel}:{lineno} [{name}]: {line[:80]}")
        sys.exit(2)
    else:
        print("No secrets found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
