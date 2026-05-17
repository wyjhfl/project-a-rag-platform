from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = PROJECT_DIR.parent / "project-a-rag-platform-public"

FILES_TO_COPY = [
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "README.md",
    "docker-compose.yml",
    "pyproject.toml",
    "frontend/index.html",
    "frontend/Dockerfile",
    "frontend/package-lock.json",
    "frontend/package.json",
    "frontend/nginx.conf",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
    "frontend/src/App.vue",
    "frontend/src/api.ts",
    "frontend/src/main.ts",
    "frontend/src/styles.css",
    "prompts/rag_prompt_v0.1.txt",
    "data/seed_qa.json",
    "data/retrieval_cases_v0.2.json",
    "data/eval/adversarial_cases_v0.5.json",
    "data/eval/regression_cases_v0.5.json",
    "data/eval/release_scenarios_v1.json",
    "data/eval/real_adversarial_cases_v1.json",
    "data/eval/real_regression_cases_v1.json",
    "data/uploaded_docs/.gitkeep",
    "docs/A-v1.0_bad_cases.md",
    "docs/A-v1.0_public_feature_audit.md",
    "docs/A-v1.0_public_release.md",
    "docs/A-v1.0_测试结果.md",
]

DIRECTORIES_TO_COPY = [
    "backend/app",
    "data/real_manuals_sanitized",
    "data/seed_docs",
]

SCRIPT_FILES_TO_COPY = [
    "backend/scripts/__init__.py",
    "backend/scripts/compare_retrieval.py",
    "backend/scripts/create_public_release_repo.py",
    "backend/scripts/evaluate_ragas.py",
    "backend/scripts/run_adversarial.py",
    "backend/scripts/run_regression.py",
]

TEST_FILES_TO_COPY = [
    "backend/tests/test_api.py",
    "backend/tests/test_enterprise_api.py",
    "backend/tests/test_hybrid_retrieval.py",
    "backend/tests/test_rag_security.py",
    "backend/tests/test_release_scenarios.py",
    "backend/tests/test_ticket_workflow.py",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=str(DEFAULT_TARGET))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if target == PROJECT_DIR:
        raise ValueError("Target directory must be different from the source repository.")

    if target.exists():
        if not args.force:
            raise FileExistsError(f"Target already exists: {target}")
        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    for relative_path in FILES_TO_COPY:
        _copy_file(relative_path, target)

    for relative_path in SCRIPT_FILES_TO_COPY + TEST_FILES_TO_COPY:
        _copy_file(relative_path, target)

    for relative_path in DIRECTORIES_TO_COPY:
        _copy_directory(relative_path, target)

    workflow_dir = target / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    _copy_file(".github/workflows/ci.yml", target)

    print(f"public_release_repo={target}")
    return 0


def _copy_file(relative_path: str, target_root: Path) -> None:
    source = PROJECT_DIR / relative_path
    if not source.exists():
        raise FileNotFoundError(f"Missing required file: {source}")
    target = target_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _copy_directory(relative_path: str, target_root: Path) -> None:
    source = PROJECT_DIR / relative_path
    if not source.exists():
        raise FileNotFoundError(f"Missing required directory: {source}")
    target = target_root / relative_path
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "node_modules",
            "dist",
            "*.pyc",
            "*.pyo",
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
