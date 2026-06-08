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

    assert 'data-testid="release-badge"' in text
    assert 'data-testid="release-link"' in text
    assert "v1.0.4" in text
    assert "https://github.com/wyjhfl/project-a-rag-platform/releases/tag/v1.0.4" in text
