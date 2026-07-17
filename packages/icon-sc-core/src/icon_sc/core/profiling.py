"""Labelled nested Timer with an injectable device-sync hook (SPEC S02).

Ports the *idea* of Ubbiali's Timer (tasmania ``utils/timex.py``, REFERENCES.lock):
a tree of labelled nested sections with cumulative call counts and runtimes, and a
device synchronization before every tic/toc so asynchronous (GPU) work is charged to
the section that launched it. Differences from the reference: instance-based (no
class-global state) and the sync is an injected callback — core carries no cupy
dependency; a CUDA context injects ``cupy.cuda.Device(0).synchronize`` later.
"""

from __future__ import annotations

import timeit
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

__all__ = ["Timer", "TimerError"]


class TimerError(RuntimeError):
    """Mismatched start/stop of timer sections."""


@dataclass
class _Node:
    label: str
    parent: _Node | None = None
    children: dict[str, _Node] = field(default_factory=dict)
    level: int = 0
    tic: float = 0.0
    total_calls: int = 0
    total_runtime: float = 0.0


class Timer:
    """Labelled nested sections; cumulative statistics; explicit sync hook."""

    def __init__(self, sync: Callable[[], None] | None = None) -> None:
        self._sync = sync
        self._roots: dict[str, _Node] = {}
        self._stack: list[_Node] = []

    def start(self, label: str) -> None:
        """Open a section nested under the currently open one (if any)."""
        if any(node.label == label for node in self._stack):
            raise TimerError(f"section {label!r} is already running.")
        if self._stack:
            parent = self._stack[-1]
            node = parent.children.setdefault(
                label, _Node(label, parent=parent, level=parent.level + 1)
            )
        else:
            node = self._roots.setdefault(label, _Node(label))
        self._stack.append(node)
        if self._sync is not None:
            self._sync()
        node.tic = timeit.default_timer()

    def stop(self, label: str | None = None) -> None:
        """Close the innermost section (only nested stops are legal)."""
        if not self._stack:
            raise TimerError("no section is running.")
        node = self._stack[-1]
        if label is not None and label != node.label:
            raise TimerError(f"cannot stop {label!r} before stopping {node.label!r}.")
        if self._sync is not None:
            self._sync()
        toc = timeit.default_timer()
        node.total_calls += 1
        node.total_runtime += toc - node.tic
        self._stack.pop()

    @contextmanager
    def section(self, label: str) -> Iterator[None]:
        """``with timer.section("dycore"): ...``"""
        self.start(label)
        try:
            yield
        finally:
            self.stop(label)

    def _nodes(self, label: str) -> list[_Node]:
        out: list[_Node] = []

        def walk(node: _Node) -> None:
            if node.label == label:
                out.append(node)
            for child in node.children.values():
                walk(child)

        for root in self._roots.values():
            walk(root)
        return out

    def total_runtime(self, label: str) -> float:
        """Cumulative seconds across every section with this label."""
        nodes = self._nodes(label)
        if not nodes:
            raise TimerError(f"{label!r} is not a known section.")
        return sum(node.total_runtime for node in nodes)

    def total_calls(self, label: str) -> int:
        """Cumulative completed calls across every section with this label."""
        nodes = self._nodes(label)
        if not nodes:
            raise TimerError(f"{label!r} is not a known section.")
        return sum(node.total_calls for node in nodes)

    def reset(self) -> None:
        """Zero all statistics; running sections are discarded."""
        self._stack.clear()

        def walk(node: _Node) -> None:
            node.total_calls = 0
            node.total_runtime = 0.0
            for child in node.children.values():
                walk(child)

        for root in self._roots.values():
            walk(root)

    def report(self) -> str:
        """Human-readable tree of cumulative runtimes (seconds)."""
        if self._stack:
            raise TimerError(f"sections still running: {[n.label for n in self._stack]!r}.")
        lines: list[str] = []

        def walk(node: _Node) -> None:
            indent = "  " * node.level
            lines.append(
                f"{indent}{node.label}: {node.total_runtime:.6f} s ({node.total_calls} calls)"
            )
            for child in node.children.values():
                walk(child)

        for root in self._roots.values():
            walk(root)
        return "\n".join(lines)
