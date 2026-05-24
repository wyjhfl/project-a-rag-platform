from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PROJECT_DIR / "docs" / "A-v1.4_provider_manifest.json"
DEFAULT_OUTPUT = PROJECT_DIR / "docs" / f"A-v1.4_provider_auth_preflight_{date.today().isoformat()}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--dotenv-override",
        action="store_true",
        help="Load .env over existing process environment variables.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_DIR / ".env", override=args.dotenv_override)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    providers = manifest.get("providers", [])
    if not providers:
        raise ValueError("Provider manifest must contain at least one provider.")

    results = [probe_provider(entry) for entry in providers]
    report = {
        "version": manifest.get("version") or "A-v1.4",
        "generated_on": date.today().isoformat(),
        "summary": build_summary(results),
        "results": results,
    }
    output_path = Path(args.output)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


def probe_provider(entry: dict[str, Any]) -> dict[str, Any]:
    runtime = build_runtime(entry)
    api_key = resolve_api_key(entry)
    if not runtime["base_url"]:
        return build_result(runtime, "config_missing", auth_ok=False, chat_ok=False, detail="LLM_BASE_URL is empty.")
    if not runtime["model"]:
        return build_result(runtime, "config_missing", auth_ok=False, chat_ok=False, detail="LLM_MODEL is empty.")
    if not api_key:
        return build_result(runtime, "config_missing", auth_ok=False, chat_ok=False, detail="LLM_API_KEY is empty.")

    models_probe = request_json(
        method="GET",
        url=runtime["base_url"].rstrip("/") + "/models",
        api_key=api_key,
    )
    chat_probe = request_json(
        method="POST",
        url=runtime["base_url"].rstrip("/") + "/chat/completions",
        api_key=api_key,
        payload={
            "model": runtime["model"],
            "messages": [{"role": "user", "content": "Reply with OK only."}],
            "temperature": 0,
            "max_tokens": 8,
        },
    )

    status = classify_auth_status(models_probe=models_probe, chat_probe=chat_probe)
    return {
        "name": runtime["name"],
        "runtime": runtime,
        "status": status,
        "auth_ok": models_probe["ok"],
        "chat_ok": chat_probe["ok"],
        "models_probe": summarize_probe(models_probe),
        "chat_probe": summarize_probe(chat_probe),
    }


def build_runtime(entry: dict[str, Any]) -> dict[str, str]:
    if entry.get("from_env"):
        return {
            "name": str(entry.get("name", "")),
            "provider": os.getenv("LLM_PROVIDER", ""),
            "model": os.getenv("LLM_MODEL", ""),
            "base_url": os.getenv("LLM_BASE_URL", ""),
        }
    return {
        "name": str(entry.get("name", "")),
        "provider": str(entry.get("provider", "")),
        "model": str(entry.get("model", "")),
        "base_url": str(entry.get("base_url", "")),
    }


def resolve_api_key(entry: dict[str, Any]) -> str:
    if entry.get("from_env"):
        return os.getenv("LLM_API_KEY", "")
    api_key_env = str(entry.get("api_key_env", "")).strip()
    if api_key_env:
        return os.getenv(api_key_env, "")
    return str(entry.get("api_key", ""))


def request_json(
    *,
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Authorization": f"Bearer {api_key}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8")
            return {"ok": True, "status": response.status, "body": body[:500]}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "body": body[:500]}
    except Exception as exc:
        return {"ok": False, "status": "exception", "body": str(exc)[:500]}


def classify_auth_status(*, models_probe: dict[str, Any], chat_probe: dict[str, Any]) -> str:
    if models_probe["ok"] and chat_probe["ok"]:
        return "passed"
    combined = f"{models_probe.get('body', '')} {chat_probe.get('body', '')}".lower()
    if "invalid_api_key" in combined or "incorrect api key" in combined or "authentication fails" in combined:
        return "auth_invalid"
    if models_probe["ok"] and not chat_probe["ok"]:
        return "model_or_request_rejected"
    if str(models_probe.get("status", "")).startswith("5") or str(chat_probe.get("status", "")).startswith("5"):
        return "provider_server_error"
    return "connectivity_or_runtime_error"


def summarize_probe(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": probe.get("ok", False),
        "status": probe.get("status", ""),
        "body_preview": probe.get("body", ""),
    }


def build_result(
    runtime: dict[str, str],
    status: str,
    *,
    auth_ok: bool,
    chat_ok: bool,
    detail: str,
) -> dict[str, Any]:
    return {
        "name": runtime["name"],
        "runtime": runtime,
        "status": status,
        "auth_ok": auth_ok,
        "chat_ok": chat_ok,
        "models_probe": {"ok": auth_ok, "status": "", "body_preview": detail},
        "chat_probe": {"ok": chat_ok, "status": "", "body_preview": detail},
    }


def build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for item in results:
        status = str(item.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return {
        "provider_count": len(results),
        "status_counts": counts,
    }


if __name__ == "__main__":
    raise SystemExit(main())
