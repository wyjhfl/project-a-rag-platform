import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.scripts.run_av23_paddleocr_compatibility import build_report  # noqa: E402


def test_build_report_marks_runtime_incompatible_boundary():
    report = build_report(
        current_preflight={
            "summary": {
                "docker_daemon_ready": False,
                "wsl_repo_mounted": True,
                "wsl_python_ready": True,
                "wsl_packages_ready": True,
                "wsl_ocr_runtime_ready": False,
                "recommended_path": "wsl_runtime_incompatible",
            },
            "wsl": {
                "package_flags": {"numpy": True, "paddle": True, "paddleocr": True},
                "ocr_probe": {
                    "ocr_error": {
                        "message": "ConvertPirAttribute2RuntimeAttribute",
                    }
                },
            },
        },
        final_probe={
            "attempts": [
                {
                    "name": "flags_enable_pir_api_0",
                    "result": "runtime_incompatible",
                    "error_type": "NotImplementedError",
                    "error_contains": "ConvertPirAttribute2RuntimeAttribute",
                }
            ]
        },
    )

    assert report["summary"]["runtime_incompatible_confirmed"] is True
    assert report["decision"]["status"] == "formal_boundary"


def test_build_report_marks_candidate_when_everything_passes():
    report = build_report(
        current_preflight={
            "summary": {
                "docker_daemon_ready": True,
                "wsl_repo_mounted": True,
                "wsl_python_ready": True,
                "wsl_packages_ready": True,
                "wsl_ocr_runtime_ready": True,
                "recommended_path": "docker_or_wsl",
            },
            "wsl": {
                "package_flags": {"numpy": True, "paddle": True, "paddleocr": True},
                "ocr_probe": {"ocr_runtime_ready": True},
            },
        },
        final_probe={"attempts": []},
    )

    assert report["decision"]["status"] == "candidate_for_reenable"
