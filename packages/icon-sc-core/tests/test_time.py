"""Cadence arithmetic (property-tested vs brute force) and cftime-aware datetimes."""

from __future__ import annotations

import datetime as stdlib_datetime

import cftime
import pytest
from hypothesis import given
from hypothesis import strategies as st

from symcon.core.time import datetime, is_due, phase, timedelta, timedelta_lcm

microseconds = st.integers(min_value=1, max_value=60)


@given(st.lists(microseconds, min_size=1, max_size=3))
def test_lcm_matches_brute_force(values: list[int]) -> None:
    deltas = [timedelta(microseconds=v) for v in values]
    result = timedelta_lcm(*deltas) // timedelta(microseconds=1)
    # brute force: the smallest positive integer divisible by every value
    candidate = next(m for m in range(1, 60**3 + 1) if all(m % v == 0 for v in values))
    assert result == candidate


@given(st.integers(min_value=-(10**7), max_value=10**7), microseconds)
def test_phase_is_mod_into_period(offset_us: int, period_us: int) -> None:
    result = phase(timedelta(microseconds=offset_us), timedelta(microseconds=period_us))
    result_us = result // timedelta(microseconds=1)
    assert 0 <= result_us < period_us
    assert (offset_us - result_us) % period_us == 0


@given(
    st.integers(min_value=0, max_value=300),
    st.integers(min_value=1, max_value=50),
    st.integers(min_value=0, max_value=120),
)
def test_is_due_matches_brute_force_fire_times(
    elapsed_us: int, period_us: int, phase_us: int
) -> None:
    fire_times = {phase_us % period_us + k * period_us for k in range(400)}
    assert is_due(
        timedelta(microseconds=elapsed_us),
        timedelta(microseconds=period_us),
        timedelta(microseconds=phase_us),
    ) == (elapsed_us in fire_times)


def test_lcm_of_model_cadences() -> None:
    # Δt=90s, dt_conv=600s, dt_rad=1800s → the step-signature pattern repeats
    # every 1800s (lcm = 2^3·3^2·5^2 µs-exact, no float in sight).
    assert timedelta_lcm(
        timedelta(seconds=90), timedelta(seconds=600), timedelta(seconds=1800)
    ) == timedelta(seconds=1800)
    assert timedelta_lcm(
        timedelta(seconds=90), timedelta(seconds=600), timedelta(seconds=2100)
    ) == timedelta(seconds=12600)


def test_zero_or_negative_period_rejected() -> None:
    with pytest.raises(ValueError, match="positive"):
        timedelta_lcm(timedelta(0))
    with pytest.raises(ValueError, match="positive"):
        phase(timedelta(seconds=1), timedelta(seconds=-1))


def test_datetime_default_calendar_is_stdlib() -> None:
    value = datetime(2000, 1, 1, 12)
    assert type(value) is stdlib_datetime.datetime


@pytest.mark.parametrize(
    ("calendar", "cls"),
    [
        ("no_leap", cftime.DatetimeNoLeap),
        ("365_day", cftime.DatetimeNoLeap),
        ("all_leap", cftime.DatetimeAllLeap),
        ("360_day", cftime.Datetime360Day),
        ("julian", cftime.DatetimeJulian),
        ("gregorian", cftime.DatetimeGregorian),
    ],
)
def test_datetime_cf_calendars(calendar: str, cls: type) -> None:
    value = datetime(2000, 3, 1, calendar=calendar)
    assert isinstance(value, cls)


def test_360_day_calendar_actually_has_30_day_months() -> None:
    value = datetime(2000, 2, 30, calendar="360_day")  # invalid in gregorian
    assert (value + timedelta(days=1)).month == 3


def test_unknown_calendar_rejected() -> None:
    with pytest.raises(ValueError, match="proleptic_gregorian"):
        datetime(2000, 1, 1, calendar="klingon")


def test_timezone_only_for_proleptic_gregorian() -> None:
    with pytest.raises(ValueError, match="timezone"):
        datetime(2000, 1, 1, tzinfo=stdlib_datetime.timezone.utc, calendar="julian")
