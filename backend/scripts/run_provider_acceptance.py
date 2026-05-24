from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_DIR / "docs" / "A-v1.3_provider_manifest.example.json"
DEFAULT_OUTPUT = PROJECT_DIR / "docs" / "A-v1.3_provider_acceptance_report.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--version", default="")
    parser.add_argument(
        "--dotenv-override",
        action="store_true",
        help="Load .env over existing process environment variables before resolving default_env.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_DIR / ".env", override=args.dotenv_override)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    providers = manifest.get("providers", [])
    if not providers:
        raise ValueError("Provider manifest must contain at least one provider.")

    results = [run_provider_probe(entry) for entry in providers]
    version = args.version or manifest.get("version") or infer_report_version(Path(args.output))
    report = {
        "version": version,
        "generated_on": date.today().isoformat(),
        "summary": build_provider_summary(results),
        "results": results,
    }
    output_path = Path(args.output)
    output_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(output_text, encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def run_provider_probe(entry: dict[str, Any]) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "backend"

    runtime = {"name": entry["name"]}
    if entry.get("from_env"):
        runtime.update(
            {
                "provider": env.get("LLM_PROVIDER", ""),
                "model": env.get("LLM_MODEL", ""),
                "base_url": env.get("LLM_BASE_URL", ""),
            }
        )
    else:
        runtime.update(
            {
                "provider": str(entry.get("provider", "")),
                "model": str(entry.get("model", "")),
                "base_url": str(entry.get("base_url", "")),
            }
        )
        env["LLM_PROVIDER"] = runtime["provider"]
        env["LLM_MODEL"] = runtime["model"]
        env["LLM_BASE_URL"] = runtime["base_url"]
        api_key = resolve_api_key(entry, env)
        if api_key:
            env["LLM_API_KEY"] = api_key
        else:
            env["LLM_API_KEY"] = ""

    command = [
        sys.executable,
        "backend/scripts/preflight_real_llm_grounding.py",
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = parse_probe_payload(completed.stdout, completed.stderr)
    return summarize_provider_result(runtime, payload, completed.returncode)


def resolve_api_key(entry: dict[str, Any], env: dict[str, str]) -> str:
    api_key_env = str(entry.get("api_key_env", "")).strip()
    if api_key_env:
        return env.get(api_key_env, "")
    return str(entry.get("api_key", ""))


def parse_probe_payload(stdout: str, stderr: str) -> dict[str, Any]:
    text = stdout.strip()
    if text:
        return json.loads(text)
    return {
        "runtime": {},
        "checks": [],
        "critical_failures": [
            {
                "name": "probe_execution",
                "reason": stderr.strip() or "empty output",
            }
        ],
    }


def summarize_provider_result(
    runtime: dict[str, Any],
    payload: dict[str, Any],
    returncode: int,
) -> dict[str, Any]:
    checks = {item["name"]: item for item in payload.get("checks", [])}
    direct_check = checks.get("direct_llm_connected", {"passed": False, "detail": {}})
    grounded_check = checks.get("chat_grounded_llm", {"passed": False, "detail": {}})
    critical_failures = payload.get("critical_failures", [])
    status = classify_provider_result(
        direct_passed=bool(direct_check.get("passed")),
        grounded_passed=bool(grounded_check.get("passed")),
    )
    blocker_type = determine_blocker_type(
        status=status,
        critical_failures=critical_failures,
    )
    return {
        "name": runtime.get("name", ""),
        "runtime": {
            **runtime,
            **payload.get("runtime", {}),
        },
        "status": status,
        "blocker_type": blocker_type,
        "returncode": returncode,
        "direct_llm_connected": bool(direct_check.get("passed")),
        "chat_grounded_llm": bool(grounded_check.get("passed")),
        "accepted_attempt": grounded_check.get("detail", {}).get("accepted_attempt"),
        "warnings": payload.get("warnings", []),
        "critical_failures": critical_failures,
    }


def classify_provider_result(*, direct_passed: bool, grounded_passed: bool) -> str:
    if grounded_passed:
        return "accepted"
    if direct_passed:
        return "unstable"
    return "blocked"


def build_provider_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"accepted": 0, "unstable": 0, "blocked": 0}
    blocker_counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        blocker_type = str(result.get("blocker_type", ""))
        if blocker_type:
            blocker_counts[blocker_type] = blocker_counts.get(blocker_type, 0) + 1
    return {
        "provider_count": len(results),
        "accepted_count": counts["accepted"],
        "unstable_count": counts["unstable"],
        "blocked_count": counts["blocked"],
        "blocker_type_counts": blocker_counts,
    }


def infer_report_version(output_path: Path) -> str:
    stem = output_path.stem
    if stem.startswith("A-v") and "_" in stem:
        return stem.split("_", 1)[0]
    return "A-v1.3"


def determine_blocker_type(
    *,
    status: str,
    critical_failures: list[dict[str, Any]],
) -> str:
    if status == "accepted":
        return "accepted"
    if status == "unstable":
        return "grounded_rejection"

    reasons = " ".join(
        str(item.get("reason", "")).lower()
        for item in critical_failures
    )
    if "invalid_api_key" in reasons or "incorrect api key" in reasons or "401" in reasons:
        return "auth_invalid"
    if "llm is not enabled" in reasons or "not configured" in reasons:
        return "config_missing"
    if "timed out" in reasons or "timeout" in reasons:
        return "timeout"
    if "http 429" in reasons or "rate limit" in reasons:
        return "rate_limited"
    if "http 5" in reasons or "server error" in reasons or "bad gateway" in reasons:
        return "provider_server_error"
    if "http 4" in reasons:
        return "request_rejected"
    if "empty output" in reasons or "probe_execution" in reasons:
        return "probe_execution_failed"
    return "connectivity_or_runtime_error"


if __name__ == "__main__":
    raise SystemExit(main())
