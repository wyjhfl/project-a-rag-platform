from __future__ import annotations

import json
import os
import subprocess
from argparse import ArgumentParser
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    PROJECT_DIR / "docs" / f"A-v1.5_multimodal_linux_runtime_{date.today().isoformat()}.json"
)
WSL_DISTRO = "Ubuntu-24.04"
WSL_REPO_PATH = os.environ.get(
    "WSL_PROJECT_A_REPO_PATH",
    "/mnt/e/project-a-rag-platform",
)
WSL_USER_LIBGOMP_PATH = os.environ.get(
    "WSL_PROJECT_A_LIBGOMP_PATH",
    "$HOME/project_a_wsl_libgomp/usr/lib/x86_64-linux-gnu",
)


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--version", default="A-v1.5")
    args = parser.parse_args()

    report = {
        "version": args.version,
        "generated_on": date.today().isoformat(),
        "docker": probe_docker(),
        "wsl": probe_wsl(),
    }
    report["summary"] = build_summary(report)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def probe_docker() -> dict[str, Any]:
    version_probe = run_command(["docker", "version"], timeout_seconds=60)
    config_probe = run_command(["docker", "compose", "config"], timeout_seconds=60)
    daemon_ready = version_probe["returncode"] == 0
    compose_config_ready = config_probe["returncode"] == 0
    return {
        "client_available": True,
        "daemon_ready": daemon_ready,
        "compose_config_ready": compose_config_ready,
        "version_error": summarize_stderr(version_probe),
        "compose_config_error": "" if compose_config_ready else summarize_stderr(config_probe),
    }


def probe_wsl() -> dict[str, Any]:
    distro_probe = run_command(["wsl", "-l", "-v"], timeout_seconds=60)
    python_probe = run_command(
        ["wsl", "-d", WSL_DISTRO, "python3", "-c", "import sys; print(sys.version)"],
        timeout_seconds=60,
    )
    ensurepip_probe = run_command(
        ["wsl", "-d", WSL_DISTRO, "python3", "-m", "ensurepip", "--version"],
        timeout_seconds=60,
    )
    package_probe = run_command(
        [
            "wsl",
            "-d",
            WSL_DISTRO,
            "python3",
            "-c",
            (
                "import importlib.util as u; "
                "mods=['cv2','numpy','paddle','paddleocr','paddlex']; "
                "[print(f'{m}={bool(u.find_spec(m))}') for m in mods]"
            ),
        ],
        timeout_seconds=60,
    )
    repo_probe = run_command(
        ["wsl", "-d", WSL_DISTRO, "python3", "-c", "from pathlib import Path; print(Path.cwd())"],
        timeout_seconds=60,
    )
    libgomp_probe = run_command(
        [
            "wsl",
            "-d",
            WSL_DISTRO,
            "python3",
            "-c",
            (
                "from pathlib import Path; "
                f"print(Path('{WSL_USER_LIBGOMP_PATH}').joinpath('libgomp.so.1.0.0').exists())"
            ),
        ],
        timeout_seconds=60,
    )

    ocr_env = {"PYTHONPATH": "backend"}
    if "true" in libgomp_probe["stdout"].lower():
        ocr_env["LD_LIBRARY_PATH"] = WSL_USER_LIBGOMP_PATH
    ocr_probe = run_command(
        ["wsl", "-d", WSL_DISTRO, "python3", "backend/scripts/wsl_paddleocr_probe.py"],
        timeout_seconds=300,
        extra_env=ocr_env,
    )

    distro_text = normalize_wsl_text(distro_probe["stdout"])
    package_flags = parse_bool_lines(package_probe["stdout"])
    ocr_payload = parse_json_output(ocr_probe["stdout"])
    return {
        "distro": WSL_DISTRO,
        "distro_listed": distro_probe["returncode"] == 0 and WSL_DISTRO in distro_text,
        "python_ready": python_probe["returncode"] == 0,
        "python_version": python_probe["stdout"].splitlines()[0].strip() if python_probe["stdout"] else "",
        "repo_mounted": repo_probe["returncode"] == 0 and "/project-a-rag-platform" in repo_probe["stdout"],
        "repo_mount_error": summarize_stderr(repo_probe),
        "ensurepip_ready": ensurepip_probe["returncode"] == 0,
        "ensurepip_error": summarize_stderr(ensurepip_probe),
        "user_libgomp_ready": "true" in libgomp_probe["stdout"].lower(),
        "user_libgomp_error": summarize_stderr(libgomp_probe),
        "package_flags": package_flags,
        "ocr_probe": ocr_payload if ocr_payload else {"error": summarize_stderr(ocr_probe)},
        "warnings": collect_wsl_warnings(
            distro_probe, python_probe, ensurepip_probe, package_probe, repo_probe, libgomp_probe, ocr_probe
        ),
    }


def build_summary(report: dict[str, Any]) -> dict[str, Any]:
    docker = report["docker"]
    wsl = report["wsl"]
    packages = wsl["package_flags"]
    packages_ready = all(packages.get(name, False) for name in ["numpy", "paddle", "paddleocr"])
    ocr_runtime_ready = bool(wsl.get("ocr_probe", {}).get("ocr_runtime_ready", False))
    recommended_path = "wsl_bootstrap"
    if docker["daemon_ready"]:
        recommended_path = "docker_or_wsl"
    if wsl["repo_mounted"] and wsl["python_ready"] and packages_ready:
        recommended_path = "wsl_runtime_ready"
    if wsl["repo_mounted"] and wsl["python_ready"] and packages_ready and not ocr_runtime_ready:
        recommended_path = classify_wsl_runtime_blocker(wsl.get("ocr_probe", {}))
    return {
        "docker_daemon_ready": docker["daemon_ready"],
        "wsl_repo_mounted": wsl["repo_mounted"],
        "wsl_python_ready": wsl["python_ready"],
        "wsl_packages_ready": packages_ready,
        "wsl_ocr_runtime_ready": ocr_runtime_ready,
        "recommended_path": recommended_path,
    }


def run_command(
    command: list[str], timeout_seconds: int, extra_env: dict[str, str] | None = None
) -> dict[str, Any]:
    effective_command = command
    if extra_env:
        env_parts = [f"{key}={value}" for key, value in extra_env.items()]
        effective_command = command[:3] + ["env", *env_parts] + command[3:]
    completed = subprocess.run(
        effective_command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=False,
        timeout=timeout_seconds,
    )
    return {
        "returncode": completed.returncode,
        "stdout": decode_output(completed.stdout),
        "stderr": decode_output(completed.stderr),
    }


def summarize_stderr(probe: dict[str, Any], limit: int = 500) -> str:
    text = (probe.get("stderr") or probe.get("stdout") or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit // 2] + "\n...\n" + text[-limit // 2 :]


def parse_bool_lines(stdout: str) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        flags[name.strip()] = value.strip().lower() == "true"
    return flags


def parse_json_output(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        lines = [line for line in text.splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {}


def classify_wsl_runtime_blocker(ocr_probe: dict[str, Any]) -> str:
    text = json.dumps(ocr_probe, ensure_ascii=False).lower()
    if "libgomp.so.1" in text:
        return "wsl_shared_lib_fix"
    if "convertpirattribute2runtimeattribute" in text:
        return "wsl_runtime_incompatible"
    if "no module named ensurepip" in text:
        return "wsl_bootstrap"
    return "wsl_runtime_debug"


def decode_output(raw: bytes | None) -> str:
    if not raw:
        return ""
    for encoding in ("utf-8", "gbk", "utf-16le"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()


def normalize_wsl_text(text: str) -> str:
    return text.replace("\x00", "")


def collect_wsl_warnings(*probes: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for probe in probes:
        combined = "\n".join(part for part in [probe.get("stdout", ""), probe.get("stderr", "")] if part)
        if "Failed to translate" in combined and "wsl_path_translate_noise" not in seen:
            seen.append("wsl_path_translate_noise")
        if "localhost" in combined and "wsl_localhost_forwarding_warning" not in seen:
            seen.append("wsl_localhost_forwarding_warning")
    return seen


if __name__ == "__main__":
    raise SystemExit(main())
