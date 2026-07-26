"""HTTP load test helper for Project A.

This script intentionally uses only the Python standard library so it can run in
local demo and CI environments without installing k6, Locust, or aiohttp.

Examples:
    python scripts/load_test_http.py --scenario health --requests 100 --concurrency 10
    python scripts/load_test_http.py --scenario agentic --requests 50 --concurrency 5 --json-out reports/load-agentic.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    method: str
    path: str
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class RequestResult:
    ok: bool
    status: int
    latency_ms: float
    error: str = ""


SCENARIOS: dict[str, Scenario] = {
    "health": Scenario("health", "GET", "/healthz"),
    "ready": Scenario("ready", "GET", "/readyz"),
    "metrics": Scenario("metrics", "GET", "/metrics"),
    "chat": Scenario(
        "chat",
        "POST",
        "/api/v1/chat",
        {"question": "E21 故障码应该如何排查？", "top_k": 4},
    ),
    "agentic": Scenario(
        "agentic",
        "POST",
        "/api/v1/agent/diagnose",
        {
            "question": "UPS-30K 出现 E21 故障码并伴随异味，应该如何处理？",
            "top_k": 4,
            "create_ticket_on_escalation": False,
        },
    ),
    "traces": Scenario("traces", "GET", "/api/v1/rag/traces?limit=20"),
    "graph": Scenario("graph", "GET", "/api/v1/rag/graph/relations"),
}


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((pct / 100) * (len(ordered) - 1)))
    return ordered[max(0, min(index, len(ordered) - 1))]


def build_request(base_url: str, scenario: Scenario, api_key: str | None) -> urllib.request.Request:
    url = base_url.rstrip("/") + scenario.path
    headers = {"User-Agent": "project-a-load-test/1.0"}
    data = None
    if api_key:
        headers["X-API-Key"] = api_key
    if scenario.payload is not None:
        data = json.dumps(scenario.payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url=url, data=data, headers=headers, method=scenario.method)


def run_one(base_url: str, scenario: Scenario, timeout: float, api_key: str | None) -> RequestResult:
    request = build_request(base_url, scenario, api_key)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            latency_ms = (time.perf_counter() - start) * 1000
            status = int(response.status)
            return RequestResult(ok=200 <= status < 400, status=status, latency_ms=latency_ms)
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(ok=False, status=int(exc.code), latency_ms=latency_ms, error=str(exc))
    except Exception as exc:  # noqa: BLE001 - load test must record all transport failures.
        latency_ms = (time.perf_counter() - start) * 1000
        return RequestResult(ok=False, status=0, latency_ms=latency_ms, error=type(exc).__name__)


def summarize(results: list[RequestResult], elapsed_s: float, scenario: str, concurrency: int) -> dict[str, Any]:
    latencies = [r.latency_ms for r in results]
    ok_count = sum(1 for r in results if r.ok)
    total = len(results)
    errors = [r for r in results if not r.ok]
    status_counts: dict[str, int] = {}
    error_counts: dict[str, int] = {}
    for result in results:
        status_counts[str(result.status)] = status_counts.get(str(result.status), 0) + 1
        if result.error:
            error_counts[result.error] = error_counts.get(result.error, 0) + 1
    return {
        "scenario": scenario,
        "requests": total,
        "concurrency": concurrency,
        "ok": ok_count,
        "failed": total - ok_count,
        "error_rate": round((total - ok_count) / total, 6) if total else 0.0,
        "elapsed_s": round(elapsed_s, 3),
        "throughput_rps": round(total / elapsed_s, 3) if elapsed_s > 0 else 0.0,
        "latency_ms": {
            "min": round(min(latencies), 3) if latencies else 0.0,
            "avg": round(statistics.mean(latencies), 3) if latencies else 0.0,
            "p50": round(percentile(latencies, 50), 3),
            "p95": round(percentile(latencies, 95), 3),
            "p99": round(percentile(latencies, 99), 3),
            "max": round(max(latencies), 3) if latencies else 0.0,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "error_counts": dict(sorted(error_counts.items())),
        "sample_errors": [r.error for r in errors[:5] if r.error],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project A HTTP load test helper")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="health")
    parser.add_argument("--requests", type=int, default=100, help="Total request count")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent workers")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per request timeout in seconds")
    parser.add_argument("--api-key", default=None, help="Optional X-API-Key header value")
    parser.add_argument("--json-out", default=None, help="Optional JSON summary output path")
    parser.add_argument(
        "--max-error-rate",
        type=float,
        default=0.01,
        help="Fail when error_rate is greater than this value",
    )
    parser.add_argument(
        "--max-p95-ms",
        type=float,
        default=0.0,
        help="Fail when p95 latency is greater than this value; 0 disables the check",
    )
    args = parser.parse_args()
    if args.requests <= 0:
        raise SystemExit("--requests must be positive")
    if args.concurrency <= 0:
        raise SystemExit("--concurrency must be positive")
    if args.concurrency > args.requests:
        args.concurrency = args.requests
    return args


def main() -> int:
    args = parse_args()
    scenario = SCENARIOS[args.scenario]
    started = time.perf_counter()
    results: list[RequestResult] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [
            executor.submit(run_one, args.base_url, scenario, args.timeout, args.api_key)
            for _ in range(args.requests)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed_s = time.perf_counter() - started
    summary = summarize(results, elapsed_s, args.scenario, args.concurrency)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    failed = False
    if summary["error_rate"] > args.max_error_rate:
        print(
            f"FAIL: error_rate {summary['error_rate']} > max_error_rate {args.max_error_rate}",
            flush=True,
        )
        failed = True
    if args.max_p95_ms > 0 and summary["latency_ms"]["p95"] > args.max_p95_ms:
        print(
            f"FAIL: p95 {summary['latency_ms']['p95']}ms > max_p95_ms {args.max_p95_ms}ms",
            flush=True,
        )
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

