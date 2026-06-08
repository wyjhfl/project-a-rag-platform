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
