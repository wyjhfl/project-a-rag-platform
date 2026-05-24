from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar

T = TypeVar("T", bound=Callable)

_TRACE_SESSION: ContextVar[dict[str, Any] | None] = ContextVar(
    "project_a_trace_session",
    default=None,
)


def start_trace(name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    session = {
        "name": name,
        "metadata": metadata or {},
        "events": [],
    }
    _TRACE_SESSION.set(session)
    return session


def end_trace() -> dict[str, Any] | None:
    session = _TRACE_SESSION.get()
    _TRACE_SESSION.set(None)
    return session


def current_trace() -> dict[str, Any] | None:
    return _TRACE_SESSION.get()


def record_trace_event(
    name: str,
    *,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    session = _TRACE_SESSION.get()
    if session is None:
        return
    session["events"].append(
        {
            "name": name,
            "inputs": _safe_value(inputs or {}),
            "outputs": _safe_value(outputs or {}),
            "metadata": _safe_value(metadata or {}),
        }
    )


def summarize_chunks(chunks: list[Any]) -> list[dict[str, Any]]:
    summary = []
    for chunk in chunks:
        metadata = getattr(chunk, "metadata", {}) or {}
        summary.append(
            {
                "source": str(metadata.get("source", "")),
                "chunk_index": int(metadata.get("chunk_index", 0)),
                "preview": getattr(chunk, "content", "")[:120],
            }
        )
    return summary


def trace_retrieval(name: str) -> Callable[[T], T]:
    try:
        from langsmith import traceable
    except ImportError:
        return lambda function: function

    return traceable(name=name, run_type="retriever")


def _safe_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return _safe_value(value.model_dump())
    if hasattr(value, "__dict__"):
        return _safe_value(vars(value))
    return str(value)
