"""Module thuật toán tìm kiếm và giải màn chơi Bloxorz."""

from .base import (
    ALGORITHMS,
    Limits,
    ORDERED_DIRECTIONS,
    SearchAborted,
    SearchContext,
    SearchResult,
    reconstruct,
    register,
    run,
)
from .cost import move_cost  # noqa: F401 – public API VT5
from . import bfs  # noqa: F401 – đăng ký @register("bfs")
from . import ucs  # noqa: F401 – đăng ký @register("ucs")

__all__ = [
    "ALGORITHMS",
    "Limits",
    "ORDERED_DIRECTIONS",
    "SearchAborted",
    "SearchContext",
    "SearchResult",
    "bfs",
    "move_cost",
    "reconstruct",
    "register",
    "run",
    "ucs",
]