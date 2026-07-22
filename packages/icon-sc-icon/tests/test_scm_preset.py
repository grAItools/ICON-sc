"""S09 acceptance tests: the SCM preset composition (SPEC acceptance 1, 3, 4, 5).

The 48-hour L3-lite stability run (acceptance 2) lives in
``test_scm_stability.py`` (``slow``-marked). Everything here runs on the
embedded (debug) backend and stays in the fast tier, except the short
backend-parametrized smoke (gtfn legs share the compiled n_cell=1 variant with
the stability test through the persistent gt4py build cache).
"""

from __future__ import annotations

import hashlib
import importlib.util
import platform
import sys
import warnings
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import xarray as xr

from icon_sc.core import (
    BusError,
    ComputeContext,
    CouplingConstraintError,
    MemoryMonitor,
    make_backend,
    timeloop,
)
from icon_sc.core.state import canonical_units
from icon_sc.core.time import datetime
from icon_sc.icon.components import ApplySlowTendencies, PrescribedCooling
from icon_sc.icon.components.idealized import SLOW_TEMPERATURE_SLOT
from icon_sc.icon.grid.vertical import reference_temperature
from icon_sc.icon.presets import SCM_FAST_ORDER, SCMConfig, build_scm

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_PATH = REPO_ROOT / "examples" / "01_scm_column.py"

TRACERS = (
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
)
RATES = (
    "icon:rain_gsp_rate",
    "icon:snow_gsp_rate",
    "icon:ice_gsp_rate",
    "icon:graupel_gsp_rate",
)

#: SPEC acceptance 5 — column regression fingerprint (a change-detector, not a
#: science claim): SHA-256 over the raw float64 bytes of the selected final-state
#: fields after ``_FINGERPRINT_STEPS`` steps of the default preset on the
#: embedded backend, fp64-exact on the same platform. Platform-tagged: unlisted
#: platforms skip (fp contractions may differ across ISAs/BLAS builds). The tag
#: includes numpy's float64 ``exp`` SIMD dispatch family: on AVX-512 hosts numpy
#: selects ``exp``/``log`` inner loops whose results differ in the last ULP from
#: the AVX2/SSE loops, and CI's heterogeneous fleet draws both host kinds per-VM
#: (issue #11). Each golden is bit-exact within its family. The AVX-512 hash is
#: byte-identical across the CI failures and an Intel SDE ``-skx`` emulation of
#: the avx2-family reference host; numpy ≤2.2 names the targets by ISA extension
#: (``AVX2``/``AVX512_SKX``), numpy ≥2.5 by x86-64 microarchitecture level
#: (``X86_V3``/``X86_V4``) — same two kernel families, so the hash pairs match.
_FINGERPRINT_STEPS = 12  # covers one slow-physics refire (period = 10 steps)
_FINGERPRINT_FIELDS = ("air_temperature", *TRACERS, *RATES, SLOW_TEMPERATURE_SLOT)
_FINGERPRINT_AVX2 = "c4e0b5b776e03d5f4e8f56c9774da50aa3dac20095e7cbec8cae11202fb1aa68"
_FINGERPRINT_AVX512 = "f6e575d1fc83e1191137b7e26a39a418a1e19fefceeb1e257115ae2f8950302d"
_FINGERPRINT_GOLDEN = {
    ("linux", "x86_64", "avx2"): _FINGERPRINT_AVX2,
    ("linux", "x86_64", "x86_v3"): _FINGERPRINT_AVX2,
    ("linux", "x86_64", "avx512_skx"): _FINGERPRINT_AVX512,
    ("linux", "x86_64", "x86_v4"): _FINGERPRINT_AVX512,
}


def _simd_family() -> str:
    """The numpy float64 ``exp`` inner-loop dispatch family active in this process.

    numpy picks the loop per process at import time by CPUID (honoring
    ``NPY_DISABLE_CPU_FEATURES``), so this is exactly the discriminator the
    fingerprint needs. An unknown family (new numpy dispatch target, non-x86
    build, feature-disabling env vars) skips the test rather than mis-keying
    a golden.
    """
    info = np.lib.introspect.opt_func_info(func_name="exp", signature="float64")
    (loop,) = info["exp"].values()
    return str(loop["current"]).split("(")[0].lower()


def _load_example() -> Any:
    spec = importlib.util.spec_from_file_location("example_01_scm_column", EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_steps(
    composition: Any,
    state: dict[str, Any],
    cfg: SCMConfig,
    n_steps: int,
    monitors: tuple[Any, ...] = (),
) -> dict[str, Any]:
    with warnings.catch_warnings():
        # icon4py's embedded execution warns about Python execution; their own
        # tests run with the same warnings (S07/S08 precedent).
        warnings.simplefilter("ignore")
        return timeloop(
            state, composition.step, timestep=cfg.dtime, n_steps=n_steps, monitors=monitors
        )


# -- acceptance 1: the example runs green and writes declared variables ------------


def test_example_smoke_writes_declared_variables(tmp_path: Path) -> None:
    """SPEC acceptance 1: run the example (short horizon) and inspect the NetCDF:
    every declared output variable is present, with its registry units."""
    example = _load_example()
    out = tmp_path / "scm_column.nc"
    final = example.main(output=out, hours=0.1)  # 12 steps at dt=30 s

    assert out.exists()
    with xr.open_dataset(out) as dataset:
        assert dataset.sizes["time"] == 12
        for name in example.OUTPUT_SET:
            assert name in dataset, name
            assert dataset[name].attrs["units"] == canonical_units(name), name
            assert np.isfinite(np.asarray(dataset[name].data)).all(), name
    assert np.isfinite(np.asarray(final["air_temperature"].data)).all()


def test_example_uses_the_preset_builder() -> None:
    """PLAN item 2: the example must stay diff-clean against the builder — it
    assembles nothing by hand (the plan-hash version of this arrives in S10/S14)."""
    source = EXAMPLE_PATH.read_text()
    assert "build_scm(" in source
    for hand_rolled in ("SequentialUpdateSplitting", "ConcurrentCoupling", "SlowTendencyBus"):
        assert hand_rolled not in source, hand_rolled


# -- builder structure (PLAN item 2) ------------------------------------------------


def test_builder_structure() -> None:
    """The composition the builder returns is the §5.1 shape at column scale."""
    composition, state, cfg = build_scm()

    assert composition.order == SCM_FAST_ORDER == ("satad", "mphys", "satad")
    section_names = tuple(section.name for section in composition.fast.sections)
    assert section_names == ("satad", "mphys", "satad")
    # The two satad sections are one instance: same scheme, same config (ICON's
    # fast suite calls the identical satad_v_3D twice).
    assert composition.fast.sections[0] is composition.fast.sections[2]

    assert composition.slow.components == (composition.cooling,)
    assert isinstance(composition.cooling.component, PrescribedCooling)
    assert composition.cooling.update_period == cfg.slow_timestep
    assert cfg.slow_timestep == 10 * cfg.dtime  # SPEC acceptance 3 cadence
    assert isinstance(composition.core, ApplySlowTendencies)
    assert sorted(composition.bus.slots) == [SLOW_TEMPERATURE_SLOT]

    # The initial column is ready for the suite: moist, unstable, qnc present.
    assert "icon:qnc" in state
    assert float(np.max(state["specific_humidity"].data)) > 0.01  # scaled profile


def test_composition_runs_on_all_backends(backend: str) -> None:
    """Short composition smoke per backend (gtfn_gpu leg skips without a device)."""
    ctx = ComputeContext(backend=make_backend(backend))
    composition, state, cfg = build_scm(ctx=ctx)
    final = _run_steps(composition, state, cfg, n_steps=2)
    for name in ("air_temperature", *TRACERS, *RATES, SLOW_TEMPERATURE_SLOT):
        assert np.isfinite(np.asarray(final[name].data)).all(), name


# -- acceptance 3: piecewise-constant bus tendency + consumer enforcement -----------


def _slot_series(cfg: SCMConfig, n_steps: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run ``n_steps`` and return (post-step snapshots, initial-state snapshot)."""
    composition, state, cfg = build_scm(cfg)
    initial = {name: value.copy(deep=True) for name, value in state.items() if name != "time"}
    monitor = MemoryMonitor(variables=(SLOW_TEMPERATURE_SLOT, "air_temperature", "altitude"))
    _run_steps(composition, state, cfg, n_steps=n_steps, monitors=(monitor,))
    return list(monitor.snapshots), initial


def _expected_cooling_tendency(temperature: Any, altitude: Any, cfg: SCMConfig) -> Any:
    """The PrescribedCooling closed form, replicated operation-for-operation."""
    tau = cfg.cooling.relaxation_timescale.total_seconds()
    t_eq = reference_temperature(np.asarray(altitude)) - cfg.cooling.equilibrium_offset
    return (t_eq - np.asarray(temperature)) / tau


def test_slow_tendency_exact_step_function() -> None:
    """SPEC acceptance 3: with dt_slow = 10·dt the published tendency is an exact
    step function — bitwise-constant inside each 10-step window, refired from the
    pre-fire state at window boundaries, matching the analytic closed form."""
    cfg = SCMConfig()
    snapshots, initial = _slot_series(cfg, n_steps=21)

    series = [np.asarray(snapshot[SLOW_TEMPERATURE_SLOT].data) for snapshot in snapshots]
    # Windows [1..10] and [11..20] (1-based steps): bitwise-constant.
    for step_index in range(1, 10):
        assert np.array_equal(series[step_index], series[0]), f"step {step_index + 1}"
    for step_index in range(11, 20):
        assert np.array_equal(series[step_index], series[10]), f"step {step_index + 1}"
    # Refires produce *different* values (the column cooled/warmed in between).
    assert not np.array_equal(series[10], series[0])
    assert not np.array_equal(series[20], series[10])

    # Fired values match the closed form evaluated on the pre-fire state, exactly.
    expected_first = _expected_cooling_tendency(
        initial["air_temperature"].data, initial["altitude"].data, cfg
    )
    assert np.array_equal(series[0], expected_first)
    expected_refire = _expected_cooling_tendency(
        snapshots[9]["air_temperature"].data, snapshots[9]["altitude"].data, cfg
    )
    assert np.array_equal(series[10], expected_refire)


def test_cadence_rounding_and_phase_offset() -> None:
    """PLAN pitfall: non-divisor cadence + off-grid start time. dt_slow = 285 s
    over dt = 30 s rounds to the nearest multiple (300 s, frozen S03 rule), and
    the firing phase anchors on the first call, not on wall-clock multiples."""
    cfg = SCMConfig(
        slow_timestep=timedelta(seconds=285),
        start_time=datetime(2000, 1, 1, 0, 0, 45),  # not a dt_slow multiple
    )
    composition, _, _ = build_scm(cfg)
    assert composition.cooling.period_for(cfg.dtime) == timedelta(seconds=300)

    snapshots, _ = _slot_series(cfg, n_steps=12)
    series = [np.asarray(snapshot[SLOW_TEMPERATURE_SLOT].data) for snapshot in snapshots]
    for step_index in range(1, 10):
        assert np.array_equal(series[step_index], series[0]), f"step {step_index + 1}"
    assert not np.array_equal(series[10], series[0])  # refire at step 11
    assert np.array_equal(series[11], series[10])


def test_bus_rejects_preset_without_consumer() -> None:
    """SPEC acceptance 3: removing the consumer must reject at build time (the
    single-consumer check — a dangling tendency silently loses physics)."""
    with pytest.raises(BusError, match="0 consumers"):
        build_scm(consume_slow=False)


# -- acceptance 4: ordering constraints ---------------------------------------------


def test_order_swap_against_must_follow_raises() -> None:
    """SPEC acceptance 4: microphysics before the first satad violates its
    must_follow constraint at composition time."""
    with pytest.raises(CouplingConstraintError, match="must follow"):
        build_scm(fast_order=("mphys", "satad", "satad"))


def test_order_swap_against_must_precede_raises() -> None:
    """Microphysics not followed by a satad violates must_precede (tutorial
    §3.7.2: equilibrium before the slow physics)."""
    with pytest.raises(CouplingConstraintError, match="must precede"):
        build_scm(fast_order=("satad", "satad", "mphys"))


def test_unknown_section_name_raises() -> None:
    with pytest.raises(ValueError, match="not SCM sections"):
        build_scm(fast_order=("satad", "turb", "satad"))


# -- PLAN pitfall: SUS chaining actually feeds updated buffers -----------------------


def test_sus_chaining_feeds_graupel_outputs_to_second_satad() -> None:
    """The federation must equal the hand-rolled satad → mphys → satad chain
    bitwise, and must differ from the broken variant that feeds the second satad
    the *first* satad's state (a deliberate chaining bug still 'runs')."""
    composition, state, cfg = build_scm()
    # Spin up a few steps so hydrometeors exist and every section has real work.
    state = _run_steps(composition, state, cfg, n_steps=5)

    satad, mphys, _ = composition.fast.sections

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, federation_state = composition.fast(state, cfg.dtime)

        # Hand-rolled chain (SUS eq. 2.12 semantics).
        working = dict(state)
        chained: dict[str, Any] = {}
        for section in (satad, mphys, satad):
            diags, new_state = section(working, cfg.dtime)
            working.update(diags)
            working.update(new_state)
            chained.update(new_state)

        # Broken variant: second satad sees the first satad's state, not graupel's.
        broken_working = dict(state)
        _, satad_state = satad(broken_working, cfg.dtime)
        broken_working.update(satad_state)
        _, broken_state = satad(broken_working, cfg.dtime)

    for name, expected in chained.items():
        assert np.array_equal(np.asarray(federation_state[name].data), np.asarray(expected.data)), (
            name
        )
    # The graupel step visibly changed what the second satad consumes.
    assert not np.array_equal(
        np.asarray(federation_state["specific_cloud_content"].data),
        np.asarray(broken_state["specific_cloud_content"].data),
    )


# -- acceptance 5: regression fingerprint --------------------------------------------


def _fingerprint(final: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    for name in _FINGERPRINT_FIELDS:
        array = np.asarray(final[name].data)
        assert array.dtype == np.float64, name
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def test_column_regression_fingerprint() -> None:
    """SPEC acceptance 5: fp64-exact change detector on the same platform."""
    key = (sys.platform, platform.machine(), _simd_family())
    golden = _FINGERPRINT_GOLDEN.get(key)
    if golden is None:
        pytest.skip(f"no golden fingerprint recorded for platform {key!r}")
    composition, state, cfg = build_scm()
    final = _run_steps(composition, state, cfg, n_steps=_FINGERPRINT_STEPS)
    assert _fingerprint(final) == golden, key
