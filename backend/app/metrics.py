"""Metrics collection for Project A RAG Platform."""
from __future__ import annotations

import threading
from collections import defaultdict


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._request_counts: dict[str, int] = defaultdict(int)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._request_durations: list[float] = []

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        with self._lock:
            key = f"{method} {path} {status_code}"
            self._request_counts[key] += 1
            if status_code >= 400:
                self._error_counts[f"{status_code}"] += 1
            self._request_durations.append(duration_ms)

    def record_job(self, job_type: str, status: str, duration_ms: float = 0):
        with self._lock:
            key = f"job_{job_type}_{status}"
            self._request_counts[key] += 1

    def generate(self) -> str:
        lines = ["# Project A Metrics"]
        with self._lock:
            for key, count in sorted(self._request_counts.items()):
                lines.append(f"request_total{{key=\"{key}\"}} {count}")
            for code, count in sorted(self._error_counts.items()):
                lines.append(f"error_total{{status=\"{code}\"}} {count}")
            if self._request_durations:
                avg = sum(self._request_durations) / len(self._request_durations)
                lines.append(f"request_duration_ms_avg {avg:.2f}")
        return "\n".join(lines) + "\n"

_metrics = Metrics()

def get_metrics() -> Metrics:
    return _metrics

MetricsCollector = Metrics  # backward-compatible alias
