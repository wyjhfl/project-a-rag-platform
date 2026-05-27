from __future__ import annotations

import argparse
import re
import shutil
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = PROJECT_DIR.parent / "project-a-rag-platform-public"

SANITIZE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"[A-Z]:\\\\[^\\\\]+\\\\我的学习计划\\\\天空没有极限",
            re.IGNORECASE,
        ),
        "<LOCAL_REPO_ROOT>",
    ),
    (
        re.compile(
            r"[A-Z]:\\[^\\]+\\我的学习计划\\天空没有极限",
            re.IGNORECASE,
        ),
        "<LOCAL_REPO_ROOT>",
    ),
    (
        re.compile(
            r"[A-Z]:/[^/]+/我的学习计划/天空没有极限",
            re.IGNORECASE,
        ),
        "<LOCAL_REPO_ROOT>",
    ),
    (
        re.compile(
            r"/mnt/[a-z]/[^/]+/我的学习计划/天空没有极限",
            re.IGNORECASE,
        ),
        "<LOCAL_REPO_ROOT>",
    ),
    (
        re.compile(r"/home/[a-zA-Z_][a-zA-Z0-9_-]*"),
        "<WSL_HOME>",
    ),
    (
        re.compile(r"[A-Z]:\\\\[^\\\\]*[Dd]ownload", re.IGNORECASE),
        "<LOCAL_DOWNLOAD_DIR>",
    ),
    (
        re.compile(r"[A-Z]:\\[^\\]*[Dd]ownload", re.IGNORECASE),
        "<LOCAL_DOWNLOAD_DIR>",
    ),
    (
        re.compile(r"[A-Z]:/[^/]*[Dd]ownload", re.IGNORECASE),
        "<LOCAL_DOWNLOAD_DIR>",
    ),
]

TEXT_EXTENSIONS: frozenset[str] = frozenset({
    ".md", ".txt", ".json", ".js", ".ts", ".vue", ".css",
    ".html", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sh",
    ".ps1", ".env", ".example", ".gitignore",
})


def sanitize_text(text: str) -> str:
    for pattern, replacement in SANITIZE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


_CACHE_DIRS = frozenset({".ruff_cache", ".pytest_cache", "__pycache__"})


def robust_rmtree(path: Path, max_retries: int = 3) -> None:
    for cache_name in _CACHE_DIRS:
        for cache_dir in path.rglob(cache_name):
            try:
                shutil.rmtree(cache_dir)
            except OSError:
                pass
    for attempt in range(max_retries):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            if attempt < max_retries - 1:
                time.sleep(0.5)
            else:
                raise

FILES_TO_COPY = [
    ".env.example",
    ".env.demo.example",
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
    "docs/A-real-data_adversarial_report.json",
    "docs/A-real-data_bad_cases.md",
    "docs/A-real-data_ragas_report.json",
    "docs/A-real-data_regression_report.json",
    "docs/A-v1.1_API与关键演示说明.md",
    "docs/A-v1.1_教学说明.md",
    "docs/A-v1.1_面试讲法与版本边界说明.md",
    "docs/A-v1.1_验证记录.md",
    "docs/A-v1.1_preflight_2026-05-18.json",
    "docs/A-v1.2_ragas_report.json",
    "docs/A-v1.2_定向优化复盘.md",
    "docs/A-v1.2_bad_case_trace闭环.md",
    "docs/A-v1.2_评测与可观测性说明.md",
    "docs/A-v1.3_provider_manifest.example.json",
    "docs/A-v1.3_provider_acceptance_report.json",
    "docs/A-v1.3_acceptance_report.json",
    "docs/A-v1.3_真实多模态与企业增强验收.md",
    "docs/A-v1.4_provider_acceptance_report_2026-05-19.json",
    "docs/A-v1.4_real_llm_grounding_preflight_deepseek_2026-05-19.json",
    "docs/A-v1.4_真实LLM_Provider稳定性收口与默认模型决策.md",
    "docs/A-v1.5_multimodal_acceptance_report_2026-05-20.json",
    "docs/A-v1.5_paddleocr_linux_final_probe_2026-05-20.json",
    "docs/A-v1.5_bad_cases.md",
    "docs/A-v1.5_真实多模态全链路开启与验收收口.md",
    "docs/A-v1.6_验收中心与演示产品化.md",
    "docs/A-v2.0_frontend_live_preflight_publicchain_2026-05-22.json",
    "docs/A-v2.0_前端验收中心与演示产品化.md",
    "docs/A-v2.1-demo-delivery-review.md",
    "docs/A-v2.2-mimo-provider-reacceptance.md",
    "docs/A-v2.2_bad_cases.md",
    "docs/A-v2.2_provider_acceptance_report_2026-05-23.json",
    "docs/A-v2.2_provider_auth_preflight_2026-05-23.json",
    "docs/A-v2.2_provider_manifest.json",
    "docs/A-v2.3-paddleocr-compatibility-review.md",
    "docs/A-v2.3_bad_cases.md",
    "docs/A-v2.3_paddleocr_compatibility_report_2026-05-23.json",
    "docs/A-v2.3_paddleocr_runtime_preflight_2026-05-23.json",
    "docs/A-v2.4-provider-comparison-review.md",
    "docs/A-v2.4_bad_cases.md",
    "docs/A-v2.4_provider_comparison_report_2026-05-23.json",
    "docs/A-v2.5-demo-assets-review.md",
    "docs/A-v2.6-public-delivery-review.md",
    "docs/A-v2.6_bad_cases.md",
    "docs/A-v2.7-interview-compression-review.md",
    "docs/A-v2.7_bad_cases.md",
    "docs/A-v2.8-portfolio-visual-assets-review.md",
    "docs/A-v2.8_bad_cases.md",
    "docs/A-v2.9-evaluation-quality-review.md",
    "docs/A-v2.9_bad_cases.md",
    "docs/A-v3.0-public-release-verification.md",
    "docs/A-v3.1-public-readability-review.md",
    "docs/A-v3.2-remote-ci-display-review.md",
    "docs/A-v3.3-portfolio-entry-review.md",
    "docs/A-v3.4-resume-delivery-pack.md",
    "docs/A-v3.5-final-remote-audit.md",
    "docs/A-v3.6-public-release-notes.md",
    "docs/A-v4_engineering_baseline_report.md",
    "docs/A-vue-fastapi_preflight_2026-05-17.json",
    "docs/demo_assets_checklist.md",
    "docs/demo_guide.md",
    "docs/demo_script.md",
    "docs/final_delivery_index.md",
    "docs/five_min_demo_route.md",
    "docs/interview_guide.md",
    "docs/interview_pitch_pack.md",
    "docs/public_delivery_checklist.md",
    "scripts/start_demo_stack.ps1",
    "scripts/stop_demo_stack.ps1",
]

DIRECTORIES_TO_COPY = [
    "backend/app",
    "docs/assets/a-v1.1",
    "docs/assets/a-v2.5",
    "data/real_manuals_sanitized",
    "data/seed_docs",
]

SCRIPT_FILES_TO_COPY = [
    "backend/scripts/__init__.py",
    "backend/scripts/compare_retrieval.py",
    "backend/scripts/create_public_release_repo.py",
    "backend/scripts/evaluate_ragas.py",
    "backend/scripts/preflight_multimodal_linux_runtime.py",
    "backend/scripts/preflight_provider_auth.py",
    "backend/scripts/preflight_real_llm_grounding.py",
    "backend/scripts/run_adversarial.py",
    "backend/scripts/run_av13_acceptance.py",
    "backend/scripts/run_av23_paddleocr_compatibility.py",
    "backend/scripts/run_av24_provider_comparison.py",
    "backend/scripts/run_provider_acceptance.py",
    "backend/scripts/run_regression.py",
]

TEST_FILES_TO_COPY = [
    "backend/tests/test_acceptance_overview_api.py",
    "backend/tests/test_api.py",
    "backend/tests/test_av13_acceptance.py",
    "backend/tests/test_av23_paddleocr_compatibility.py",
    "backend/tests/test_av24_provider_comparison.py",
    "backend/tests/test_enterprise_api.py",
    "backend/tests/test_hybrid_retrieval.py",
    "backend/tests/test_public_release_sanitization.py",
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
        robust_rmtree(target)

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
    if source.suffix.lower() in TEXT_EXTENSIONS:
        raw = source.read_text(encoding="utf-8", errors="replace")
        sanitized = sanitize_text(raw)
        target.write_text(sanitized, encoding="utf-8")
    else:
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
    for child in target.rglob("*"):
        if child.is_file() and child.suffix.lower() in TEXT_EXTENSIONS:
            raw = child.read_text(encoding="utf-8", errors="replace")
            sanitized = sanitize_text(raw)
            child.write_text(sanitized, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
