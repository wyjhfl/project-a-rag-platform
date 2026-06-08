import json
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
APP_SHELL = FRONTEND_SRC / "components" / "AppShell.vue"
VISIBLE_SOURCE_GLOBS = ("*.vue", "*.ts")
EXCLUDED_FILES = {"generated.ts"}
MOJIBAKE_MARKERS = (
    "�",
    "锛",
    "銆",
    "€",
    "浼",
    "绯",
    "楠",
    "瀹",
    "鎶",
    "鎵",
    "鍒",
    "閰",
    "鐘",
    "彂",
    "妯",
    "鏌",
    "涓",
    "勭",
)


def _visible_frontend_files() -> list[Path]:
    files: list[Path] = []
    for pattern in VISIBLE_SOURCE_GLOBS:
        files.extend(FRONTEND_SRC.rglob(pattern))
    return sorted(path for path in files if path.name not in EXCLUDED_FILES)


def test_frontend_visible_copy_has_no_mojibake_markers() -> None:
    findings: list[str] = []
    for path in _visible_frontend_files():
        text = path.read_text(encoding="utf-8")
        for marker in MOJIBAKE_MARKERS:
            if marker in text:
                rel = path.relative_to(FRONTEND_SRC.parents[1])
                findings.append(f"{rel}: contains {marker!r}")
                break

    assert findings == []


def test_app_shell_exposes_current_release_entrypoint() -> None:
    text = APP_SHELL.read_text(encoding="utf-8")
    release_text = (FRONTEND_SRC / "release.ts").read_text(encoding="utf-8")

    assert 'data-testid="release-badge"' in text
    assert 'data-testid="release-link"' in text
    assert "RELEASE_VERSION" in text
    assert "RELEASE_URL" in text
    assert "v1.0.4" in release_text
    assert "https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.4" in release_text


def test_app_shell_uses_central_release_metadata() -> None:
    text = APP_SHELL.read_text(encoding="utf-8")
    release_file = FRONTEND_SRC / "release.ts"

    assert release_file.exists()
    release_text = release_file.read_text(encoding="utf-8")
    assert "export const RELEASE_VERSION" in release_text
    assert "export const RELEASE_URL" in release_text
    assert "import { RELEASE_URL, RELEASE_VERSION } from '../release'" in text
    assert "const releaseUrl =" not in text


def test_system_status_page_has_stable_release_and_empty_state_selectors() -> None:
    text = (FRONTEND_SRC / "pages" / "SystemStatusPage.vue").read_text(encoding="utf-8")

    assert 'data-testid="healthz-version"' in text
    assert 'data-testid="readyz-version"' in text
    assert 'data-testid="legacy-health-version"' in text
    assert 'data-testid="system-status-version"' in text
    assert 'data-testid="system-release-link"' in text
    assert "import { RELEASE_URL } from '../release'" in text
    assert "function displayValue" in text
    assert "function displayList" in text
    assert "\u2014" in text


def test_jobs_page_exposes_management_controls() -> None:
    text = (FRONTEND_SRC / "pages" / "JobsPage.vue").read_text(encoding="utf-8")

    assert "cancelJob" in text
    assert 'data-testid="job-status-filter"' in text
    assert 'data-testid="job-summary-total"' in text
    assert 'data-testid="job-summary-active"' in text
    assert 'data-testid="job-summary-failed"' in text
    assert 'data-testid="job-cancel-button"' in text
    assert 'data-testid="jobs-list-error"' in text
    assert 'data-testid="job-search-error"' in text
    assert "safeJobs" in text
    assert "Array.isArray(data)" in text
    assert "filteredJobs" in text
    assert "canCancelJob" in text


def test_jobs_page_preserves_element_plus_on_demand_imports() -> None:
    text = (FRONTEND_SRC / "pages" / "JobsPage.vue").read_text(encoding="utf-8")
    plugin_text = (FRONTEND_SRC / "plugins" / "element-plus.ts").read_text(encoding="utf-8")

    assert "from 'element-plus'" not in text
    assert "from '../plugins/element-plus'" in text
    assert "element-plus/es/components/message/index.mjs" in plugin_text


def test_frontend_docker_and_e2e_use_actual_api_base() -> None:
    project_root = FRONTEND_SRC.parents[1]
    dockerfile = project_root / "frontend" / "Dockerfile"
    dockerignore = project_root / ".dockerignore"
    compose = (project_root / "docker-compose.yml").read_text(encoding="utf-8")
    demo_compose = (project_root / "docker-compose.demo.yml").read_text(encoding="utf-8")
    e2e_runner = (project_root / "scripts" / "run_full_e2e_demo.ps1").read_text(encoding="utf-8")

    assert dockerfile.exists()
    assert dockerignore.exists()
    dockerfile_text = dockerfile.read_text(encoding="utf-8")
    dockerignore_text = dockerignore.read_text(encoding="utf-8")
    assert "ARG NODE_IMAGE=node:20-alpine" in dockerfile_text
    assert "ARG NGINX_IMAGE=nginx:1.27-alpine" in dockerfile_text
    assert "ARG VITE_API_BASE" in dockerfile_text
    assert "ENV VITE_API_BASE=$VITE_API_BASE" in dockerfile_text
    assert "VITE_API_BASE:" in compose
    assert "VITE_API_BASE_URL" not in compose
    assert "VITE_API_BASE:" in demo_compose
    assert "VITE_API_BASE_URL" not in demo_compose
    assert '$env:VITE_API_BASE = "http://127.0.0.1:8000"' in e2e_runner
    assert '$env:CORS_ALLOW_ORIGINS = "http://127.0.0.1:4173,http://localhost:4173"' in e2e_runner
    assert "frontend/node_modules/" in dockerignore_text
    assert "frontend/dist/" in dockerignore_text
    assert "frontend/test-results/" in dockerignore_text


def test_app_supports_hash_deep_links_and_accessible_nav_state() -> None:
    app_text = (FRONTEND_SRC / "App.vue").read_text(encoding="utf-8")
    shell_text = APP_SHELL.read_text(encoding="utf-8")

    assert "function tabFromHash" in app_text
    assert "function tabToHash" in app_text
    assert "window.addEventListener('hashchange'" in app_text
    assert "window.removeEventListener('hashchange'" in app_text
    assert "window.history.replaceState" in app_text
    assert "localStorage.setItem(TAB_STORAGE_KEY" in app_text
    assert ':aria-current="activeTab === item.key ? \'page\' : undefined"' in shell_text


def test_openapi_generation_is_ci_guarded() -> None:
    project_root = FRONTEND_SRC.parents[1]
    export_script = project_root / "scripts" / "export_openapi.py"
    python_runner = project_root / "scripts" / "run_python.mjs"
    defaults_example = project_root / "scripts" / "acceptance.defaults.example.json"
    package_json = (project_root / "frontend" / "package.json").read_text(encoding="utf-8")
    ci = (project_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    final_acceptance = (project_root / "scripts" / "final_production_acceptance.ps1").read_text(encoding="utf-8")

    assert export_script.exists()
    assert python_runner.exists()
    assert defaults_example.exists()
    script_text = export_script.read_text(encoding="utf-8")
    runner_text = python_runner.read_text(encoding="utf-8")
    assert "create_app" in script_text
    assert "docs/openapi.json" in script_text
    assert '"api:openapi"' in package_json
    assert "run_python.mjs" in package_json
    assert '"api:types"' in package_json
    assert '"api:check"' in package_json
    assert "PROJECT_A_PYTHON_EXE" in runner_text
    assert "acceptance.defaults.json" in runner_text
    assert "WindowsApps" in runner_text
    assert "npm --prefix frontend run api:check" in ci
    assert "python -m ruff check backend scripts" in ci
    assert "git diff --exit-code docs/openapi.json frontend/src/api/generated.ts" in ci
    assert "api:check" in final_acceptance
    assert "$env:PROJECT_A_PYTHON_EXE = $PythonExe" in final_acceptance
    assert "git diff --exit-code docs/openapi.json frontend/src/api/generated.ts" in final_acceptance


def test_job_create_response_is_strongly_typed_in_openapi() -> None:
    project_root = FRONTEND_SRC.parents[1]
    openapi = json.loads((project_root / "docs" / "openapi.json").read_text(encoding="utf-8"))

    job_schema = openapi["components"]["schemas"]["JobCreateResponse"]["properties"]["job"]
    assert job_schema == {"$ref": "#/components/schemas/JobRecord"}


def test_frontend_api_types_are_generated_schema_aliases() -> None:
    types_text = (FRONTEND_SRC / "api" / "types.ts").read_text(encoding="utf-8")

    assert "import type { components" in types_text
    assert "from './generated'" in types_text
    assert "export type JobRecord = ApiSchema<'JobRecord'>" in types_text
    assert "export type ChatResponse = ApiSchema<'ChatResponse'>" in types_text
    assert 'export interface JobRecord' not in types_text
    assert 'export interface ChatResponse' not in types_text


def test_api_client_parses_unified_error_payload_and_formats_cleanly() -> None:
    client_text = (FRONTEND_SRC / "api" / "client.ts").read_text(encoding="utf-8")

    assert "function extractApiErrorPayload" in client_text
    assert "const nested = data?.error" in client_text
    assert "nested?.message" in client_text
    assert "nested?.code" in client_text
    assert "nested?.request_id" in client_text
    assert "Validation failed" in client_text
    assert "parts.join(' " + chr(0x2014) + " ')" in client_text
    assert chr(0x9225) not in client_text
    assert chr(0xFFFD) not in client_text
