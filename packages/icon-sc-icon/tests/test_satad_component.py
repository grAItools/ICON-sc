"""S07 acceptance tests for ``SaturationAdjustment`` on the S06 test column.

Covers SPEC acceptance 2 (zero-copy through the component path), 3 (fixed-point
idempotence ≤ 1e-12), 4 (sympl Fig.-1 standalone usability) and 5 (``out=``
path), plus the coupling-constraint declaration and an L0 check of the adjusted
state against the mined Tetens/qsat closure (REFERENCES.lock ``icon4py-satad``).

Backends: ``embedded`` + ``gtfn_cpu`` always, ``gtfn_gpu`` under the ``gpu``
marker (via the shared ``backend`` fixture).
"""

from __future__ import annotations

import warnings
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

from icon_sc.core import (
    ComputeContext,
    CouplingConstraintError,
    SequentialUpdateSplitting,
    make_backend,
    validate_composition,
)
from icon_sc.core.testing import assert_allclose
from icon_sc.icon._constants import ALV, CLW, CVD, RV, TMELT
from icon_sc.icon.components import SaturationAdjustment, SaturationAdjustmentConfig
from icon_sc.icon.grid.vertical import SLEVEConfig, VerticalGrid
from icon_sc.icon.testing import moist_test_column

#: SPEC S07 acceptance-3 tolerance contract (idempotence on adjusted states).
IDEMPOTENCE_ATOL = 1e-12

#: Tetens constants of the wrapped granule (icon4py v0.2.0
#: microphysics_constants.py: TETENS_P0/AW/BW; REFERENCES.lock icon4py-satad).
TETENS_P0 = 610.78
TETENS_AW = 17.269
TETENS_BW = 35.86

NLEV = 65
DT = timedelta(seconds=30.0)


def _qsat_rho(temperature: np.ndarray, rho: np.ndarray) -> np.ndarray:
    """qsat = psat / (rho·rv·T), Tetens psat — the granule's closure, mined."""
    psat = TETENS_P0 * np.exp(TETENS_AW * (temperature - TMELT) / (temperature - TETENS_BW))
    return psat / (rho * RV * temperature)


@pytest.fixture(scope="module")
def vertical_grid() -> VerticalGrid:
    return VerticalGrid.from_config(SLEVEConfig(num_levels=NLEV))


def _supersaturated_column(n_cell: int = 4) -> dict[str, Any]:
    """The S06 moist test column with qv boosted into supersaturation low down."""
    state = _column = moist_test_column("reference_moist", nlev=NLEV, n_cell=n_cell)
    _column["specific_humidity"].data[:] *= 3.0
    return state


def _run(component: SaturationAdjustment, state: dict[str, Any], **kwargs: Any) -> Any:
    with warnings.catch_warnings():
        # icon4py's embedded execution warns about Python execution / where-branch
        # arithmetic; their own tests run with the same warnings.
        warnings.simplefilter("ignore")
        return component(state, DT, **kwargs)


def _ctx(backend: str) -> ComputeContext:
    return ComputeContext(backend=make_backend(backend))


def test_standalone_fig1_pattern(backend: str, vertical_grid: VerticalGrid) -> None:
    """SPEC acceptance 4: ``satad(state)`` works interactively on an S06 column."""
    state = _supersaturated_column()
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx(backend))
    diagnostics, new_state = _run(satad, state)
    assert diagnostics == {}
    assert sorted(new_state) == [
        "air_temperature",
        "specific_cloud_content",
        "specific_humidity",
    ]
    # Condensation happened: cloud created, latent heat warms the column.
    assert float(new_state["specific_cloud_content"].data.max()) > 0.0
    assert float(new_state["air_temperature"].data.max()) > float(
        state["air_temperature"].data.max()
    )


def test_adjusted_state_is_saturated_and_conservative(
    backend: str, vertical_grid: VerticalGrid
) -> None:
    """L0 physics: qv+qc conserved; condensing points end at qv = qsat(T_new, rho);
    energy closure T_new - T = (Lv/cvd)·(qv - qv_new) with L_v(T_initial)."""
    state = _supersaturated_column()
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx(backend))
    _, new_state = _run(satad, state)

    qv0 = state["specific_humidity"].data
    qc0 = state["specific_cloud_content"].data
    t0 = state["air_temperature"].data
    rho = state["air_density"].data
    qv1 = np.asarray(new_state["specific_humidity"].data)
    qc1 = np.asarray(new_state["specific_cloud_content"].data)
    t1 = np.asarray(new_state["air_temperature"].data)

    assert_allclose(qv1 + qc1, qv0 + qc0, rtol=1e-13, atol=1e-18, names="total water")

    condensed = qc1 > 1e-12
    assert condensed.any()
    assert_allclose(
        qv1[condensed],
        _qsat_rho(t1, rho)[condensed],
        rtol=1e-9,  # Newton tolerance is 1e-3 K on T; qsat sensitivity ~5%/K
        atol=1e-6,
        names=("qv_adjusted", "qsat(T_adjusted)"),
    )
    # Latent-heat closure with cvd bookkeeping (mo_satad.f90: lwdocvd = L_v(T)/cvd;
    # L(T) = alv + (1850 - cpl)(T - tmelt) - rv·T, icon4py latent_heat_vaporization
    # with cpl = clw = (rcpl+1)·cpd). Exact on the subsaturated shortcut; on Newton
    # points the defect is the converged residual (quadratic in the 1e-3 K
    # tolerance), hence atol 1e-4 K.
    lv = ALV + (1850.0 - CLW) * (t0 - TMELT) - RV * t0
    assert_allclose(
        t1 - t0,
        lv / CVD * (qv0 - qv1),
        rtol=0.0,
        atol=1e-4,
        names=("dT", "Lv/cvd dqv"),
    )


def test_levels_above_kstart_moist_untouched(backend: str, vertical_grid: VerticalGrid) -> None:
    """The moist-physics domain starts at kstart_moist; above it satad is a no-op."""
    kstart = vertical_grid.kstart_moist
    assert kstart > 0  # default grid tops out above htop_moist_proc
    state = _supersaturated_column()
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx(backend))
    _, new_state = _run(satad, state)
    for name in ("air_temperature", "specific_humidity", "specific_cloud_content"):
        before = np.asarray(state[name].data)[:, :kstart]
        after = np.asarray(new_state[name].data)[:, :kstart]
        assert_allclose(after, before, rtol=0.0, atol=0.0, names=name)


def test_fixed_point_idempotence(backend: str, vertical_grid: VerticalGrid) -> None:
    """SPEC acceptance 3: applying satad twice changes nothing beyond 1e-12."""
    state = _supersaturated_column()
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx(backend))
    _, once = _run(satad, state)
    second_input = dict(state)
    second_input.update(once)
    _, twice = _run(satad, second_input)
    for name in ("air_temperature", "specific_humidity", "specific_cloud_content"):
        assert_allclose(
            np.asarray(twice[name].data),
            np.asarray(once[name].data),
            rtol=0.0,
            atol=IDEMPOTENCE_ATOL,
            names=name,
        )


def test_out_path(backend: str, vertical_grid: VerticalGrid) -> None:
    """SPEC acceptance 5: the S03 ``out=`` acceptance repeated on a real component."""
    state = _supersaturated_column()
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx(backend))
    _, reference = _run(satad, state)

    out = {
        name: state[name].copy(deep=True)
        for name in ("air_temperature", "specific_humidity", "specific_cloud_content")
    }
    out_buffers = {name: out[name].data for name in out}
    _, new_state = _run(satad, state, out=out)
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
    """SPEC acceptance 2 on the component path: the gt4py views built inside
    ``array_call`` alias the state buffers (numpy; the cupy path is the
    gpu-marked test in test_ingress_gt4py.py)."""
    from icon4py.model.common import dimension as i4_dims

    satad = SaturationAdjustment(vertical_grid, ctx=_ctx("embedded"))
    buf = np.full((4, NLEV), 250.0)
    field = satad._backend.as_field((i4_dims.CellDim, i4_dims.KDim), buf)
    assert field.ndarray is buf


def test_coupling_constraints_declared() -> None:
    assert SaturationAdjustment.coupling_constraints.admissible_operators == (
        "sequential_update_splitting",
    )


def test_satad_enters_sus_but_not_parallel_splitting(vertical_grid: VerticalGrid) -> None:
    """tutorial §3.7.2: satad is a sequential-update-split adjustment; the
    tendency-summing operator families must reject it at composition time."""
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx("embedded"))
    federation = SequentialUpdateSplitting([satad])  # accepted
    assert federation is not None
    with pytest.raises(CouplingConstraintError, match="does not admit"):
        validate_composition([satad], operator="parallel_splitting", ordered=False)


def test_wrong_level_count_raises(vertical_grid: VerticalGrid) -> None:
    state = moist_test_column("reference_moist", nlev=40, n_cell=2)
    satad = SaturationAdjustment(vertical_grid, ctx=_ctx("embedded"))
    with pytest.raises(ValueError, match="40 levels"):
        _run(satad, state)


def test_config_defaults_match_icon4py() -> None:
    """Transcribed defaults (REFERENCES.lock icon4py-satad): 10 / 1e-3."""
    cfg = SaturationAdjustmentConfig()
    assert cfg.max_iter == 10
    assert cfg.tolerance == 1.0e-3
