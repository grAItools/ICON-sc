"""Timer: labelled nested sections, cumulative stats, injectable sync hook."""

from __future__ import annotations

import pytest

from symcon.core.profiling import Timer, TimerError


def test_nested_sections_and_cumulative_stats() -> None:
    timer = Timer()
    for _ in range(3):
        with timer.section("step"), timer.section("dycore"):
            pass
    assert timer.total_calls("step") == 3
    assert timer.total_calls("dycore") == 3
    assert timer.total_runtime("step") >= timer.total_runtime("dycore") >= 0.0


def test_report_shows_nesting() -> None:
    timer = Timer()
    with timer.section("step"):
        with timer.section("dycore"):
            pass
        with timer.section("physics"):
            pass
    report = timer.report()
    lines = report.splitlines()
    assert lines[0].startswith("step:")
    assert any(line.startswith("  dycore:") for line in lines)
    assert any(line.startswith("  physics:") for line in lines)


def test_same_label_under_different_parents_is_separate_but_aggregated() -> None:
    timer = Timer()
    with timer.section("a"), timer.section("halo"):
        pass
    with timer.section("b"), timer.section("halo"):
        pass
    assert timer.total_calls("halo") == 2


def test_only_nested_stops_allowed() -> None:
    timer = Timer()
    timer.start("outer")
    timer.start("inner")
    with pytest.raises(TimerError, match="inner"):
        timer.stop("outer")
    timer.stop("inner")
    timer.stop("outer")


def test_stop_without_start_and_unknown_label() -> None:
    timer = Timer()
    with pytest.raises(TimerError, match="no section"):
        timer.stop()
    with pytest.raises(TimerError, match="not a known section"):
        timer.total_runtime("ghost")


def test_reentrant_label_rejected() -> None:
    timer = Timer()
    timer.start("x")
    with pytest.raises(TimerError, match="already running"):
        timer.start("x")
    timer.stop()


def test_sync_hook_called_before_tic_and_toc() -> None:
    calls: list[str] = []
    timer = Timer(sync=lambda: calls.append("sync"))
    with timer.section("kernel"):
        pass
    assert calls == ["sync", "sync"]  # once at start, once at stop


def test_reset_zeroes_statistics_but_keeps_tree() -> None:
    timer = Timer()
    with timer.section("step"):
        pass
    timer.reset()
    assert timer.total_calls("step") == 0
    assert timer.total_runtime("step") == 0.0


def test_report_refuses_while_running() -> None:
    timer = Timer()
    timer.start("open")
    with pytest.raises(TimerError, match="running"):
        timer.report()
    timer.stop()
