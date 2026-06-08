"""Metrics collection for Project A RAG Platform."""
from __future__ import annotations

import threading
import time
from collections import defaultdict


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self._request_counts: dict[tuple[str, str, str], int] = defaultdict(int)
        self._error_counts: dict[str, int] = defaultdict(int)
        self._job_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._job_durations: list[float] = []
        self._request_durations: list[float] = []
        self._start_time = time.time()

    def record_request(self, method: str, path: str, status_code: int, duration_ms: float):
        with self._lock:
            key = (method, path, str(status_code))
            self._request_counts[key] += 1
            if status_code >= 400:
                self._error_counts[str(status_code)] += 1
            self._request_durations.append(duration_ms)

    def record_job(self, job_type: str, status: str, duration_ms: float = 0):
        with self._lock:
            key = (job_type, status)
            self._job_counts[key] += 1
            if duration_ms:
                self._job_durations.append(duration_ms)

    def generate(self) -> str:
        lines = []
        with self._lock:
            # Request metrics
            lines.append("# HELP project_a_request_total Total HTTP requests")
            lines.append("# TYPE project_a_request_total counter")
            for (method, path, status), count in sorted(self._request_counts.items()):
                lines.append(f'project_a_request_total{{method="{method}",path="{path}",status="{status}"}} {count}')

            # Error metrics
            if self._error_counts:
                lines.append("# HELP project_a_error_total Total errors")
                lines.append("# TYPE project_a_error_total counter")
                for status, count in sorted(self._error_counts.items()):
                    lines.append(f'project_a_error_total{{status="{status}"}} {count}')

            # Job metrics
            if self._job_counts:
                lines.append("# HELP project_a_job_total Total jobs processed")
                lines.append("# TYPE project_a_job_total counter")
                for (job_type, status), count in sorted(self._job_counts.items()):
                    lines.append(f'project_a_job_total{{job_type="{job_type}",status="{status}"}} {count}')

            # Job duration
            if self._job_durations:
                avg = sum(self._job_durations) / len(self._job_durations)
                lines.append("# HELP project_a_job_duration_ms Average job duration in ms")
                lines.append("# TYPE project_a_job_duration_ms gauge")
                lines.append(f"project_a_job_duration_ms {avg:.2f}")

            # Uptime
            uptime = time.time() - self._start_time
            lines.append("# HELP project_a_uptime_seconds Platform uptime in seconds")
            lines.append("# TYPE project_a_uptime_seconds gauge")
            lines.append(f"project_a_uptime_seconds {uptime:.2f}")

            # Duration
            if self._request_durations:
                avg = sum(self._request_durations) / len(self._request_durations)
                lines.append(f"# Request duration avg: {avg:.2f}ms")

        return "\n".join(lines) + "\n"

_metrics = Metrics()

def get_metrics() -> Metrics:
    return _metrics

MetricsCollector = Metrics  # backward-compatible alias
