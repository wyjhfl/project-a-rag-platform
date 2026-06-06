from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CURRENT_PREFLIGHT = (
    PROJECT_DIR / "docs" / f"A-v2.3_paddleocr_runtime_preflight_{date.today().isoformat()}.json"
)
DEFAULT_FINAL_PROBE = PROJECT_DIR / "docs" / "A-v1.5_paddleocr_linux_final_probe_2026-05-20.json"
DEFAULT_OUTPUT = (
    PROJECT_DIR / "docs" / f"A-v2.3_paddleocr_compatibility_report_{date.today().isoformat()}.json"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-preflight", default=str(DEFAULT_CURRENT_PREFLIGHT))
    parser.add_argument("--final-probe", default=str(DEFAULT_FINAL_PROBE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    current_preflight = read_json(Path(args.current_preflight))
    final_probe = read_json(Path(args.final_probe))
    report = build_report(current_preflight=current_preflight, final_probe=final_probe)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def build_report(*, current_preflight: dict[str, Any], final_probe: dict[str, Any]) -> dict[str, Any]:
    matrix = build_matrix(current_preflight=current_preflight, final_probe=final_probe)
    summary = summarize_matrix(matrix)
    return {
        "version": "A-v2.3",
        "generated_on": date.today().isoformat(),
        "component": "paddleocr_compatibility",
        "summary": summary,
        "decision": build_decision(summary),
        "matrix": matrix,
        "evidence": {
            "current_preflight_summary": current_preflight.get("summary", {}),
            "final_probe_environment": final_probe.get("environment", {}),
            "final_probe_conclusion": final_probe.get("final_conclusion", {}),
        },
    }


def build_matrix(*, current_preflight: dict[str, Any], final_probe: dict[str, Any]) -> list[dict[str, Any]]:
    current_summary = current_preflight.get("summary", {})
    wsl = current_preflight.get("wsl", {})
    attempts = final_probe.get("attempts", [])
    matrix = [
        {
            "name": "docker_daemon",
            "status": "passed" if current_summary.get("docker_daemon_ready") else "blocked",
            "blocker_type": "" if current_summary.get("docker_daemon_ready") else "docker_daemon_unavailable",
            "detail": "Docker daemon can be used for an isolated OCR runtime."
            if current_summary.get("docker_daemon_ready")
            else "Docker client or compose may exist, but daemon is not ready.",
        },
        {
            "name": "wsl_python_and_packages",
            "status": "passed" if current_summary.get("wsl_packages_ready") else "blocked",
            "blocker_type": "" if current_summary.get("wsl_packages_ready") else "wsl_package_bootstrap_required",
            "detail": {
                "repo_mounted": current_summary.get("wsl_repo_mounted"),
                "python_ready": current_summary.get("wsl_python_ready"),
                "package_flags": wsl.get("package_flags", {}),
            },
        },
        {
            "name": "wsl_paddleocr_real_runtime",
            "status": "passed" if current_summary.get("wsl_ocr_runtime_ready") else "blocked",
            "blocker_type": ""
            if current_summary.get("wsl_ocr_runtime_ready")
            else current_summary.get("recommended_path", "wsl_runtime_debug"),
            "detail": wsl.get("ocr_probe", {}),
        },
    ]
    for attempt in attempts:
        matrix.append(
            {
                "name": f"final_probe_{attempt.get('name', 'unknown')}",
                "status": "passed" if attempt.get("result") == "passed" else "blocked",
                "blocker_type": attempt.get("result", "unknown"),
                "detail": {
                    "error_type": attempt.get("error_type", ""),
                    "error_contains": attempt.get("error_contains", ""),
                },
            }
        )
    return matrix


def summarize_matrix(matrix: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    blocker_counts: dict[str, int] = {}
    for item in matrix:
        status = str(item.get("status", "unknown"))
        blocker = str(item.get("blocker_type", ""))
        status_counts[status] = status_counts.get(status, 0) + 1
        if blocker:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
    runtime_incompatible = (
        blocker_counts.get("wsl_runtime_incompatible", 0) > 0
        or blocker_counts.get("runtime_incompatible", 0) > 0
    )
    return {
        "check_count": len(matrix),
        "status_counts": status_counts,
        "blocker_type_counts": blocker_counts,
        "runtime_incompatible_confirmed": runtime_incompatible,
    }


def build_decision(summary: dict[str, Any]) -> dict[str, str]:
    if summary.get("runtime_incompatible_confirmed"):
        return {
            "status": "formal_boundary",
            "recommendation": "Keep PaddleOCR out of the default demo path and document it as a runtime compatibility boundary.",
            "next_step": "Only continue if a clean Docker/Linux runtime matrix is allocated as a separate spike.",
        }
    if summary.get("status_counts", {}).get("passed", 0) == summary.get("check_count", 0):
        return {
            "status": "candidate_for_reenable",
            "recommendation": "PaddleOCR runtime is ready and can be considered for guarded real-backend acceptance.",
            "next_step": "Run multimodal acceptance with PaddleOCR enabled.",
        }
    return {
        "status": "needs_more_probe",
        "recommendation": "Current evidence is not enough to decide; run a targeted runtime probe.",
        "next_step": "Refresh linux runtime preflight and inspect blocker_type.",
    }


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
