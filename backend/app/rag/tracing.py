from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T", bound=Callable)


def trace_retrieval(name: str) -> Callable[[T], T]:
    try:
        from langsmith import traceable
    except ImportError:
        return lambda function: function

    return traceable(name=name, run_type="retriever")
