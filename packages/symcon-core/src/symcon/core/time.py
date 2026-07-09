"""cftime-aware datetime handling and cadence arithmetic (SPEC S02).

The calendar-keyed :func:`datetime` factory ports upstream sympl's semantics
(``sympl/_core/time.py``, see REFERENCES.lock): ``proleptic_gregorian`` yields a
stdlib ``datetime.datetime``; every other CF calendar yields the matching
``cftime`` class (timezones are a stdlib-only feature).

Cadence arithmetic backs the §8.2 cadence masks: the distinct step signatures of a
composition follow from the lcm of the component cadences and each cadence's phase.
All arithmetic is exact, over integer microseconds (``timedelta`` resolution).
"""

from __future__ import annotations

import datetime as _datetime
import math

import cftime

__all__ = [
    "CALENDARS",
    "datetime",
    "is_due",
    "phase",
    "timedelta",
    "timedelta_lcm",
]

#: Re-export so callers need no separate stdlib import for cadence declarations.
timedelta = _datetime.timedelta

#: CF calendar name → cftime datetime class (upstream sympl's calendar keying).
CALENDARS: dict[str, type] = {
    "all_leap": cftime.DatetimeAllLeap,
    "366_day": cftime.DatetimeAllLeap,
    "no_leap": cftime.DatetimeNoLeap,
    "noleap": cftime.DatetimeNoLeap,
    "365_day": cftime.DatetimeNoLeap,
    "360_day": cftime.Datetime360Day,
    "julian": cftime.DatetimeJulian,
    "gregorian": cftime.DatetimeGregorian,
    "standard": cftime.DatetimeGregorian,
}


def datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    tzinfo: _datetime.tzinfo | None = None,
    calendar: str = "proleptic_gregorian",
) -> _datetime.datetime | cftime.datetime:
    """Datetime-like object for the requested CF calendar (sympl semantics)."""
    if calendar.lower() == "proleptic_gregorian":
        return _datetime.datetime(
            year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo
        )
    if tzinfo is not None:
        raise ValueError("cftime does not support timezone-aware datetimes.")
    try:
        cftime_cls = CALENDARS[calendar.lower()]
    except KeyError:
        raise ValueError(
            f"unknown calendar {calendar!r}; known: {['proleptic_gregorian', *sorted(CALENDARS)]}"
        ) from None
    result: cftime.datetime = cftime_cls(year, month, day, hour, minute, second, microsecond)
    return result


def _microseconds(delta: _datetime.timedelta, *, positive: bool = True) -> int:
    out = delta // _datetime.timedelta(microseconds=1)
    if positive and out <= 0:
        raise ValueError(f"cadence periods must be positive, got {delta!r}.")
    return out


def timedelta_lcm(*deltas: _datetime.timedelta) -> _datetime.timedelta:
    """Least common multiple of positive timedeltas (exact, integer microseconds).

    The lcm of the component cadences (Δt, dt_conv, dt_rad, …) is the period of the
    step-signature pattern the plan compiler precomputes (§8.2).
    """
    if not deltas:
        raise ValueError("timedelta_lcm needs at least one timedelta.")
    return _datetime.timedelta(microseconds=math.lcm(*(_microseconds(d) for d in deltas)))


def phase(offset: _datetime.timedelta, period: _datetime.timedelta) -> _datetime.timedelta:
    """``offset`` modulo ``period``, normalized into ``[0, period)`` (exact)."""
    return _datetime.timedelta(
        microseconds=_microseconds(offset, positive=False) % _microseconds(period)
    )


def is_due(
    elapsed: _datetime.timedelta,
    period: _datetime.timedelta,
    cadence_phase: _datetime.timedelta = _datetime.timedelta(0),
) -> bool:
    """True when a cadence with the given period/phase fires at ``elapsed``.

    A cadence fires at ``phase, phase + period, phase + 2*period, …``; ``elapsed``
    is time since composition start (non-negative).
    """
    elapsed_us = _microseconds(elapsed, positive=False)
    if elapsed_us < 0:
        raise ValueError(f"elapsed must be non-negative, got {elapsed!r}.")
    period_us = _microseconds(period)
    phase_us = _microseconds(cadence_phase, positive=False) % period_us
    return elapsed_us >= phase_us and (elapsed_us - phase_us) % period_us == 0
