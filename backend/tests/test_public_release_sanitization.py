from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_DIR))

from backend.scripts.create_public_release_repo import sanitize_text  # noqa: E402


def test_sanitize_windows_backslash_repo_root():
    raw = "D:\\myrepo\\我的学习计划\\天空没有极限\\project-a-rag-platform"
    result = sanitize_text(raw)
    assert "myrepo" not in result
    assert "<LOCAL_REPO_ROOT>" in result


def test_sanitize_windows_forward_slash_repo_root():
    raw = "D:/myrepo/我的学习计划/天空没有极限/project-a-rag-platform"
    result = sanitize_text(raw)
    assert "myrepo" not in result
    assert "<LOCAL_REPO_ROOT>" in result


def test_sanitize_wsl_home_path():
    raw = "/home/testuser/.local/bin:/usr/bin"
    result = sanitize_text(raw)
    assert "testuser" not in result
    assert "<WSL_HOME>" in result


def test_sanitize_download_dir_backslash():
    raw = "D:\\UserDownloads\\manuals\\device.pdf"
    result = sanitize_text(raw)
    assert "UserDownloads" not in result
    assert "<LOCAL_DOWNLOAD_DIR>" in result


def test_sanitize_download_dir_forward_slash():
    raw = "D:/UserDownloads/manuals/device.pdf"
    result = sanitize_text(raw)
    assert "UserDownloads" not in result
    assert "<LOCAL_DOWNLOAD_DIR>" in result


def test_sanitize_json_preserves_structure():
    payload = {
        "repo_path": "D:\\myrepo\\我的学习计划\\天空没有极限\\project-a-rag-platform",
        "wsl_home": "/home/testuser/project_a_wsl_libgomp",
        "download": "D:\\UserDownloads\\docs",
        "count": 42,
        "nested": {"inner_path": "/home/testuser/.local/bin"},
    }
    raw_json = json.dumps(payload, ensure_ascii=False)
    sanitized = sanitize_text(raw_json)
    parsed = json.loads(sanitized)
    assert parsed["count"] == 42
    assert "<LOCAL_REPO_ROOT>" in parsed["repo_path"]
    assert "myrepo" not in parsed["repo_path"]
    assert parsed["wsl_home"] == "<WSL_HOME>/project_a_wsl_libgomp"
    assert "<LOCAL_DOWNLOAD_DIR>" in parsed["download"]
    assert "UserDownloads" not in parsed["download"]
    assert parsed["nested"]["inner_path"] == "<WSL_HOME>/.local/bin"


def test_sanitize_no_match_returns_original():
    raw = "这是一段普通文本，没有敏感路径。"
    result = sanitize_text(raw)
    assert result == raw


def test_sanitize_mixed_patterns():
    raw = (
        "项目: D:\\myrepo\\我的学习计划\\天空没有极限, "
        "WSL: /home/testuser, "
        "下载: D:\\UserDownloads"
    )
    result = sanitize_text(raw)
    assert "myrepo" not in result
    assert "testuser" not in result
    assert "UserDownloads" not in result
    assert "<LOCAL_REPO_ROOT>" in result
    assert "<WSL_HOME>" in result
    assert "<LOCAL_DOWNLOAD_DIR>" in result


def test_sanitize_wsl_mount_repo_path():
    raw = "/mnt/c/myrepo/我的学习计划/天空没有极限/project-a-rag-platform"
    result = sanitize_text(raw)
    assert "myrepo" not in result
    assert "<LOCAL_REPO_ROOT>" in result


def test_sanitize_wsl_home_generic():
    raw = "/home/some_user/project_a_wsl_libgomp/usr/lib"
    result = sanitize_text(raw)
    assert "some_user" not in result
    assert "<WSL_HOME>" in result


def test_sanitize_generic_windows_repo_root():
    raw = "E:\\anotherrepo\\我的学习计划\\天空没有极限\\project-a-rag-platform"
    result = sanitize_text(raw)
    assert "anotherrepo" not in result
    assert "<LOCAL_REPO_ROOT>" in result


def test_sanitize_generic_download_dir():
    raw = "E:\\NetDownloads\\manuals\\device.pdf"
    result = sanitize_text(raw)
    assert "NetDownloads" not in result
    assert "<LOCAL_DOWNLOAD_DIR>" in result


def test_sanitize_generic_wsl_mount_repo():
    raw = "/mnt/d/anotheruser/我的学习计划/天空没有极限/project-a-rag-platform"
    result = sanitize_text(raw)
    assert "anotheruser" not in result
    assert "<LOCAL_REPO_ROOT>" in result
