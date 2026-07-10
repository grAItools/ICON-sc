"""S08 acceptance tests for ``Microphysics``/``Graupel`` on the S06 test column.

Covers SPEC acceptance 2 (conservation + negativity on hypothesis-generated
admissible columns), 3 (performance smoke, ``slow``-marked) and 4 (structure
mirror of ``test_satad_component.py`` — the diff between the two modules is
meant to be ≲ field lists), plus the scheme-registry selection, the coupling-
constraint declaration, zero-copy through the component path, the ``out=``
path, and the config/constants transcription checks against icon4py.

Backends: ``embedded`` + ``gtfn_cpu`` always, ``gtfn_gpu`` under the ``gpu``
marker (via the shared ``backend`` fixture).
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from symcon.core import (
    ComputeContext,
    CouplingConstraintError,
    SequentialUpdateSplitting,
    make_backend,
    validate_composition,
)
from symcon.core.state import canonical_units, make_dataarray
from symcon.core.testing import assert_allclose
from symcon.icon.components import Graupel, GraupelConfig, Microphysics
from symcon.icon.components.fast.graupel_constants import CLOUD_NUM, GRAUPEL_QMIN
from symcon.icon.grid.vertical import SleveConfig, VerticalGrid
from symcon.icon.testing import moist_test_column

#: SPEC S08 acceptance-2 tolerance contracts:
#: |Δ(Σq·rho·dz) + total_ground_flux·Δt| ≤ rtol · Σq·rho·dz.
#: In the mixed-phase/warm regime (condensate at T > 233 K) the scheme's
#: flux-form sedimentation closes the discrete column water budget to fp
#: round-off (observed ≤ 3e-17 relative) — CONSERVATION_RTOL leaves margin for
#: fp accumulation only. Supercooled cloud water at T ≤ 233 K near the top of
#: the moist domain leaks mass through the fresh-ice glaciation/sedimentation
#: corner of the granule's scan (observed ≤ 4e-6 of the water path per step;
#: reproduced by the icon4py granule itself — symcon only adds x + dx/dt·Δt;
#: see STATUS.md), so the any-admissible-column bound is the *documented*
#: CONSERVATION_RTOL_COLD.
CONSERVATION_RTOL = 1e-13
CONSERVATION_RTOL_COLD = 1e-5
#: Coldest temperature at which the strict (round-off) contract applies [K].
STRICT_CONSERVATION_TMIN = 233.0
#: Negativity contract: no tracer below the scheme's own clipping epsilon
#: (QMIN = 1e-15, "threshold for lowest detectable mixing ratios").
NEGATIVITY_EPS = GRAUPEL_QMIN

TRACERS = (
    "specific_humidity",
    "specific_cloud_content",
    "specific_ice_content",
    "specific_rain_content",
    "specific_snow_content",
    "specific_graupel_content",
)
OUTPUTS = ("air_temperature", *TRACERS)
RATES = (
    "icon:rain_gsp_rate",
    "icon:snow_gsp_rate",
    "icon:ice_gsp_rate",
    "icon:graupel_gsp_rate",
)

NLEV = 65
DT = timedelta(seconds=30.0)


@pytest.fixture(scope="module")
def vertical_grid() -> VerticalGrid:
    return VerticalGrid.from_config(SleveConfig(num_levels=NLEV))


def _with_qnc(state: dict[str, Any], n_cell: int) -> dict[str, Any]:
    """Add the cloud droplet number concentration the graupel scheme consumes
    (ICON default ``cloud_num`` = 200e6 /m3, ``gscp_data.f90``; the S06 column
    builders do not carry it)."""
    state["icon:qnc"] = make_dataarray(
        np.full((n_cell,), CLOUD_NUM),
        name="icon:qnc",
        dims=("cell",),
        units=canonical_units("icon:qnc"),
        location="cell",
    )
    return state


def _precipitating_column(n_cell: int = 4, nlev: int = NLEV) -> dict[str, Any]:
    """The S06 moist test column seeded with cloud/hydrometeor content so every
    graupel process family (autoconversion, riming, sedimentation, melting)
    has something to chew on."""
    state = moist_test_column("reference_moist", nlev=nlev, n_cell=n_cell)
    state["specific_humidity"].data[:] *= 2.0
    state["specific_cloud_content"].data[:] = 1e-3
    state["specific_ice_content"].data[:] = 1e-4
    state["specific_rain_content"].data[:] = 1e-4
    state["specific_snow_content"].data[:] = 1e-4
    state["specific_graupel_content"].data[:] = 1e-4
    return _with_qnc(state, n_cell)


def _run(component: Microphysics, state: dict[str, Any], **kwargs: Any) -> Any:
    with warnings.catch_warnings():
        # icon4py's embedded execution warns about Python execution / where-branch
        # arithmetic; their own tests run with the same warnings.
        warnings.simplefilter("ignore")
        return component(state, DT, **kwargs)


def _ctx(backend: str) -> ComputeContext:
    return ComputeContext(backend=make_backend(backend))


@pytest.fixture
def graupel(backend: str, vertical_grid: VerticalGrid) -> Microphysics:
    return Microphysics(vertical_grid, GraupelConfig(), _ctx(backend))


def test_standalone_fig1_pattern(graupel: Microphysics) -> None:
    """SPEC-mirror of S07 acceptance 4: ``mphys(state)`` works interactively."""
    state = _precipitating_column()
    diagnostics, new_state = _run(graupel, state)
    assert sorted(diagnostics) == sorted(RATES)
    assert sorted(new_state) == sorted(OUTPUTS)
    # Precipitation happened: hydrometeors fell out and reached the ground.
    total_rate = sum(float(np.asarray(diagnostics[name].data).max()) for name in RATES)
    assert total_rate > 0.0


def _budget_check(
    graupel: Microphysics,
    qv_scale: float,
    condensate: tuple[float, float, float, float, float],
    *,
    tmin: float,
    rtol: float,
) -> None:
    """Build an admissible column (bounded moisture scalings on the hydrostatic
    ICON reference atmosphere, condensate seeded where T > ``tmin``), step it,
    and assert the water budget ``Σq·rho·dz + total_ground_flux·Δt`` closes to
    ``rtol`` and no tracer ends below -QMIN.

    ``n_cell`` matches the other tests so all gtfn legs share one compiled
    program variant (horizontal sizes are compile-time static args)."""
    n_cell = 4
    state = moist_test_column("reference_moist", nlev=NLEV, n_cell=n_cell)
    state["specific_humidity"].data[:] *= qv_scale
    seed_mask = np.asarray(state["air_temperature"].data) > tmin
    for name, magnitude in zip(TRACERS[1:], condensate, strict=True):
        state[name].data[:] = magnitude * seed_mask
    _with_qnc(state, n_cell)

    diagnostics, new_state = _run(graupel, state)

    rho = np.asarray(state["air_density"].data)
    dz = np.asarray(state["icon:ddqz_z_full"].data)
    path_before = (sum(np.asarray(state[name].data) for name in TRACERS) * rho * dz).sum(axis=1)
    path_after = (sum(np.asarray(new_state[name].data) for name in TRACERS) * rho * dz).sum(axis=1)
    ground_flux = sum(np.asarray(diagnostics[name].data) for name in RATES)
    assert_allclose(
        path_after + ground_flux * DT.total_seconds(),
        path_before,
        rtol=rtol,
        atol=0.0,
        names=("water path + accumulated precip", "initial water path"),
    )
    for name in TRACERS:
        assert float(np.asarray(new_state[name].data).min()) >= -NEGATIVITY_EPS, name


_CONDENSATE = st.tuples(
    st.floats(0.0, 3e-3),  # qc
    st.floats(0.0, 1e-3),  # qi
    st.floats(0.0, 1e-3),  # qr
    st.floats(0.0, 1e-3),  # qs
    st.floats(0.0, 1e-3),  # qg
)
_HYPOTHESIS_SETTINGS = settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


@given(qv_scale=st.floats(0.1, 3.0), condensate=_CONDENSATE)
@_HYPOTHESIS_SETTINGS
def test_total_water_conservation_and_negativity(
    graupel: Microphysics, qv_scale: float, condensate: tuple[float, float, float, float, float]
) -> None:
    """SPEC acceptance 2 on hypothesis-generated admissible columns: with
    condensate in the mixed-phase/warm regime (T > 233 K) the budget closes to
    fp round-off."""
    _budget_check(
        graupel, qv_scale, condensate, tmin=STRICT_CONSERVATION_TMIN, rtol=CONSERVATION_RTOL
    )


@given(qv_scale=st.floats(0.1, 3.0), condensate=_CONDENSATE)
@_HYPOTHESIS_SETTINGS
def test_total_water_conservation_cold_documented_bound(
    graupel: Microphysics, qv_scale: float, condensate: tuple[float, float, float, float, float]
) -> None:
    """SPEC acceptance 2, any-column bound: condensate everywhere (including
    supercooled cloud water above the glaciation corner near the moist-domain
    top) leaks ≤ the *documented* CONSERVATION_RTOL_COLD (see constant note +
    STATUS.md — a granule property, not symcon arithmetic)."""
    _budget_check(graupel, qv_scale, condensate, tmin=0.0, rtol=CONSERVATION_RTOL_COLD)


def test_levels_above_kstart_moist_untouched(graupel: Microphysics) -> None:
    """The moist-physics domain starts at kstart_moist; above it graupel is a no-op."""
    kstart = graupel._vertical.kstart_moist
    assert kstart > 0  # default grid tops out above htop_moist_proc
    state = _precipitating_column()
    _, new_state = _run(graupel, state)
    for name in OUTPUTS:
        before = np.asarray(state[name].data)[:, :kstart]
        after = np.asarray(new_state[name].data)[:, :kstart]
        assert_allclose(after, before, rtol=0.0, atol=0.0, names=name)


def test_out_path(graupel: Microphysics) -> None:
    """The S03 ``out=`` acceptance repeated on a real component (S07 mirror)."""
    state = _precipitating_column()
    _, reference = _run(graupel, state)

    out = {name: state[name].copy(deep=True) for name in OUTPUTS}
    out_buffers = {name: out[name].data for name in out}
    _, new_state = _run(graupel, state, out=out)
    for name, provided in out.items():
        assert new_state[name] is provided  # the caller's DataArrays come back
        assert new_state[name].data is out_buffers[name]  # written in place
        assert_allclose(
            np.asarray(new_state[name].data),
            np.asarray(reference[name].data),
            rtol=0.0,
            atol=0.0,
            names=name,
        )


def test_zero_copy_through_component_ingress(vertical_grid: VerticalGrid) -> None:
    """S07-mirror: the gt4py views built inside ``array_call`` alias the state
    buffers (numpy; the cupy path is the gpu-marked test in
    test_ingress_gt4py.py)."""
    from icon4py.model.common import dimension as i4_dims

    graupel = Microphysics(vertical_grid, ctx=_ctx("embedded"))
    buf = np.full((4, NLEV), 250.0)
    field = graupel._backend.as_field((i4_dims.CellDim, i4_dims.KDim), buf)
    assert field.ndarray is buf


def test_coupling_constraints_declared() -> None:
    assert Graupel.coupling_constraints.admissible_operators == ("sequential_update_splitting",)


def test_graupel_enters_sus_but_not_parallel_splitting(vertical_grid: VerticalGrid) -> None:
    """tutorial §3.7.2: microphysics is a sequential-update-split fast process;
    the tendency-summing operator families must reject it at composition time."""
    graupel = Microphysics(vertical_grid, ctx=_ctx("embedded"))
    federation = SequentialUpdateSplitting([graupel])  # accepted
    assert federation is not None
    with pytest.raises(CouplingConstraintError, match="does not admit"):
        validate_composition([graupel], operator="parallel_splitting", ordered=False)


def test_wrong_level_count_raises(vertical_grid: VerticalGrid) -> None:
    state = _precipitating_column(n_cell=2, nlev=40)
    graupel = Microphysics(vertical_grid, ctx=_ctx("embedded"))
    with pytest.raises(ValueError, match="40 levels"):
        _run(graupel, state)


def test_scheme_registry_selection(vertical_grid: VerticalGrid) -> None:
    """SPEC: scheme selectable by registry name ("graupel" only, for now)."""
    ctx = _ctx("embedded")
    by_kwarg = Microphysics(vertical_grid, ctx=ctx, scheme="graupel")
    by_default = Microphysics(vertical_grid, ctx=ctx)
    by_factory = Microphysics.factory("graupel", vertical_grid, None, ctx)
    direct = Graupel(vertical_grid, ctx=ctx)
    assert all(type(c) is Graupel for c in (by_kwarg, by_default, by_factory, direct))
    assert sorted(Microphysics.registry) == ["graupel"]
    with pytest.raises(KeyError, match="kessler"):
        Microphysics(vertical_grid, ctx=ctx, scheme="kessler")
    with pytest.raises(ValueError, match="graupel"):
        Graupel(vertical_grid, ctx=ctx, scheme="kessler")


def test_config_defaults_match_icon4py() -> None:
    """Transcribed defaults + round trip (REFERENCES.lock icon4py-graupel)."""
    from icon4py.model.atmosphere.subgrid_scale_physics.microphysics import (
        single_moment_six_class_gscp_graupel as i4_graupel,
    )

    cfg = GraupelConfig()
    assert cfg.to_icon4py() == i4_graupel.SingleMomentSixClassIconGraupelConfig()
    assert GraupelConfig.from_icon4py(cfg.to_icon4py()) == cfg


def test_scheme_constants_match_icon4py() -> None:
    """Shared scheme-constants module = single source of numerical truth (§8.6)."""
    from icon4py.model.atmosphere.subgrid_scale_physics.microphysics.microphysics_constants import (
        MicrophysicsConstants,
    )

    assert float(MicrophysicsConstants.QMIN) == GRAUPEL_QMIN


@pytest.mark.slow
def test_perf_smoke_gtfn_cpu_vs_embedded() -> None:
    """SPEC acceptance 3: gtfn_cpu >= 5x embedded on a 10k-column batch — a
    regression tripwire, not a target (observed >> 100x; embedded executes the
    K-scan per column in Python, which is also why this test keeps nlev small
    and carries the ``slow`` marker)."""
    import time

    n_cell, nlev = 10_000, 5
    grid = VerticalGrid.from_config(SleveConfig(num_levels=nlev))
    state = _precipitating_column(n_cell=n_cell, nlev=nlev)

    def steady_seconds(backend_name: str, warmup: bool) -> float:
        component = Microphysics(grid, GraupelConfig(), _ctx(backend_name))
        if warmup:  # bind + gtfn compile outside the timed region
            _run(component, state)
        start = time.perf_counter()
        _run(component, state)
        return time.perf_counter() - start

    embedded = steady_seconds("embedded", warmup=False)
    gtfn_cpu = steady_seconds("gtfn_cpu", warmup=True)
    assert gtfn_cpu * 5.0 <= embedded, f"gtfn_cpu {gtfn_cpu:.3f}s vs embedded {embedded:.3f}s"
